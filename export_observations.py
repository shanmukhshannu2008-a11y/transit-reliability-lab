"""Convert saved snapshots to traceable observations; never request live data."""
import argparse
import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from transit_fields import parse_lateness

PROJECT = Path(__file__).resolve().parent
FIELDS = [
    "source_file", "record_index", "collected_at", "train_number", "line",
    "current_stop", "next_stop", "raw_late_json", "reported_delay",
    "status", "quality_flags",
]


def snapshot_rows(path):
    """One row per matching train record. Preserve repeated observations."""
    with path.open(encoding="utf-8") as file:
        snapshot = json.load(file)
    if not isinstance(snapshot, dict):
        raise ValueError(f"{path.name}: expected a snapshot object")
    timestamp = snapshot.get("collected_at")
    if not isinstance(timestamp, str):
        raise ValueError(f"{path.name}: missing collection timestamp")
    try:
        parsed_time = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ValueError(f"{path.name}: invalid collection timestamp") from exc
    if parsed_time.utcoffset() is None:
        raise ValueError(f"{path.name}: collection timestamp needs a timezone")
    trains = snapshot.get("trains")
    if not isinstance(trains, list):
        raise ValueError(f"{path.name}: expected a trains list")

    rows = []
    for index, train in enumerate(trains):
        if not isinstance(train, dict):
            raise ValueError(f"{path.name}: record {index} is not an object")
        line = str(train.get("line") or "")
        if "paoli" not in line.lower() and "thorndale" not in line.lower():
            continue
        raw_late = train.get("late")
        parsed = parse_lateness(raw_late)
        flags = []
        if not str(train.get("currentstop") or "").strip():
            flags.append("missing_current_stop")
        if not str(train.get("trainno") or "").strip():
            flags.append("missing_train_number")
        if parsed["status"] == "cancelled_or_suspended":
            flags.append("historical_status_interpretation_999")
        elif parsed["status"] == "unknown":
            flags.append("unknown_lateness")
        rows.append({
            "source_file": path.name,
            "record_index": index,
            "collected_at": timestamp,
            "train_number": str(train.get("trainno") or ""),
            "line": line,
            "current_stop": train.get("currentstop") or "",
            "next_stop": train.get("nextstop") or "",
            "raw_late_json": json.dumps(raw_late),
            "reported_delay": parsed["reported_delay"],
            "status": parsed["status"],
            "quality_flags": "|".join(flags),
        })
    return rows


def export_observations(input_dir, output_path):
    paths = sorted(input_dir.glob("trainview_*.json"))
    if not paths:
        raise ValueError(f"No trainview snapshots found in {input_dir}")
    # Validate everything before replacing any previous export.
    rows = [row for path in paths for row in snapshot_rows(path)]
    rows.sort(key=lambda row: (
        datetime.fromisoformat(row["collected_at"]),
        row["source_file"], row["record_index"],
    ))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="",
            dir=output_path.parent, delete=False,
        ) as file:
            temporary = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return len(paths), rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=PROJECT / "data/raw")
    parser.add_argument("--output", type=Path,
                        default=PROJECT / "data/processed/observations.csv")
    args = parser.parse_args()
    try:
        count, rows = export_observations(args.input_dir, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Export failed: {exc}\n")
    print(f"Snapshots read: {count}")
    print(f"Paoli/Thorndale observations: {len(rows)}")
    print(f"Flagged observations: {sum(bool(row['quality_flags']) for row in rows)}")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
