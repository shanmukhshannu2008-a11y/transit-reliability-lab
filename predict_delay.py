"""Predict reported delay from manually supplied observations."""

import argparse
import math

from prediction_runtime import MODEL_PATH, load_model, delay_bin


def prepare_features(current, previous=None, gap_minutes=None):
    if type(current) is not int or not 0 <= current <= 997:
        raise ValueError(
            "Current delay must be an integer from 0 through 997. "
            "Special-status reports cannot receive a numeric prediction."
        )

    if (previous is None) != (gap_minutes is None):
        raise ValueError(
            "Provide both previous delay and gap minutes, or neither."
        )

    if gap_minutes is not None:
        if not math.isfinite(gap_minutes) or gap_minutes <= 0:
            raise ValueError("Gap minutes must be finite and greater than zero.")

    valid_history = (
        previous is not None
        and type(previous) is int
        and 0 <= previous <= 997
        and gap_minutes <= 30
    )

    if not valid_history:
        trend = "missing"
    elif current > previous:
        trend = "rising"
    elif current < previous:
        trend = "falling"
    else:
        trend = "unchanged"

    return {
        "initial": current,
        "delay_bin": delay_bin(current),
        "trend": trend,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", type=int, required=True)
    parser.add_argument("--previous", type=int)
    parser.add_argument("--gap-minutes", type=float)
    args = parser.parse_args()

    try:
        features = prepare_features(
            args.current,
            args.previous,
            args.gap_minutes,
        )
        model = load_model(MODEL_PATH)
        prediction = model.predict(features)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Prediction failed: {error}\n")

    print(f"Current reported delay: {args.current} minutes")
    print(f"History category: {features['trend']}")
    print(f"Predicted later reported delay: {prediction:.1f} minutes")
    print(
        "Experimental estimate for an eligible stored update "
        "8–12 minutes later; not a station-arrival forecast."
    )
    print("Loaded saved model. No training or archive access performed.")


if __name__ == "__main__":
    main()