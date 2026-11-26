import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from live_evaluation_panel import load_summary


PROJECT = Path(__file__).resolve().parents[1]


class LiveEvaluationPanelTests(unittest.TestCase):
    def test_reviewed_summary(self):
        report = load_summary(
            PROJECT / "docs/live_evaluations/2026-11-26.json"
        )

        self.assertEqual(report["overall"]["examples"], 58)
        self.assertAlmostEqual(
            report["overall"]["persistence_mae"],
            1.7586206896551724,
        )
        self.assertAlmostEqual(
            report["overall"]["model_mae"],
            1.9827586206896552,
        )

    def test_dashboard_displays_transfer_result(self):
        app = AppTest.from_file(
            str(PROJECT / "dashboard.py"),
            default_timeout=30,
        ).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)

        metrics = {item.label: item.value for item in app.metric}

        self.assertEqual(metrics["Evaluated live examples"], "58")
        self.assertEqual(metrics["Persistence MAE"], "1.759 min")
        self.assertEqual(metrics["Historical model MAE"], "1.983 min")

        warnings = [item.value for item in app.warning]
        self.assertTrue(
            any("performed worse than persistence" in text for text in warnings)
        )


if __name__ == "__main__":
    unittest.main()