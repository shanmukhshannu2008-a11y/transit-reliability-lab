"""Audit a 10-minute live target with tolerance through 12 minutes."""

from collections import Counter
from datetime import timedelta

from audit_live_outcomes import load_snapshots, numeric, TARGET_DATE


def match_live_target(snapshots, index, number):
    anchor_time, anchor_trains = snapshots[index]

    if number not in anchor_trains or not numeric(anchor_trains[number]):
        return {"status": "invalid_anchor"}

    lower = anchor_time + timedelta(minutes=10)
    upper = anchor_time + timedelta(minutes=12)

    if snapshots[-1][0] < upper:
        return {"status": "collection_ended_before_12_minutes"}

    followup = []
    previous_time = anchor_time

    for timestamp, trains in snapshots[index + 1:]:
        if (
            (timestamp - previous_time).total_seconds() > 180
            or number not in trains
        ):
            return {"status": "interrupted_followup"}

        followup.append((timestamp, trains[number]))
        previous_time = timestamp

        if timestamp >= upper:
            break

    # Pick the first report in the window before checking its value.
    for timestamp, value in followup:
        if not lower <= timestamp <= upper:
            continue

        if not numeric(value):
            return {"status": "nonnumeric_outcome"}

        if any(
            not numeric(earlier_value)
            for earlier_time, earlier_value in followup
            if earlier_time < timestamp
        ):
            return {"status": "intervening_special_or_unknown"}

        return {
            "status": "eligible",
            "outcome_time": timestamp,
            "outcome_delay": value,
            "horizon_minutes": (
                timestamp - anchor_time
            ).total_seconds() / 60,
        }

    return {"status": "no_report_in_10_to_12_minute_window"}


def main():
    snapshots = load_snapshots()
    counts = Counter()
    horizons = []
    examples = []

    for index, (timestamp, trains) in enumerate(snapshots):
        for number, value in trains.items():
            if not numeric(value):
                continue

            result = match_live_target(snapshots, index, number)
            counts[result["status"]] += 1

            if result["status"] == "eligible":
                horizons.append(result["horizon_minutes"])
                examples.append({
                    "train": number,
                    "anchor_utc": timestamp.isoformat(),
                    "current_delay": value,
                    "outcome_utc": result["outcome_time"].isoformat(),
                    "outcome_delay": result["outcome_delay"],
                    "horizon_minutes": round(
                        result["horizon_minutes"], 2
                    ),
                })

    print(f"Collection date: {TARGET_DATE}")
    print(f"Numeric anchors: {sum(counts.values())}")

    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

    if horizons:
        print(
            f"\nObserved horizons: "
            f"{min(horizons):.2f}–{max(horizons):.2f} minutes"
        )
        print("\nFirst five eligible examples:")
        for example in examples[:5]:
            print(example)

    print(
        "\nUses collection timestamps and requires continuous presence "
        "through the first poll at/after 12 minutes. "
        "No training or prediction scoring performed."
    )


if __name__ == "__main__":
    main()