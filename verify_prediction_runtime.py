"""Compare the lightweight runtime with the original saved-model loader."""

from datetime import date

import duckdb

from baseline_delay import PROJECT, build_pairs
from train_delay_model import load_development, feature_rows
from save_model import load_model as load_original
from prediction_runtime import MODEL_PATH, load_model as load_runtime


def main():
    original = load_original(MODEL_PATH)
    runtime = load_runtime(MODEL_PATH)

    archive = PROJECT / "data/raw/historical-review/2025.parquet"

    with duckdb.connect() as connection:
        load_development(connection, archive)
        build_pairs(connection)
        rows = feature_rows(connection)

    validation = [
        row for row in rows
        if row["day"] == date(2025, 12, 5)
    ]

    if len(validation) != 8238:
        raise ValueError(
            f"Expected 8,238 validation examples; found {len(validation):,}."
        )

    for row in validation:
        expected = original.predict(row)
        actual = runtime.predict(row)

        if expected != actual:
            raise AssertionError(
                f"Prediction mismatch for train {row['train']} "
                f"at {row['stamp']}: {expected} versus {actual}"
            )

    print(
        f"Runtime verification passed: "
        f"{len(validation):,} identical predictions."
    )
    print("No retraining performed. Reserved test dates not used.")


if __name__ == "__main__":
    main()