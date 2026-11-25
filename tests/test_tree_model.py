import unittest

from tree_model import features, score


class TreeModelTests(unittest.TestCase):
    def row(self, previous=4, age=300):
        return {
            "initial": 6,
            "previous_delay": previous,
            "previous_age_seconds": age,
            "outcome": 9,
            "horizon": 600,
        }

    def test_valid_history_features(self):
        self.assertEqual(features(self.row()), [6, 2, 5, 0])

    def test_missing_history_is_explicit(self):
        for previous, age in [
            (None, 300),
            (999, 300),
            (998, 300),
            (-1, 300),
            (4, None),
            (4, 0),
            (4, 1801),
        ]:
            with self.subTest(previous=previous, age=age):
                self.assertEqual(
                    features(self.row(previous, age)),
                    [6, 0, 0, 1],
                )

    def test_future_values_do_not_change_features(self):
        row = self.row()
        before = features(row)

        row["outcome"] = 100
        row["horizon"] = 720

        self.assertEqual(features(row), before)

    def test_known_prediction_error(self):
        result = score([self.row()], [8.5])
        self.assertEqual(result["pairs"], 1)
        self.assertAlmostEqual(result["mae_minutes"], 0.5)

    def test_mismatched_prediction_count_rejected(self):
        with self.assertRaises(ValueError):
            score([self.row()], [])


if __name__ == "__main__":
    unittest.main()