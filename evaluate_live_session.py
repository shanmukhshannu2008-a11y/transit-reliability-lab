"""Evaluate the saved model on recorded live snapshots without retraining."""

from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import mean

from audit_live_outcomes import load_snapshots, numeric, TARGET_DATE
from audit_live_target import match_live_target
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


def main():
    snapshots = load_snapshots()
    model = load_model()
    examples = []
    exclusions = Counter()

    for index, (timestamp, trains) in enumerate(snapshots):
        for number, current in trains.items():
            if not numeric(current):
                exclusions["invalid_anchor"] += 1
                continue

            # Construct the prediction using only information available now.
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

            features = prepare_features(
                current,
                previous,
                gap_minutes,
            )
            prediction = model.predict(features)

            # Future reports are used only to determine eligibility and error.
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

    overall = summarize(examples)
    by_train = {
        number: summarize([
            row for row in examples if row["train"] == number
        ])
        for number in sorted({row["train"] for row in examples})
    }

    report = {
        "collection_date": str(TARGET_DATE),
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
        "exclusions": dict(exclusions),
        "examples": examples,
        "limitations": [
            "Retrospective evaluation of one short recorded session.",
            "Overlapping examples are not independent journeys.",
            "Historical training and live sampling differ.",
            "Collection time is not verified source-observation time.",
            "No retraining; reserved historical test dates remain unscored.",
        ],
    }

    output = PROJECT / "data/processed/live_session_evaluation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")

    print(f"Collection date: {TARGET_DATE}")
    print("\nOverall:")
    print(json.dumps(overall, indent=2))

    print("\nBy train:")
    for number, scores in by_train.items():
        print(f"Train {number}: {scores}")

    print("\nExcluded anchors:")
    print(json.dumps(dict(exclusions), indent=2))
    print(f"\nSaved: {output}")
    print("No retraining or network requests performed.")


if __name__ == "__main__":
    main()