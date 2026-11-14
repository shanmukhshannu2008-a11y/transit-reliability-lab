import duckdb
from train_delay_model import load_development
from baseline_delay import PROJECT

archive = PROJECT / "data/raw/historical-review/2025.parquet"

with duckdb.connect() as connection:
    load_development(connection, archive)

    events = [
        ("5229", "18:40:00", "19:15:00"),
        ("5322", "09:40:00", "10:15:00"),
    ]

    for train, start, end in events:
        rows = connection.execute(
            """
            SELECT stamp, lateness
            FROM observations
            WHERE service_date = DATE '2025-12-05'
              AND train_number = ?
              AND CAST(stamp AS TIME)
                  BETWEEN CAST(? AS TIME) AND CAST(? AS TIME)
            ORDER BY stamp
            """,
            [train, start, end],
        ).fetchall()

        print(f"\nTrain {train} — stored reports:")
        for timestamp, delay in rows:
            print(f"{timestamp} | Reported delay: {delay}")