"""Explore observed-update eligibility, not general forecasting accuracy."""
import argparse
import json
from pathlib import Path
import duckdb

PROJECT = Path(__file__).resolve().parent


def eligibility(connection):
    # 'observations' contains service_date, train_number, stamp, lateness.
    # Do not drop 999 before matching: a status event must not be skipped.
    return connection.execute('''
        WITH anchors AS (
            SELECT *, stamp + INTERVAL '8 minutes' AS earliest
            FROM observations WHERE lateness BETWEEN 0 AND 998
        ), pairs AS (
            SELECT a.lateness AS initial, b.lateness AS future,
                   epoch(b.stamp - a.stamp) AS horizon_seconds
            FROM anchors a ASOF LEFT JOIN observations b
            ON a.service_date = b.service_date
            AND a.train_number = b.train_number
            AND a.earliest <= b.stamp
        )
        SELECT count(*) AS numeric_anchors,
          count(*) FILTER (WHERE horizon_seconds BETWEEN 480 AND 720) AS nearby_updates,
          count(*) FILTER (WHERE horizon_seconds BETWEEN 480 AND 720
                           AND future BETWEEN 0 AND 998) AS numeric_pairs,
          count(*) FILTER (WHERE horizon_seconds BETWEEN 480 AND 720
                           AND future = 999) AS special_status_pairs
        FROM pairs
    ''').fetchone()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=PROJECT/'data/raw/historical-review/2025.parquet')
    parser.add_argument('--start', default='2025-12-01')
    parser.add_argument('--end', default='2025-12-08', help='Exclusive service-date bound')
    args = parser.parse_args()
    from datetime import date
    try:
        if date.fromisoformat(args.start) >= date.fromisoformat(args.end):
            parser.error('start must precede end')
    except ValueError:
        parser.error('dates must be YYYY-MM-DD')
    c = duckdb.connect()
    c.execute('CREATE TABLE archive AS SELECT * FROM read_parquet(?)', [str(args.input)])
    totals = c.execute('''SELECT count(*),min(service_date),max(service_date),
                         count(distinct service_date),count(distinct train_number),
                         count(*) FILTER (WHERE lateness=999) FROM archive''').fetchone()
    # Restrict the pilot to daytime to avoid ambiguous DST/overnight timestamps.
    c.execute('''CREATE TABLE observations AS SELECT service_date, train_number,
                 CAST(service_date AS DATE) + CAST(time AS TIME) AS stamp, lateness
                 FROM archive WHERE service_date >= CAST(? AS DATE)
                   AND service_date < CAST(? AS DATE)
                   AND CAST(time AS TIME) >= TIME '06:00:00'
                   AND CAST(time AS TIME) < TIME '22:00:00' ''', [args.start,args.end])
    sample = c.execute('SELECT count(*),count(distinct service_date),count(distinct train_number) FROM observations').fetchone()
    duplicate_count = c.execute('''SELECT count(*) FROM (SELECT service_date, train_number, stamp
                 FROM observations GROUP BY ALL HAVING count(*) > 1)''').fetchone()[0]
    if duplicate_count:
        raise ValueError('Duplicate observation keys require investigation before matching')
    anchors, updates, numeric, special = eligibility(c)
    result = {
        'archive': dict(zip(['rows','first_date','last_date','dates','train_numbers','status_999_rows'],totals)),
        'pilot': {'start_inclusive':args.start,'end_exclusive':args.end,
                  'local_hours':'06:00 to before 22:00','rows':sample[0],
                  'dates':sample[1],'train_numbers':sample[2],
                  'numeric_anchors':anchors,'nearby_observed_updates':updates,
                  'numeric_pairs':numeric,'special_status_pairs':special,
                  'numeric_pair_fraction':numeric/anchors if anchors else None},
        'pair_rule':'First stored update at or after anchor+8 minutes, accepted only through +12 minutes, same service date and train number.',
        'limitations':[
          'All regional rail: historical route mapping not established.',
          'Missing unchanged updates prevent treating this as general fixed-horizon ground truth.',
          'Numeric means 0..998 excluding known 999; other code meanings and outliers require validation.',
          'Daytime restriction avoids overnight/DST ambiguity; no claim of complete trip coverage.',
          'This measures label availability, not model accuracy; no forward filling or model training.',
        ],
    }
    out=PROJECT/'data/processed/historical_eligibility.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(result,indent=2,default=str)
    out.write_text(text+'\n')
    print(text)
    print(f'Saved: {out}')


if __name__ == '__main__':
    main()
