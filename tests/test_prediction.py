import tempfile
import unittest
from pathlib import Path

from predict_delay import prepare_features
from save_model import save_model, load_model
from train_delay_model import MedianChangeModel


class PredictionTests(unittest.TestCase):
    def test_history_categories(self):
        cases = [
            (4, "rising"),
            (8, "falling"),
            (6, "unchanged"),
        ]

        for previous, expected in cases:
            with self.subTest(previous=previous):
                features = prepare_features(6, previous, 5)
                self.assertEqual(features["trend"], expected)
                self.assertEqual(features["delay_bin"], 2)

    def test_missing_stale_and_special_history(self):
        self.assertEqual(
            prepare_features(6)["trend"], "missing"
        )
        self.assertEqual(
            prepare_features(6, 4, 31)["trend"], "missing"
        )
        self.assertEqual(
            prepare_features(6, 999, 5)["trend"], "missing"
        )
        self.assertEqual(
            prepare_features(6, 4, 30)["trend"], "rising"
        )

    def test_invalid_current_delay_rejected(self):
        for current in (-1, 998, 999, True, 6.5):
            with self.subTest(current=current):
                with self.assertRaises(ValueError):
                    prepare_features(current)

    def test_incomplete_or_invalid_history_gap_rejected(self):
        cases = [
            (4, None),
            (None, 5),
            (4, 0),
            (4, -1),
            (4, float("nan")),
            (4, float("inf")),
        ]

        for previous, gap in cases:
            with self.subTest(previous=previous, gap=gap):
                with self.assertRaises(ValueError):
                    prepare_features(6, previous, gap)

    def test_save_load_preserves_known_prediction_and_fallback(self):
        # Synthetic training data; no historical archive needed.
        training = [
            {
                "initial": 6,
                "outcome": outcome,
                "delay_bin": 2,
                "trend": "rising",
            }
            for outcome in (7, 8, 9)
        ]

        original = MedianChangeModel(
            use_history=True,
            min_count=3,
        ).fit(training)

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.json"
            save_model(original, path)
            restored = load_model(path)

        self.assertEqual(restored.parameters(), original.parameters())

        # Learned median change is +2.
        self.assertEqual(
            restored.predict(prepare_features(6, 4, 5)), 8
        )

        # No matching delay bin: use the global learned change.
        self.assertEqual(
            restored.predict(prepare_features(0)), 2
        )


if __name__ == "__main__":
    unittest.main()