"""Development-only persistence baseline for observed historical updates."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import duckdb

PROJECT = Path(__file__).resolve().parent
EXPECTED_SHA = '24ff2d976b140357c47e1eb320ad2a1ecc9f3d161b4a35c5c6c8290f39dedb37'


def build_pairs(connection):
    """Select outcome before filtering statuses, never skip an invalid update."""
    connection.execute('''CREATE OR REPLACE TABLE pairs AS
        WITH anchors AS (
          SELECT *, stamp + INTERVAL '8 minutes' AS earliest
          FROM observations WHERE lateness BETWEEN 0 AND 997
        ), matched AS (
          SELECT a.service_date, a.train_number, a.stamp AS anchor_time,
                 a.lateness AS initial, b.stamp AS outcome_time,
                 b.lateness AS outcome,
                 epoch(b.stamp-a.stamp) AS horizon_seconds
          FROM anchors a ASOF LEFT JOIN observations b
          ON a.service_date=b.service_date AND a.train_number=b.train_number
          AND a.earliest<=b.stamp
        )
        SELECT m.*, CASE
          WHEN outcome_time IS NULL OR horizon_seconds>720 THEN 'no_nearby_update'
          WHEN outcome IS NULL OR outcome NOT BETWEEN 0 AND 997 THEN 'non_numeric_outcome'
          WHEN EXISTS (SELECT 1 FROM observations x
            WHERE x.service_date=m.service_date AND x.train_number=m.train_number
              AND x.stamp>m.anchor_time AND x.stamp<m.outcome_time
              AND (x.lateness IS NULL OR x.lateness NOT BETWEEN 0 AND 997))
            THEN 'intervening_status'
          ELSE 'eligible' END AS eligibility
        FROM matched m
    ''')


def metrics(rows):
    """rows = (initial delay, observed outcome, horizon seconds)."""
    if not rows:
        return {'pairs': 0, 'mae_minutes': None, 'mean_error_minutes': None,
                'median_absolute_error_minutes': None}
    signed = [initial-outcome for initial, outcome, _ in rows]
    absolute = [abs(error) for error in signed]
    return {'pairs':len(rows), 'mae_minutes':statistics.mean(absolute),
            'mean_error_minutes':statistics.mean(signed),
            'median_absolute_error_minutes':statistics.median(absolute)}


def run(input_path):
    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA:
        raise ValueError('Archive checksum differs from reviewed dataset; review before scoring')
    c = duckdb.connect()
    try:
        # December 6–7 is intentionally not loaded into observations or scored.
        c.execute('''CREATE TABLE observations AS SELECT service_date,train_number,
          CAST(service_date AS DATE)+CAST(time AS TIME) AS stamp,lateness
          FROM read_parquet(?) WHERE service_date>=DATE '2025-12-01'
          AND service_date<DATE '2025-12-06'
          AND CAST(time AS TIME)>=TIME '06:00:00' AND CAST(time AS TIME)<TIME '22:00:00'
        ''',[str(input_path)])
        duplicates = c.execute('''SELECT count(*) FROM (SELECT service_date,train_number,stamp
            FROM observations GROUP BY ALL HAVING count(*)>1)''').fetchone()[0]
        if duplicates:
            raise ValueError('Duplicate keys require review')
        raw_stats = c.execute('''SELECT count(*),min(lateness) FILTER(WHERE lateness<998),
            max(lateness) FILTER(WHERE lateness<998),count(*) FILTER(WHERE lateness=998),
            count(*) FILTER(WHERE lateness=999),count(*) FILTER(WHERE lateness IS NULL
            OR lateness<0 OR lateness>999) FROM observations''').fetchone()
        build_pairs(c)
        report = {
          'baseline':'Persistence: predicted future delay equals anchor delay',
          'archive_sha256':digest,
          'development_value_audit':dict(zip(['rows','numeric_min','numeric_max','code_998','code_999','other_invalid'],raw_stats)),
          'scope':'Regional rail observed-update pilot; not verified arrivals or Paoli-only',
          'matching':'First update at/after +8 minutes, accepted through +12; same service date/train. Reject nonnumeric endpoints and intervening statuses.',
          'numeric_policy':'Provisional integers 0..997; exclude 998 conservatively as unresolved and 999 as special. No outlier clipping.',
          'splits':{},
          'test':'December 6–7 not scored. Prior feasibility audit included their aggregate eligibility only.',
          'limitations':['Outcome availability selects a change-heavy subset.',
                         'Pairs overlap; no independence or confidence-interval claim.',
                         'Units are minutes based on upstream code, pending maintainer confirmation.',
                         'Train/date is a grouping assumption, not verified journey identity.']}
        for name,start,end in [('train','2025-12-01','2025-12-05'),('validation','2025-12-05','2025-12-06')]:
            selected = c.execute('''SELECT service_date,train_number,initial,outcome,horizon_seconds,eligibility
                FROM pairs WHERE service_date>=CAST(? AS DATE) AND service_date<CAST(? AS DATE)
                ORDER BY service_date,train_number,anchor_time''',[start,end]).fetchall()
            accepted = [r for r in selected if r[5]=='eligible']
            values = [(r[2],r[3],r[4]) for r in accepted]
            counts = dict(Counter(r[5] for r in selected))
            daily={str(d):metrics([(r[2],r[3],r[4]) for r in accepted if r[0]==d])
                   for d in sorted({r[0] for r in selected})}
            report['splits'][name]={
                'start_inclusive':start,'end_exclusive':end,
                'candidate_anchors':len(selected),'eligibility_counts':counts,
                'eligible_fraction':len(accepted)/len(selected) if selected else None,
                'train_date_groups':len({(r[0],r[1]) for r in accepted}),
                'metrics':metrics(values),'daily_metrics':daily,
                'horizon_metrics':{
                    '8_to_under_10_minutes':metrics([r for r in values if r[2]<600]),
                    '10_through_12_minutes':metrics([r for r in values if r[2]>=600])}}
        return report
    finally:
        c.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=PROJECT/'data/raw/historical-review/2025.parquet')
    args=parser.parse_args()
    report=run(args.input)
    out=PROJECT/'data/processed/baseline_development.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n')
    for name,split in report['splits'].items():
        print(f"{name}: {split['metrics']['pairs']} eligible pairs; "
              f"MAE {split['metrics']['mae_minutes']:.3f} minutes; "
              f"eligibility {split['eligible_fraction']:.1%}")
    print('December 6–7 test dates NOT scored.')
    print(f'Saved: {out}')


if __name__=='__main__':
    main()
