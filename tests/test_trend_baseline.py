import unittest

from trend_baseline import predict_trend


class TrendBaselineTests(unittest.TestCase):
    def row(self, current=6, previous=4, age=300):
        return {
            "initial": current,
            "previous_delay": previous,
            "previous_age_seconds": age,
        }

    def test_rising_delay(self):
        # Increase of 2 over 5 minutes: predict another 4 over 10.
        self.assertAlmostEqual(predict_trend(self.row()), 10)

    def test_falling_delay(self):
        self.assertAlmostEqual(
            predict_trend(self.row(current=6, previous=8)),
            2,
        )

    def test_prediction_cannot_be_negative(self):
        self.assertEqual(
            predict_trend(self.row(current=1, previous=5)),
            0,
        )

    def test_invalid_history_falls_back_to_current_delay(self):
        cases = [
            (None, 300),
            (998, 300),
            (999, 300),
            (-1, 300),
            (4, None),
            (4, 0),
            (4, -60),
            (4, 1801),
        ]

        for previous, age in cases:
            with self.subTest(previous=previous, age=age):
                self.assertEqual(
                    predict_trend(self.row(previous=previous, age=age)),
                    6,
                )

    def test_thirty_minute_boundary_is_accepted(self):
        self.assertAlmostEqual(
            predict_trend(self.row(age=1800)),
            6 + (2 / 30) * 10,
        )

    def test_future_outcome_and_horizon_are_not_used(self):
        row = self.row()
        row["outcome"] = 999
        row["horizon"] = 720

        self.assertAlmostEqual(predict_trend(row), 10)

        row["outcome"] = 0
        row["horizon"] = 480

        self.assertAlmostEqual(predict_trend(row), 10)


if __name__ == "__main__":
    unittest.main()