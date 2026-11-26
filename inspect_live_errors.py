"""Inspect a train's errors from a dated live-evaluation report."""

import argparse
from datetime import date
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        required=True,
        type=date.fromisoformat,
        help="Local collection date, YYYY-MM-DD",
    )
    parser.add_argument(
        "--train",
        required=True,
        help="Train number, preserved as text",
    )
    args = parser.parse_args()

    path = (
        PROJECT / "data/processed/live_evaluations"
        / f"{args.date}.json"
    )

    try:
        report = json.loads(path.read_text())

        if report["collection_date"] != str(args.date):
            raise ValueError("Report date does not match the requested date.")

        examples = [
            row for row in report["examples"]
            if row["train"] == args.train
        ]
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Could not read evaluation: {error}\n")

    if not examples:
        print(
            f"No evaluated examples for train {args.train} "
            f"on {args.date}. This does not establish that it was absent."
        )
        return

    extra_errors = []

    for row in examples:
        baseline_error = abs(
            row["current_delay"] - row["outcome_delay"]
        )
        model_error = abs(
            row["prediction"] - row["outcome_delay"]
        )
        extra = model_error - baseline_error
        extra_errors.append(extra)

        print(
            f"{row['anchor_utc']} | "
            f"current={row['current_delay']} | "
            f"history={row['history_category']} | "
            f"prediction={row['prediction']} | "
            f"later={row['outcome_delay']} | "
            f"extra error={extra:+.1f}"
        )

    print(f"\nEvaluated examples: {len(examples)}")
    print(
        f"Total additional absolute error versus persistence: "
        f"{sum(extra_errors):+.1f} minutes"
    )
    print("Positive means the model was worse; negative means it helped.")


if __name__ == "__main__":
    main()