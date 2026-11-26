"""Load saved Paoli/Thorndale snapshots for a local collection date."""

from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(__file__).resolve().parent
LOCAL_ZONE = ZoneInfo("America/New_York")


def load_snapshots_for_date(target_date):
    snapshots = []

    for path in (PROJECT / "data/raw").glob("trainview_*.json"):
        data = json.loads(path.read_text())
        timestamp = datetime.fromisoformat(data["collected_at"])

        if timestamp.tzinfo is None:
            raise ValueError(f"Missing timezone: {path.name}")

        if timestamp.astimezone(LOCAL_ZONE).date() != target_date:
            continue

        trains = data["trains"]
        if not isinstance(trains, list):
            raise ValueError(f"Expected a train list: {path.name}")

        matching = {}

        for train in trains:
            if not isinstance(train, dict):
                raise ValueError(f"Malformed train record: {path.name}")

            line = str(train.get("line") or "").lower()
            if "paoli" not in line and "thorndale" not in line:
                continue

            number = str(train.get("trainno") or "")
            if not number or number in matching:
                raise ValueError(
                    f"Missing or duplicate train number: {path.name}"
                )

            matching[number] = train.get("late")

        # Preserve empty matching snapshots: absence matters to follow-up.
        snapshots.append((timestamp, matching))

    snapshots.sort(key=lambda item: item[0])

    if not snapshots:
        raise ValueError(f"No snapshots found for {target_date}")

    times = [timestamp for timestamp, _ in snapshots]
    if len(times) != len(set(times)):
        raise ValueError("Duplicate collection timestamps need review.")

    return snapshots