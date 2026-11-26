"""Load and use the saved model without importing training libraries."""

import json
import math
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT / "models/median_change_v1.json"

EXPECTED_POLICY = {
    "delay_bins": "0, 1–3, 4–7, 8–15, 16+",
    "history": (
        "Immediately previous stored report on same service date/train; "
        "valid numeric and at most 30 minutes old"
    ),
    "trend": "falling, unchanged, rising; otherwise missing",
    "minimum_cell_examples": 30,
    "fallback": (
        "delay-only median change, then global training median change"
    ),
    "prediction": "current delay + learned median change, floored at zero",
}


def delay_bin(value):
    return sum(value > boundary for boundary in (0, 3, 7, 15))


def finite_number(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError("Model parameters must be finite numbers.")
    return value


class SavedModel:
    def __init__(self, artifact):
        if (
            artifact["schema_version"] != 1
            or artifact["model_type"] != "median_change"
        ):
            raise ValueError("Unsupported model format.")

        if artifact["feature_policy"] != EXPECTED_POLICY:
            raise ValueError("Saved model uses unsupported feature rules.")

        if artifact["use_history"] is not True:
            raise ValueError("Expected a history-enabled model.")

        if artifact["minimum_cell_examples"] != 30:
            raise ValueError("Expected the reviewed 30-example setting.")

        parameters = artifact["parameters"]
        self.global_change = finite_number(parameters["global_change"])
        self.bins = {}
        self.cells = {}

        for key, value in parameters["delay_bin_changes"].items():
            if key not in {"0", "1", "2", "3", "4"}:
                raise ValueError("Invalid delay bin.")
            self.bins[int(key)] = finite_number(value)

        for key, value in parameters["history_cell_changes"].items():
            bin_text, trend = key.split(":")

            if bin_text not in {"0", "1", "2", "3", "4"}:
                raise ValueError("Invalid history-cell bin.")

            if trend not in {"rising", "falling", "unchanged", "missing"}:
                raise ValueError("Invalid history category.")

            self.cells[(int(bin_text), trend)] = finite_number(value)

        self.training_start = artifact["training_start"]
        self.training_end_exclusive = artifact["training_end_exclusive"]

    def predict(self, row):
        current = row["initial"]
        trend = row["trend"]

        if type(current) is not int or not 0 <= current <= 997:
            raise ValueError("Current delay must be an integer from 0 to 997.")

        if trend not in {"rising", "falling", "unchanged", "missing"}:
            raise ValueError("Invalid history category.")

        # Derive the bin from current delay rather than trusting an input bin.
        bucket = delay_bin(current)
        change = self.bins.get(bucket, self.global_change)
        change = self.cells.get((bucket, trend), change)

        return max(0, current + change)


def load_model(path=MODEL_PATH):
    artifact = json.loads(Path(path).read_text())
    return SavedModel(artifact)