import json
from pathlib import Path
from transit_fields import parse_lateness
import argparse

parser = argparse.ArgumentParser(
    description="Inspect a train across saved SEPTA snapshots."
)
parser.add_argument(
    "train_number",
    help="Train number to inspect, for example 9517",
)

args = parser.parse_args()
target_train = args.train_number

data_folder = Path(__file__).resolve().parent / "data" / "raw"
snapshot_files = sorted(data_folder.glob("trainview_*.json"))

print(f"Following train {target_train}")

for snapshot_file in snapshot_files:
    with snapshot_file.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)

    found = False

    for train in snapshot["trains"]:
        if str(train.get("trainno")) == target_train:
            found = True
            lateness = parse_lateness(train.get("late"))

            print(
                f"{snapshot['collected_at']} | "
                f"Current: {train.get('currentstop')} | "
                f"Raw late: {train.get('late')} | "
                f"Parsed delay: {lateness['reported_delay']} | "
                f"Status: {lateness['status']}"
            )

    if not found:
        print(f"{snapshot['collected_at']} | Not present in snapshot")
