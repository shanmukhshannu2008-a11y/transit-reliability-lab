"""Audit saved feed coverage; collection timestamps are not arrival times."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from export_observations import PROJECT, snapshot_rows

LOCAL = ZoneInfo("America/New_York")


def audit(input_dir, gap_seconds=180):
    if gap_seconds < 1:
        raise ValueError("Gap threshold must be positive")
    paths = sorted(input_dir.glob("trainview_*.json"))
    if not paths:
        raise ValueError(f"No snapshots found in {input_dir}")
    records = []
    for path in paths:
        rows = snapshot_rows(path)  # Reuse snapshot validation and field interpretation.
        with path.open(encoding="utf-8") as file:
            stamp = json.load(file)["collected_at"]
        records.append((datetime.fromisoformat(stamp).astimezone(timezone.utc), path.name, rows))
    records.sort(key=lambda record: (record[0], record[1]))
    days = defaultdict(list)
    gaps = []
    for index, record in enumerate(records):
        days[record[0].astimezone(LOCAL).date().isoformat()].append(record)
        if index:
            before = records[index - 1]
            seconds = (record[0] - before[0]).total_seconds()
            gaps.append({"from_file": before[1], "to_file": record[1],
                         "seconds": seconds, "over_threshold": seconds > gap_seconds})
    daily = []
    for date, items in sorted(days.items()):
        rows = [row for _, _, batch in items for row in batch]
        intervals = [(right[0] - left[0]).total_seconds()
                     for left, right in zip(items, items[1:])]
        daily.append({
            "local_date": date,
            "snapshots": len(items),
            "snapshots_without_matching_trains": sum(not batch for _, _, batch in items),
            "observations": len(rows),
            "distinct_train_numbers": len({r["train_number"] for r in rows if r["train_number"]}),
            "first_collection": items[0][0].astimezone(LOCAL).isoformat(),
            "last_collection": items[-1][0].astimezone(LOCAL).isoformat(),
            "elapsed_span_seconds": (items[-1][0] - items[0][0]).total_seconds(),
            "largest_within_day_gap_seconds": max(intervals) if intervals else None,
            "statuses": dict(Counter(r["status"] for r in rows)),
            "flagged_observations": sum(bool(r["quality_flags"]) for r in rows),
        })
    return {
        "timezone": "America/New_York",
        "date_definition": "Local collection date, not verified transit service date",
        "gap_threshold_seconds": gap_seconds,
        "gap_definition": "Strictly greater than threshold; a project diagnostic, not a SEPTA guarantee",
        "snapshots": len(records),
        "observations": sum(day["observations"] for day in daily),
        "duplicate_collection_timestamps": len(records) - len({r[0] for r in records}),
        "days": daily,
        "consecutive_snapshot_gaps": gaps,
        "limitations": [
            "Elapsed spans include unobserved gaps; they are not continuous monitoring time.",
            "Repeated observations are retained and may not be statistically independent.",
            "Train numbers are not verified journey identifiers.",
            "Statuses inherit the current parser, not a complete verified status specification.",
            "No actual arrivals or prediction accuracy are established by this report.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=PROJECT / "data/raw")
    parser.add_argument("--output", type=Path, default=PROJECT / "data/processed/coverage.json")
    parser.add_argument("--gap-seconds", type=int, default=180)
    args = parser.parse_args()
    try:
        report = audit(args.input_dir, args.gap_seconds)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Audit failed: {exc}\n")
    print(f"Snapshots: {report['snapshots']} | Observations: {report['observations']}")
    for day in report["days"]:
        print(f"\n{day['local_date']} (America/New_York): "
              f"{day['snapshots']} snapshots, {day['observations']} observations, "
              f"{day['distinct_train_numbers']} distinct train numbers")
        print(f"  First: {day['first_collection']} | Last: {day['last_collection']}")
        print(f"  Elapsed span: {day['elapsed_span_seconds'] / 60:.2f} minutes (includes gaps)")
        print(f"  Largest within-day gap: {day['largest_within_day_gap_seconds']} seconds")
        print(f"  Statuses: {day['statuses']} | Flagged: {day['flagged_observations']}")
    long_gaps = sum(gap["over_threshold"] for gap in report["consecutive_snapshot_gaps"])
    print(f"\nGaps over {args.gap_seconds} seconds: {long_gaps}")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
