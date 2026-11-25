"""Export selected historical case studies for the dashboard."""

from datetime import date
import json

import duckdb

from baseline_delay import PROJECT, EXPECTED_SHA
from train_delay_model import load_development


CASES = [
    {
        "date": "2025-11-24",
        "train": "5318",
        "start": "06:00:00",
        "end": "22:00:00",
        "reason": "Extended increase in reported delay.",
    },
    {
        "date": "2025-12-05",
        "train": "5229",
        "start": "18:40:00",
        "end": "19:15:00",
        "reason": "Abrupt drop followed by special status 999.",
    },
    {
        "date": "2025-12-05",
        "train": "5322",
        "start": "09:40:00",
        "end": "10:15:00",
        "reason": "Abrupt drop followed by increasing reported delay.",
    },
]


def classify(value):
    if value == 999:
        return None, "special_999"
    if value == 998:
        return None, "unresolved_998"
    if type(value) is int and 0 <= value <= 997:
        return value, "numeric"
    return None, "unknown"


def main():
    archive = PROJECT / "data/raw/historical-review/2025.parquet"
    examples = []

    with duckdb.connect() as connection:
        # This loader verifies the reviewed archive's checksum.
        load_development(
            connection,
            archive,
            start=date(2025, 11, 17),
        )

        for case in CASES:
            rows = connection.execute(
                """
                SELECT stamp, lateness
                FROM observations
                WHERE service_date = CAST(? AS DATE)
                  AND train_number = ?
                  AND CAST(stamp AS TIME) >= CAST(? AS TIME)
                  AND CAST(stamp AS TIME) < CAST(? AS TIME)
                ORDER BY stamp
                """,
                [
                    case["date"],
                    case["train"],
                    case["start"],
                    case["end"],
                ],
            ).fetchall()

            if not rows:
                raise ValueError(f"No reports found for {case}")

            reports = []

            for timestamp, raw_delay in rows:
                delay, status = classify(raw_delay)

                reports.append({
                    "timestamp": timestamp.isoformat(),
                    "raw_late": raw_delay,
                    "reported_delay": delay,
                    "status": status,
                })

            examples.append({
                **case,
                "reports": reports,
            })

            print(
                f"{case['date']} | Train {case['train']} | "
                f"{len(reports)} stored reports"
            )

    bundle = {
        "schema_version": 1,
        "source": {
            "dataset": "fulldecent/septa-regionalrail-otp",
            "url": (
                "https://huggingface.co/datasets/"
                "fulldecent/septa-regionalrail-otp"
            ),
            "license": "CC-BY-4.0",
            "archive_sha256": EXPECTED_SHA,
            "transformation": (
                "Selected date/train/time windows; retained raw values "
                "and separated provisional numeric delays from statuses."
            ),
        },
        "time_basis": (
            "Source-local America/New_York wall-clock times; "
            "timestamps are not UTC."
        ),
        "limitations": [
            "Purposively selected case studies, not a representative sample.",
            "Reported delays, not verified station arrivals.",
            "Missing reports do not establish unchanged delay.",
            "999 is a special status, not 999 minutes late; "
            "operational interpretation remains provisional.",
        ],
        "examples": examples,
    }

    output = PROJECT / "docs/TIMELINE_EXAMPLES.json"
    output.write_text(json.dumps(bundle, indent=2) + "\n")

    print(f"Saved: {output}")


if __name__ == "__main__":
    main()