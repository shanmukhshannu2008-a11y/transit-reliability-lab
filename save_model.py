"""Save and reload the median-change model, then verify predictions."""

from datetime import date
import json
import math
from pathlib import Path

import duckdb

from baseline_delay import PROJECT, EXPECTED_SHA, build_pairs
from train_delay_model import (
    FEATURE_POLICY,
    MedianChangeModel,
    feature_rows,
    load_development,
)


MODEL_PATH = PROJECT / "models/median_change_v1.json"


def save_model(model, path):
    artifact = {
        "schema_version": 1,
        "model_type": "median_change",
        "training_start": "2025-12-01",
        "training_end_exclusive": "2025-12-05",
        "archive_sha256": EXPECTED_SHA,
        "feature_policy": FEATURE_POLICY,
        "use_history": model.use_history,
        "minimum_cell_examples": model.min_count,
        "parameters": model.parameters(),
        "scope": "Future reported delay, not verified arrival time",
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n")


def load_model(path):
    """Restore learned parameters. No archive or training is needed here."""
    artifact = json.loads(path.read_text())

    if (
        artifact["schema_version"] != 1
        or artifact["model_type"] != "median_change"
    ):
        raise ValueError("Unsupported model format.")

    if artifact["feature_policy"] != FEATURE_POLICY:
        raise ValueError("Saved feature rules differ from the current code.")

    if artifact["use_history"] is not True:
        raise ValueError("This loader expects the history-enabled model.")

    minimum = artifact["minimum_cell_examples"]
    if type(minimum) is not int or minimum < 1:
        raise ValueError("Invalid minimum example count.")

    def numeric(value):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Model changes must be finite numbers.")
        return value

    parameters = artifact["parameters"]
    model = MedianChangeModel(use_history=True, min_count=minimum)
    model.global_change = numeric(parameters["global_change"])
    model.bins = {}
    model.cells = {}

    for key, value in parameters["delay_bin_changes"].items():
        if key not in {"0", "1", "2", "3", "4"}:
            raise ValueError("Invalid delay bin.")
        model.bins[int(key)] = numeric(value)

    for key, value in parameters["history_cell_changes"].items():
        bin_text, trend = key.split(":")

        if bin_text not in {"0", "1", "2", "3", "4"}:
            raise ValueError("Invalid history-cell delay bin.")

        if trend not in {"falling", "unchanged", "rising", "missing"}:
            raise ValueError("Invalid history-cell trend.")

        model.cells[(int(bin_text), trend)] = numeric(value)

    return model


def main():
    archive = PROJECT / "data/raw/historical-review/2025.parquet"

    with duckdb.connect() as connection:
        load_development(connection, archive)
        build_pairs(connection)
        rows = feature_rows(connection)

    training = [
        row for row in rows
        if date(2025, 12, 1) <= row["day"] < date(2025, 12, 5)
    ]
    validation = [
        row for row in rows
        if row["day"] == date(2025, 12, 5)
    ]

    if not training or not validation:
        raise ValueError("Training and validation examples are required.")

    original = MedianChangeModel(use_history=True).fit(training)
    save_model(original, MODEL_PATH)

    restored = load_model(MODEL_PATH)

    for row in validation:
        before = original.predict(row)
        after = restored.predict(row)

        if before != after:
            raise AssertionError(
                f"Prediction changed after loading: {before} versus {after}"
            )

    print(f"Training examples: {len(training):,}")
    print(f"Saved model: {MODEL_PATH}")
    print(
        f"Save/load check passed: identical predictions on "
        f"{len(validation):,} validation examples."
    )
    print("Reserved test dates NOT used.")


if __name__ == "__main__":
    main()