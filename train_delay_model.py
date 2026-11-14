"""Fit a small median-change regression model, without scoring reserved test dates."""
import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
from statistics import median
import duckdb
from baseline_delay import EXPECTED_SHA, PROJECT, build_pairs, metrics

FEATURE_POLICY = {
    'delay_bins': '0, 1–3, 4–7, 8–15, 16+',
    'history': 'Immediately previous stored report on same service date/train; valid numeric and at most 30 minutes old',
    'trend': 'falling, unchanged, rising; otherwise missing',
    'minimum_cell_examples': 30,
    'fallback': 'delay-only median change, then global training median change',
    'prediction': 'current delay + learned median change, floored at zero',
}


def delay_bin(value):
    return sum(value > edge for edge in (0, 3, 7, 15))


def feature_rows(connection):
    """Compute past-only features BEFORE restricting to anchors with labels."""
    result = connection.execute('''
      WITH history AS (
        SELECT *, lag(lateness) OVER w AS previous_delay,
          lag(stamp) OVER w AS previous_time
        FROM observations
        WINDOW w AS (PARTITION BY service_date,train_number ORDER BY stamp)
      )
      SELECT p.service_date,p.train_number,p.anchor_time,p.initial,p.outcome,
        p.horizon_seconds,h.previous_delay,epoch(p.anchor_time-h.previous_time)
      FROM pairs p JOIN history h ON p.service_date=h.service_date
        AND p.train_number=h.train_number AND p.anchor_time=h.stamp
      WHERE p.eligibility='eligible'
      ORDER BY p.service_date,p.train_number,p.anchor_time
    ''').fetchall()
    rows = []
    for day, train, stamp, initial, outcome, horizon, previous, age in result:
        valid = previous is not None and 0 <= previous <= 997 and 0 < age <= 1800
        trend = ('rising' if initial > previous else 'falling' if initial < previous
                 else 'unchanged') if valid else 'missing'
        rows.append(dict(day=day, train=train, stamp=stamp, initial=initial,
                         outcome=outcome, horizon=horizon, delay_bin=delay_bin(initial),
                         trend=trend))
    return rows


class MedianChangeModel:
    """Supervised regression: learn median outcome-minus-current delay per group."""
    def __init__(self, use_history=True, min_count=30):
        self.use_history = use_history
        self.min_count = min_count

    def fit(self, rows):
        if not rows:
            raise ValueError('Training examples required')
        cells, bins = defaultdict(list), defaultdict(list)
        changes = []
        for row in rows:
            change = row['outcome'] - row['initial']
            changes.append(change)
            bins[row['delay_bin']].append(change)
            cells[(row['delay_bin'], row['trend'])].append(change)
        self.global_change = median(changes)
        self.bins = {k: median(v) for k,v in bins.items() if len(v) >= self.min_count}
        self.cells = {k: median(v) for k,v in cells.items() if len(v) >= self.min_count}
        return self

    def predict(self, row):
        # outcome and actual future horizon are deliberately not model inputs.
        change = self.bins.get(row['delay_bin'], self.global_change)
        if self.use_history:
            change = self.cells.get((row['delay_bin'], row['trend']), change)
        return max(0, row['initial'] + change)

    def parameters(self):
        return {'global_change': self.global_change,
                'delay_bin_changes': {str(k): v for k,v in self.bins.items()},
                'history_cell_changes': {f'{k[0]}:{k[1]}': v for k,v in self.cells.items()}
                if self.use_history else {}}


def load_development(connection, path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise ValueError('Archive checksum differs from reviewed dataset')
    connection.execute('''CREATE TABLE observations AS
      SELECT service_date,train_number,CAST(service_date AS DATE)+CAST(time AS TIME) AS stamp,lateness
      FROM read_parquet(?) WHERE service_date>=DATE '2025-12-01'
        AND service_date<DATE '2025-12-06'
        AND CAST(time AS TIME)>=TIME '06:00:00' AND CAST(time AS TIME)<TIME '22:00:00'
    ''', [str(path)])
    if connection.execute('''SELECT count(*) FROM (SELECT service_date,train_number,stamp
        FROM observations GROUP BY ALL HAVING count(*)>1)''').fetchone()[0]:
        raise ValueError('Duplicate keys require review')


def evaluate(rows, predict):
    return metrics([(predict(r), r['outcome'], r['horizon']) for r in rows])


def run(path):
    with duckdb.connect() as connection:
        load_development(connection, path)
        build_pairs(connection)
        rows = feature_rows(connection)
    train = [r for r in rows if r['day'] < date(2025,12,5)]
    validation = [r for r in rows if r['day'] == date(2025,12,5)]
    if not train or not validation:
        raise ValueError('Both development splits require eligible examples')
    models = {'delay_only': MedianChangeModel(False).fit(train),
              'delay_and_history': MedianChangeModel(True).fit(train)}
    predictors = {'persistence': lambda r: r['initial'],
                  **{name: model.predict for name,model in models.items()}}

    errors = []

    for row in validation:
        prediction = models["delay_and_history"].predict(row)
        actual = row["outcome"]

        errors.append({
            "train": row["train"],
            "time": row["stamp"],
            "current": row["initial"],
            "trend": row["trend"],
            "prediction": prediction,
            "actual": actual,
            "absolute_error": abs(prediction - actual),
        })

    errors.sort(key=lambda row: row["absolute_error"], reverse=True)

    print("\n10 largest validation errors:")
    for error in errors[:10]:
        print(error)
        total_error = sum(row["absolute_error"] for row in errors)

    print("\nConcentration of validation error:")
    for count in (10, 50, 100):
        largest_error = sum(
            row["absolute_error"] for row in errors[:count]
        )
        share = largest_error / total_error if total_error else 0
        print(
            f"Top {count} examples account for "
            f"{share:.1%} of total absolute error"
        )
    report = {'archive_sha256': EXPECTED_SHA, 'feature_policy': FEATURE_POLICY,
              'training_dates': '2025-12-01 through 2025-12-04',
              'validation_date': '2025-12-05',
              'test': 'December 6–7 not loaded or scored; aggregate eligibility inspected previously',
              'parameters': {name: model.parameters() for name,model in models.items()},
              'splits': {}}
    for name, subset in [('train', train), ('validation', validation)]:
        report['splits'][name] = {
            'pairs': len(subset),
            'missing_history': sum(r['trend']=='missing' for r in subset),
            'metrics': {key: evaluate(subset, predict) for key,predict in predictors.items()},
            'daily': {str(day): {key: evaluate([r for r in subset if r['day']==day], predict)
                                for key,predict in predictors.items()}
                      for day in sorted({r['day'] for r in subset})}}


    for trend in ("falling", "unchanged", "rising", "missing"):
        group = [row for row in validation if row["trend"] == trend]

        if not group:
            continue

        baseline = evaluate(group, predictors["persistence"])
        learned = evaluate(group, predictors["delay_and_history"])

        baseline_mae = baseline["mae_minutes"]
        model_mae = learned["mae_minutes"]
        improvement = baseline_mae - model_mae

        print(
            f"{trend}: n={len(group)} | "
            f"baseline={baseline_mae:.3f} | "
            f"model={model_mae:.3f} | "
            f"improvement={improvement:+.3f} minutes"
        )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=PROJECT/'data/raw/historical-review/2025.parquet')
    args = parser.parse_args()
    report = run(args.input)
    out = PROJECT/'data/processed/model_development.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+'\n')
    for split, results in report['splits'].items():
        print(f"{split}: {results['pairs']} identical eligible examples")
        for name, score in results['metrics'].items():
            print(f"  {name}: MAE {score['mae_minutes']:.4f} minutes")
    print('Reserved test dates NOT scored.')
    print(f'Saved: {out}')


if __name__ == '__main__':
    main()
