"""Compare outcome labels on identical retained live anchors."""

from collections import Counter
from datetime import timedelta

from audit_live_outcomes import (
    TARGET_DATE,
    load_snapshots,
    retained_keys,
    numeric,
    classify,
)


def first_outcome(snapshots, index, number, retained, change_only):
    anchor_time = snapshots[index][0]
    lower = anchor_time + timedelta(minutes=8)
    upper = anchor_time + timedelta(minutes=12)

    for timestamp, trains in snapshots[index + 1:]:
        if timestamp > upper:
            break

        if timestamp < lower or number not in trains:
            continue

        if change_only and (timestamp, number) not in retained:
            continue

        return timestamp, trains[number]

    return None


def main():
    snapshots = load_snapshots()
    retained = retained_keys(snapshots)

    counts = Counter()
    exclusions = Counter()
    differences = []

    for index, (anchor_time, trains) in enumerate(snapshots):
        for number, value in trains.items():
            if not numeric(value) or (anchor_time, number) not in retained:
                continue

            counts["common_numeric_anchors"] += 1

            full_status = classify(
                snapshots, index, number, retained, False
            )
            change_status = classify(
                snapshots, index, number, retained, True
            )

            if (
                full_status != "numeric_outcome_available"
                or change_status != "numeric_outcome_available"
            ):
                exclusions[(full_status, change_status)] += 1
                continue

            full = first_outcome(
                snapshots, index, number, retained, False
            )
            change = first_outcome(
                snapshots, index, number, retained, True
            )

            if full is None or change is None:
                raise AssertionError("Eligible outcome unexpectedly missing.")

            counts["both_outcomes_available"] += 1

            different_time = full[0] != change[0]
            different_delay = full[1] != change[1]

            counts["different_outcome_times"] += int(different_time)
            counts["different_outcome_delays"] += int(different_delay)

            if different_time or different_delay:
                differences.append({
                    "train": number,
                    "anchor_utc": anchor_time.isoformat(),
                    "current_delay": value,
                    "full_horizon_minutes": round(
                        (full[0] - anchor_time).total_seconds() / 60, 2
                    ),
                    "full_outcome_delay": full[1],
                    "change_horizon_minutes": round(
                        (change[0] - anchor_time).total_seconds() / 60, 2
                    ),
                    "change_outcome_delay": change[1],
                })

    print(f"Collection date: {TARGET_DATE}")
    print(f"Common numeric anchors: {counts['common_numeric_anchors']}")
    print(f"Both outcomes available: {counts['both_outcomes_available']}")
    print(f"Different outcome times: {counts['different_outcome_times']}")
    print(f"Different outcome delays: {counts['different_outcome_delays']}")

    print("\nExcluded anchors, grouped by reason:")
    for (full_status, change_status), count in sorted(exclusions.items()):
        print(
            f"  {count}: full={full_status}; change_only={change_status}"
        )

    print("\nExamples with different matched outcomes:")
    if not differences:
        print("None in this session.")
    else:
        for example in differences[:10]:
            print(example)

    print(
        "\nDiagnostic only. Same conservative follow-up rules as the audit. "
        "No training or prediction scoring performed."
    )


if __name__ == "__main__":
    main()