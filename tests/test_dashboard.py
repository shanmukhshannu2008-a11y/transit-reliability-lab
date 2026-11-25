import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def start_app(self):
        app = AppTest.from_file(
            str(PROJECT / "dashboard.py"),
            default_timeout=30,
        ).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        return app

    def test_reviewed_report_loads(self):
        app = self.start_app()

        self.assertEqual(app.title[0].value, "Transit Reliability Lab")
        self.assertEqual(
            [metric.value for metric in app.metric],
            ["12", "92,474", "2.695 min"],
        )
        self.assertEqual(len(app.dataframe[0].value), 4)

    def test_date_selection_updates_table(self):
        app = self.start_app()
        app.selectbox[0].select("2025-12-05").run()

        self.assertEqual(len(app.exception), 0)

        table = app.dataframe[1].value
        scores = dict(zip(table["Model"], table["MAE (minutes)"]))

        self.assertAlmostEqual(scores["Persistence"], 2.482, places=3)
        self.assertAlmostEqual(scores["Decision tree"], 2.495, places=3)

    def test_empty_model_selection_is_handled(self):
        app = self.start_app()
        app.multiselect[0].set_value([]).run()

        self.assertEqual(len(app.exception), 0)
        messages = [element.value for element in app.markdown]
        self.assertIn("Select at least one model to display.", messages)


if __name__ == "__main__":
    unittest.main()