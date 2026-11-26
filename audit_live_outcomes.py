"""Audit outcome availability in saved snapshots; no model scoring."""

from collections import Counter
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(__file__).resolve().parent
TARGET_DATE = date(2026, 11, 26)
ZONE = ZoneInfo("America/New_York")


def numeric(value):
    return type(value) is int and 0 <= value <= 997


def load_snapshots():
    snapshots = []

    for path in (PROJECT / "data/raw").glob("trainview_*.json"):
        data = json.loads(path.read_text())
        timestamp = datetime.fromisoformat(data["collected_at"])

        if timestamp.tzinfo is None:
            raise ValueError("Collection timestamp must include a timezone.")

        if timestamp.astimezone(ZONE).date() != TARGET_DATE:
            continue

        matching = {}

        for train in data["trains"]:
            line = str(train.get("line") or "").lower()
            if "paoli" not in line and "thorndale" not in line:
                continue

            number = str(train.get("trainno") or "")
            if not number or number in matching:
                raise ValueError("Missing or duplicate train number.")

            matching[number] = train.get("late")

        snapshots.append((timestamp, matching))

    snapshots.sort(key=lambda item: item[0])

    if not snapshots:
        raise ValueError("No snapshots found for the selected date.")

    times = [timestamp for timestamp, _ in snapshots]
    if len(times) != len(set(times)):
        raise ValueError("Duplicate collection timestamps.")

    return snapshots


def retained_keys(snapshots):
    """Approximate change-only retention, resetting after absence or gaps."""
    retained = set()
    previous = {}
    previous_time = None

    for timestamp, trains in snapshots:
        if (
            previous_time is not None
            and (timestamp - previous_time).total_seconds() > 180
        ):
            previous = {}

        for number, value in trains.items():
            if (
                number not in previous
                or type(value) is not type(previous[number])
                or value != previous[number]
            ):
                retained.add((timestamp, number))

        previous = trains
        previous_time = timestamp

    return retained


def classify(snapshots, index, number, retained, change_only):
    anchor_time = snapshots[index][0]
    lower = anchor_time + timedelta(minutes=8)
    upper = anchor_time + timedelta(minutes=12)

    if snapshots[-1][0] < upper:
        return "collection_ended_before_12_minutes"

    # Require continuous observed presence through the first poll at/after +12.
    # This is deliberately stricter than the historical matching rule.
    followup = []
    previous_time = anchor_time

    for timestamp, trains in snapshots[index + 1:]:
        if (
            (timestamp - previous_time).total_seconds() > 180
            or number not in trains
        ):
            return "interrupted_followup"

        followup.append((timestamp, trains[number]))
        previous_time = timestamp

        if timestamp >= upper:
            break

    for timestamp, value in followup:
        if not lower <= timestamp <= upper:
            continue

        if change_only and (timestamp, number) not in retained:
            continue

        # Choose the first qualifying report BEFORE checking its status.
        if not numeric(value):
            return "nonnumeric_outcome"

        if any(
            not numeric(earlier_value)
            for earlier_time, earlier_value in followup
            if earlier_time < timestamp
        ):
            return "intervening_special_or_unknown"

        return "numeric_outcome_available"

    return "no_update_in_8_to_12_minute_window"


def main():
    snapshots = load_snapshots()
    retained = retained_keys(snapshots)

    print(f"Date: {TARGET_DATE} | Snapshots: {len(snapshots)}")
    print("Full 12-minute follow-up required for this diagnostic.")

    for label, change_only in [
        ("Every-snapshot sampling", False),
        ("Change-only sampling", True),
    ]:
        counts = Counter()

        for index, (timestamp, trains) in enumerate(snapshots):
            for number, value in trains.items():
                if not numeric(value):
                    continue
                if change_only and (timestamp, number) not in retained:
                    continue

                result = classify(
                    snapshots, index, number, retained, change_only
                )
                counts[result] += 1

        print(f"\n{label}")
        print(f"Numeric anchors: {sum(counts.values())}")

        for reason, count in sorted(counts.items()):
            print(f"  {reason}: {count}")

    print(
        "\nSampling methods have different anchor sets. "
        "These counts measure availability, not prediction accuracy. "
        "Collection times are not verified source-observation times."
    )


if __name__ == "__main__":
    main()