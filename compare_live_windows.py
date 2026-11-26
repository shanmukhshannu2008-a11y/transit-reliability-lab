"""Evaluate each continuous collection window separately."""

import argparse
from datetime import date
from zoneinfo import ZoneInfo

from evaluate_live_session import evaluate, summarize
from live_snapshot_data import load_snapshots_for_date
from prediction_runtime import load_model


LOCAL_ZONE = ZoneInfo("America/New_York")


def split_windows(snapshots):
    windows = []

    for snapshot in snapshots:
        if (
            not windows
            or (
                snapshot[0] - windows[-1][-1][0]
            ).total_seconds() > 180
        ):
            windows.append([])

        windows[-1].append(snapshot)

    return windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    args = parser.parse_args()

    snapshots = load_snapshots_for_date(args.date)
    windows = split_windows(snapshots)
    model = load_model()
    combined_examples = []

    for number, window in enumerate(windows, start=1):
        examples, exclusions = evaluate(window, model)
        combined_examples.extend(examples)
        scores = summarize(examples)

        start = window[0][0].astimezone(LOCAL_ZONE)
        end = window[-1][0].astimezone(LOCAL_ZONE)
        span = (window[-1][0] - window[0][0]).total_seconds() / 60

        print(
            f"\nWindow {number}: "
            f"{start.strftime('%H:%M:%S')}–"
            f"{end.strftime('%H:%M:%S %Z')}"
        )
        print(f"Snapshots: {len(window)} | Elapsed span: {span:.2f} minutes")
        print(f"Eligible examples: {scores['examples']}")

        if examples:
            print(f"Persistence MAE: {scores['persistence_mae']:.3f}")
            print(f"Model MAE: {scores['model_mae']:.3f}")
        else:
            print("No eligible outcomes; accuracy cannot be calculated.")

        print(f"Exclusions: {exclusions}")

    # Splitting must not change which examples are eligible.
    full_day_examples, _ = evaluate(snapshots, model)
    if combined_examples != full_day_examples:
        raise AssertionError(
            "Window splitting changed eligible examples; investigate."
        )

    print("\nConsistency check passed: eligible examples match full-day evaluation.")
    print(
        "Windows are separated by collection gaps over 180 seconds. "
        "They are not necessarily separate train journeys or independent samples."
    )


if __name__ == "__main__":
    main()