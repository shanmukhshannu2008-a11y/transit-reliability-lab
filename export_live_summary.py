"""Export aggregate live-evaluation results for the public dashboard."""

import argparse
from datetime import date
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    args = parser.parse_args()

    source = (
        PROJECT / "data/processed/live_evaluations"
        / f"{args.date}.json"
    )
    report = json.loads(source.read_text())

    if report["collection_date"] != str(args.date):
        raise ValueError("Report date does not match requested date.")

    overall = report["overall"]
    if overall["examples"] != len(report["examples"]):
        raise ValueError("Example count does not match the detailed report.")

    summary = {
        "schema_version": 1,
        "collection_date": report["collection_date"],
        "collection_timezone": report["collection_timezone"],
        "snapshot_count": report["snapshot_count"],
        "first_collection_utc": report["first_collection_utc"],
        "last_collection_utc": report["last_collection_utc"],
        "model_sha256": report["model_sha256"],
        "training_start": report["training_start"],
        "training_end_exclusive": report["training_end_exclusive"],
        "history_rule": report["history_rule"],
        "target_rule": report["target_rule"],
        "overall": overall,
        "by_train": report["by_train"],
        "exclusions": report["exclusions"],
        "limitations": report["limitations"],
        "deployment_decision": (
            "Automatic model predictions for live trains remain disabled."
        ),
    }

    output = PROJECT / "docs/live_evaluations" / f"{args.date}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")

    print(f"Saved: {output}")
    print(f"Eligible examples: {overall['examples']}")
    print(f"Persistence MAE: {overall['persistence_mae']:.4f}")
    print(f"Model MAE: {overall['model_mae']:.4f}")


if __name__ == "__main__":
    main()