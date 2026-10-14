import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
def quality_flags(train: dict) -> list[str]:
    flags = []

    if not str(train.get("currentstop") or "").strip():
        flags.append("missing_current_stop")

    if train.get("late") in (999, "999"):
        flags.append("unverified_late_999")

    return flags

assert quality_flags({"currentstop": "Devon", "late": 1}) == []

assert quality_flags({"currentstop": "", "late": 999}) == [
    "missing_current_stop",
    "unverified_late_999",
]

assert quality_flags({"late": 0}) == ["missing_current_stop"]

print("Quality checks passed!")
# 1. Request SEPTA's train data.
url = "https://www3.septa.org/api/TrainView/index.php"

with urlopen(url, timeout=20) as response:
    trains = json.load(response)

if not isinstance(trains, list):
    raise ValueError("Expected SEPTA to return a list of trains.")

collected_at = datetime.now(timezone.utc)

# 2. Save the entire snapshot so we can inspect it again later.
data_folder = Path(__file__).resolve().parent / "data" / "raw"
data_folder.mkdir(parents=True, exist_ok=True)

filename = collected_at.strftime("trainview_%Y%m%dT%H%M%S_%fZ.json")
output_path = data_folder / filename

snapshot = {
    "collected_at": collected_at.isoformat(),
    "source_url": url,
    "trains": trains,
}

with output_path.open("w", encoding="utf-8") as file:
    json.dump(snapshot, file, indent=2)

# 3. Find records whose line mentions Paoli or Thorndale.
matching_trains = []

for train in trains:
    line = str(train.get("line", "")).lower()

    if "paoli" in line or "thorndale" in line:
        matching_trains.append(train)

print(f"Total train records: {len(trains)}")
print(f"Paoli/Thorndale records: {len(matching_trains)}")
print(f"Saved snapshot to: {output_path}")

for train in matching_trains:
    print("Train:", train.get("trainno"))
    print("Destination:", train.get("dest"))
    print("Current:", train.get("currentstop"))
    print("Next:", train.get("nextstop"))
    print("Reported late:", train.get("late"))

    flags = quality_flags(train)
    print("Quality flags:", flags)
    print()

if not matching_trains:
    print("No Paoli/Thorndale records in this snapshot.")