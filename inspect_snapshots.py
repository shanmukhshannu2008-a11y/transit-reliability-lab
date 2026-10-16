import json
from pathlib import Path

target_train = "9517"

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
            print(
                f"{snapshot['collected_at']} | "
                f"Current: {train.get('currentstop')} | "
                f"Next: {train.get('nextstop')} | "
                f"Reported late: {train.get('late')}"
            )

    if not found:
        print(f"{snapshot['collected_at']} | Not present in snapshot")
        