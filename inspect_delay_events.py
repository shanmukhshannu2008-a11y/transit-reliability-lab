from datetime import date

import duckdb

from baseline_delay import PROJECT
from train_delay_model import load_development

archive = PROJECT / "data/raw/historical-review/2025.parquet"

with duckdb.connect() as connection:
    load_development(
        connection,
        archive,
        start=date(2025, 11, 17),
    )

    rows = connection.execute(
        """
        SELECT stamp, lateness
        FROM observations
        WHERE service_date = DATE '2025-11-24'
          AND train_number = ?
          AND CAST(stamp AS TIME)
              BETWEEN TIME '06:00:00' AND TIME '22:00:00'
        ORDER BY stamp
        """,
        ["5318"],
    ).fetchall()

    print("Train 5318 — November 24, 2025")
    print(f"Stored reports: {len(rows)}")

    print("\nFirst 15:")
    for timestamp, delay in rows[:15]:
        print(f"{timestamp} | Reported delay: {delay}")

    print("\nLast 15:")
    for timestamp, delay in rows[-15:]:
        print(f"{timestamp} | Reported delay: {delay}")