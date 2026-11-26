"""Compare full and change-only sampling on saved live snapshots."""

from collections import Counter
from datetime import date, datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(__file__).resolve().parent
TARGET_DATE = date(2026, 11, 26)
LOCAL_ZONE = ZoneInfo("America/New_York")
MAX_COLLECTION_GAP_SECONDS = 180


def trend(previous, current):
    """Use the same numeric and 30-minute history rules as our model."""
    if previous is None:
        return "missing"

    previous_time, previous_delay = previous
    current_time, current_delay = current
    age = (current_time - previous_time).total_seconds()

    if (
        type(previous_delay) is not int
        or not 0 <= previous_delay <= 997
        or not 0 < age <= 1800
    ):
        return "missing"

    if current_delay > previous_delay:
        return "rising"
    if current_delay < previous_delay:
        return "falling"
    return "unchanged"


def numeric(value):
    return type(value) is int and 0 <= value <= 997


def main():
    snapshots = []

    for path in (PROJECT / "data/raw").glob("trainview_*.json"):
        snapshot = json.loads(path.read_text())
        timestamp = datetime.fromisoformat(snapshot["collected_at"])

        if timestamp.tzinfo is None:
            raise ValueError(f"Missing timestamp timezone: {path.name}")

        if timestamp.astimezone(LOCAL_ZONE).date() == TARGET_DATE:
            snapshots.append((timestamp, snapshot["trains"]))

    snapshots.sort(key=lambda item: item[0])

    if not snapshots:
        raise ValueError(f"No saved snapshots for {TARGET_DATE}")

    timestamps = [timestamp for timestamp, _ in snapshots]
    if len(set(timestamps)) != len(timestamps):
        raise ValueError("Duplicate collection timestamps need review.")

    previous_full = {}
    previous_retained = {}
    last_snapshot_time = None

    sequences = {}
    full_categories = Counter()
    retained_categories = Counter()
    counts = Counter()

    for timestamp, trains in snapshots:
        if (
            last_snapshot_time is not None
            and (timestamp - last_snapshot_time).total_seconds()
            > MAX_COLLECTION_GAP_SECONDS
        ):
            previous_full.clear()
            previous_retained.clear()

        present = set()

        for train in trains:
            line = str(train.get("line") or "").lower()
            if "paoli" not in line and "thorndale" not in line:
                continue

            number = str(train.get("trainno") or "")
            if not number or number in present:
                raise ValueError("Missing or duplicate train number in snapshot.")
            present.add(number)

            raw = train.get("late")
            current = (timestamp, raw)
            previous = previous_full.get(number)
            retained = previous_retained.get(number)

            counts["reports"] += 1
            sequences.setdefault(number, []).append(raw)

            # Preserve changes in raw type as well as raw value.
            keep = (
                retained is None
                or type(raw) is not type(retained[1])
                or raw != retained[1]
            )

            if numeric(raw):
                full_trend = trend(previous, current)
                full_categories[full_trend] += 1

                if keep:
                    retained_trend = trend(retained, current)
                    retained_categories[retained_trend] += 1
                    counts["common_numeric_anchors"] += 1

                    if full_trend != retained_trend:
                        counts["category_disagreements"] += 1

            if keep:
                counts["retained_reports"] += 1
                previous_retained[number] = current
            else:
                counts["omitted_unchanged_reports"] += 1

            previous_full[number] = current

        # Do not carry history across a train's absence from a snapshot.
        previous_full = {
            key: value for key, value in previous_full.items()
            if key in present
        }
        previous_retained = {
            key: value for key, value in previous_retained.items()
            if key in present
        }
        last_snapshot_time = timestamp

    print(f"Local collection date: {TARGET_DATE}")
    print(f"Snapshots: {len(snapshots)}")

    for number, values in sorted(sequences.items()):
        print(f"Train {number}: " + " → ".join(map(str, values)))

    print(f"\nReports: {counts['reports']}")
    print(f"Change-only retained: {counts['retained_reports']}")
    print(f"Unchanged reports omitted: {counts['omitted_unchanged_reports']}")

    print(f"\nAll numeric reports — history categories: {dict(full_categories)}")
    print(
        "Retained numeric reports — history categories: "
        f"{dict(retained_categories)}"
    )

    print(
        "\nSame-anchor comparison: "
        f"{counts['category_disagreements']} category disagreements among "
        f"{counts['common_numeric_anchors']} retained numeric anchors."
    )

    print(
        "\nDiagnostic only: collection time is not source observation time. "
        "This short sample cannot establish historical/live compatibility. "
        "No predictions, model training, or network requests performed."
    )


if __name__ == "__main__":
    main()