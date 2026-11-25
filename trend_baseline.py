"""Compare recent-trend extrapolation with existing development models."""

from datetime import timedelta
import json

import duckdb

from baseline_delay import PROJECT, build_pairs
from train_delay_model import (
    load_development,
    feature_rows,
    MedianChangeModel,
    evaluate,
)
from walk_forward import START, FIRST_VALIDATION, END


def predict_trend(row):
    previous = row["previous_delay"]
    age = row["previous_age_seconds"]

    if (
        previous is None
        or not 0 <= previous <= 997
        or age is None
        or not 0 < age <= 1800
    ):
        return row["initial"]

    elapsed_minutes = age / 60
    rate = (row["initial"] - previous) / elapsed_minutes

    # Fixed 10 minutes: never use the actual future update time.
    return max(0, row["initial"] + rate * 10)


def load_rows():
    archive = PROJECT / "data/raw/historical-review/2025.parquet"

    with duckdb.connect() as connection:
        load_development(connection, archive, start=START)
        build_pairs(connection)
        rows = feature_rows(connection)

        history = connection.execute(
            """
            SELECT
                service_date,
                train_number,
                stamp,
                lag(lateness) OVER history_window AS previous_delay,
                epoch(
                    stamp - lag(stamp) OVER history_window
                ) AS previous_age_seconds
            FROM observations
            WINDOW history_window AS (
                PARTITION BY service_date, train_number
                ORDER BY stamp
            )
            """
        ).fetchall()

    lookup = {
        (day, train, stamp): (previous, age)
        for day, train, stamp, previous, age in history
    }

    for row in rows:
        key = (row["day"], row["train"], row["stamp"])
        previous, age = lookup[key]
        row["previous_delay"] = previous
        row["previous_age_seconds"] = age

    return rows


def run():
    rows = load_rows()
    folds = []
    day = FIRST_VALIDATION

    while day < END:
        training = [row for row in rows if START <= row["day"] < day]
        validation = [row for row in rows if row["day"] == day]

        if not training or not validation:
            raise ValueError(f"Missing examples for {day}")

        model = MedianChangeModel(True).fit(training)

        predictors = {
            "persistence": lambda row: row["initial"],
            "recent_trend": predict_trend,
            "learned_history": model.predict,
        }

        scores = {
            name: evaluate(validation, predictor)
            for name, predictor in predictors.items()
        }

        folds.append({
            "date": str(day),
            "pairs": len(validation),
            "metrics": scores,
        })

        print(
            f"{day} | n={len(validation)} | "
            f"persistence={scores['persistence']['mae_minutes']:.3f} | "
            f"trend={scores['recent_trend']['mae_minutes']:.3f} | "
            f"learned={scores['learned_history']['mae_minutes']:.3f}"
        )

        day += timedelta(days=1)

    total_pairs = sum(fold["pairs"] for fold in folds)
    pooled = {}

    for name in predictors:
        total_error = sum(
            fold["metrics"][name]["mae_minutes"] * fold["pairs"]
            for fold in folds
        )
        pooled[name] = total_error / total_pairs

    report = {
        "forecast_minutes": 10,
        "maximum_history_age_minutes": 30,
        "fallback": "Persistence for unavailable or invalid history",
        "prediction_floor": 0,
        "rate_clipping": "None",
        "scope": "Conditional reported delay at an observed 8–12 minute update",
        "test_dates": "December 6–7 excluded",
        "validation_pairs": total_pairs,
        "pooled_mae_minutes": pooled,
        "folds": folds,
    }

    output = PROJECT / "data/processed/trend_baseline.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")

    print("\nPooled MAE in minutes:")
    for name, mae in pooled.items():
        print(f"{name}: {mae:.4f}")

    print(f"\nSaved: {output}")
    print("Reserved test dates NOT scored.")


if __name__ == "__main__":
    run()