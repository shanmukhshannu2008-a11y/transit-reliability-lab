import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT = Path(__file__).resolve().parents[1]


class PredictionPanelTests(unittest.TestCase):
    def start_app(self):
        app = AppTest.from_file(
            str(PROJECT / "dashboard.py"),
            default_timeout=30,
        ).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        return app

    def submit(self, app):
        button = next(
            button for button in app.button
            if button.label == "Predict reported delay"
        )
        button.click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)

        metrics = {
            metric.label: metric.value
            for metric in app.metric
        }
        self.assertEqual(
            metrics["Predicted later reported delay"],
            "6.0 min",
        )

    def test_prediction_with_history(self):
        app = self.start_app()
        self.submit(app)

        messages = [element.value for element in app.markdown]
        self.assertTrue(
            any("History category: **rising**" in text for text in messages)
        )

    def test_prediction_without_history(self):
        app = self.start_app()
        checkbox = next(
            checkbox for checkbox in app.checkbox
            if checkbox.label == "Include a previous numeric report"
        )
        checkbox.uncheck()
        self.submit(app)

        messages = [element.value for element in app.markdown]
        self.assertTrue(
            any("History category: **missing**" in text for text in messages)
        )


if __name__ == "__main__":
    unittest.main()