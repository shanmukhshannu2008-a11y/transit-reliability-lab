"""Evaluate a saved model on a selected local collection date."""

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
from statistics import mean

from audit_live_outcomes import numeric
from audit_live_target import match_live_target
from live_snapshot_data import load_snapshots_for_date
from predict_delay import prepare_features
from prediction_runtime import MODEL_PATH, load_model


PROJECT = Path(__file__).resolve().parent


def summarize(rows):
    if not rows:
        return {
            "examples": 0,
            "persistence_mae": None,
            "model_mae": None,
        }

    return {
        "examples": len(rows),
        "persistence_mae": mean(
            abs(row["current_delay"] - row["outcome_delay"])
            for row in rows
        ),
        "model_mae": mean(
            abs(row["prediction"] - row["outcome_delay"])
            for row in rows
        ),
    }


def evaluate(snapshots, model):
    examples = []
    exclusions = Counter()

    for index, (timestamp, trains) in enumerate(snapshots):
        for number, current in trains.items():
            if not numeric(current):
                exclusions["invalid_anchor"] += 1
                continue

            previous = None
            gap_minutes = None

            if index > 0:
                previous_time, previous_trains = snapshots[index - 1]
                gap_seconds = (timestamp - previous_time).total_seconds()

                if (
                    number in previous_trains
                    and 0 < gap_seconds <= 180
                    and numeric(previous_trains[number])
                ):
                    previous = previous_trains[number]
                    gap_minutes = gap_seconds / 60

            features = prepare_features(current, previous, gap_minutes)
            prediction = model.predict(features)

            outcome = match_live_target(snapshots, index, number)

            if outcome["status"] != "eligible":
                exclusions[outcome["status"]] += 1
                continue

            examples.append({
                "train": number,
                "anchor_utc": timestamp.isoformat(),
                "current_delay": current,
                "previous_delay": previous,
                "previous_gap_minutes": gap_minutes,
                "history_category": features["trend"],
                "prediction": prediction,
                "outcome_utc": outcome["outcome_time"].isoformat(),
                "outcome_delay": outcome["outcome_delay"],
                "horizon_minutes": outcome["horizon_minutes"],
            })

    return examples, dict(exclusions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        required=True,
        type=date.fromisoformat,
        help="Local collection date, YYYY-MM-DD (America/New_York)",
    )
    args = parser.parse_args()

    try:
        snapshots = load_snapshots_for_date(args.date)
        model = load_model()
        examples, exclusions = evaluate(snapshots, model)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Evaluation failed: {error}\n")

    overall = summarize(examples)
    by_train = {
        number: summarize([
            row for row in examples if row["train"] == number
        ])
        for number in sorted({row["train"] for row in examples})
    }

    report = {
        "collection_date": str(args.date),
        "collection_timezone": "America/New_York",
        "snapshot_count": len(snapshots),
        "first_collection_utc": snapshots[0][0].isoformat(),
        "last_collection_utc": snapshots[-1][0].isoformat(),
        "model_sha256": hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(),
        "training_start": model.training_start,
        "training_end_exclusive": model.training_end_exclusive,
        "history_rule": (
            "Immediately previous collected snapshot; reset after absence "
            "or gap over 180 seconds; invalid previous values treated as missing."
        ),
        "target_rule": (
            "First collected report at/after 10 minutes, accepted through 12; "
            "requires uninterrupted full-window follow-up."
        ),
        "overall": overall,
        "by_train": by_train,
        "exclusions": exclusions,
        "examples": examples,
        "limitations": [
            "All snapshots from one local date; may contain multiple sessions.",
            "Overlapping examples are not independent journeys.",
            "Historical training and live sampling differ.",
            "Collection time is not verified source-observation time.",
            "No retraining or historical test-set evaluation.",
        ],
    }

    output = (
        PROJECT / "data/processed/live_evaluations"
        / f"{args.date}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")

    print(f"Collection date: {args.date}")
    print(f"Snapshots: {len(snapshots)}")
    print("\nOverall:")
    print(json.dumps(overall, indent=2))

    print("\nBy train:")
    for number, scores in by_train.items():
        print(f"Train {number}: {scores}")

    print("\nExcluded anchors:")
    print(json.dumps(exclusions, indent=2))
    print(f"\nSaved: {output}")
    print("No retraining or network requests performed.")


if __name__ == "__main__":
    main()