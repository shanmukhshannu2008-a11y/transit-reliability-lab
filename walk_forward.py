"""Expanding-window development evaluation; reserved December 6–7 stays excluded."""
from datetime import date, timedelta
import json
import duckdb
from baseline_delay import PROJECT, EXPECTED_SHA, build_pairs
from train_delay_model import load_development, feature_rows, MedianChangeModel, evaluate, FEATURE_POLICY

START = date(2025, 11, 17)
FIRST_VALIDATION = date(2025, 11, 24)
END = date(2025, 12, 6)  # Exclusive; never score reserved test dates.


def evaluate_folds(rows, first=FIRST_VALIDATION, end=END):
    if not START < first < end <= END:
        raise ValueError('Fold dates must stay within the development period')
    folds = []
    day = first
    while day < end:
        train = [r for r in rows if START <= r['day'] < day]
        validation = [r for r in rows if r['day'] == day]
        if not train or not validation:
            raise ValueError(f'Missing training or validation examples for {day}')
        # Fresh models every fold. Later folds may learn from earlier validation days.
        models = {'delay_only': MedianChangeModel(False).fit(train),
                  'delay_and_history': MedianChangeModel(True).fit(train)}
        predictors = {'persistence': lambda r: r['initial'],
                      **{name: model.predict for name, model in models.items()}}
        folds.append({
            'validation_date': str(day), 'train_start': str(START),
            'train_end_exclusive': str(day), 'training_pairs': len(train),
            'validation_pairs': len(validation),
            'metrics': {name: evaluate(validation, predict) for name, predict in predictors.items()},
            'by_trend': {trend: {name: evaluate([r for r in validation if r['trend']==trend], predict)
                                 for name, predict in predictors.items()}
                         for trend in ('falling', 'unchanged', 'rising', 'missing')},
            'parameters': {name: model.parameters() for name, model in models.items()}})
        day += timedelta(days=1)
    return folds


def run():
    with duckdb.connect() as connection:
        load_development(connection, PROJECT/'data/raw/historical-review/2025.parquet', start=START)
        build_pairs(connection)
        rows = feature_rows(connection)
        # Coverage includes every numeric anchor, not just rows with available outcomes.
        coverage = {str(day): {'candidate_anchors': n, 'eligible_pairs': eligible,
                              'eligible_fraction': eligible/n}
                    for day, n, eligible in connection.execute('''
                        SELECT service_date,count(*),count(*) FILTER(WHERE eligibility='eligible')
                        FROM pairs GROUP BY service_date ORDER BY service_date''').fetchall()}
    folds = evaluate_folds(rows)
    names = ('persistence', 'delay_only', 'delay_and_history')
    total = sum(f['validation_pairs'] for f in folds)
    summary = {name: {
        'pooled_mae_minutes': sum(f['metrics'][name]['mae_minutes']*f['validation_pairs'] for f in folds)/total,
        'mean_daily_mae_minutes': sum(f['metrics'][name]['mae_minutes'] for f in folds)/len(folds),
        'days_better_than_persistence': sum(f['metrics'][name]['mae_minutes'] < f['metrics']['persistence']['mae_minutes'] for f in folds)
    } for name in names}
    return {'archive_sha256': EXPECTED_SHA, 'feature_policy': FEATURE_POLICY,
            'scope': 'Conditional future reported delay; not arrival accuracy',
            'protocol': 'Train from Nov 17 through day before validation; validate Nov 24–Dec 5. Fixed model settings, no tuning.',
            'limitations': ['Development analysis, not independent final testing; December 5 inspected previously.',
                           'Pairs overlap; daily folds share training data. No independence or significance claim.',
                           'Missing unchanged reports bias outcome availability; route linkage unresolved.',
                           'December 6–7 not loaded or scored.'],
            'coverage': coverage, 'validation_pairs': total, 'summary': summary, 'folds': folds}


if __name__ == '__main__':
    report = run()
    out = PROJECT/'data/processed/walk_forward.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+'\n')
    for fold in report['folds']:
        m = fold['metrics']
        print(f"{fold['validation_date']} | n={fold['validation_pairs']} | baseline={m['persistence']['mae_minutes']:.3f} | model={m['delay_and_history']['mae_minutes']:.3f}")
    print(json.dumps(report['summary'], indent=2))
    print(f'Saved: {out}; reserved test dates NOT scored.')
