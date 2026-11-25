import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from timeline_panel import load_examples


PROJECT = Path(__file__).resolve().parents[1]


class TimelineTests(unittest.TestCase):
    def test_reviewed_example_counts(self):
        examples = load_examples()

        counts = {
            (example["date"], example["train"]): len(example["reports"])
            for example in examples
        }

        self.assertEqual(counts, {
            ("2025-11-24", "5318"): 109,
            ("2025-12-05", "5229"): 27,
            ("2025-12-05", "5322"): 30,
        })

    def test_special_status_is_not_numeric_delay(self):
        examples = load_examples()
        example = next(e for e in examples if e["train"] == "5229")

        special = [
            report
            for report in example["reports"]
            if report["status"] != "numeric"
        ]

        self.assertEqual(len(special), 8)

        for report in special:
            self.assertEqual(report["raw_late"], 999)
            self.assertEqual(report["status"], "special_999")
            self.assertIsNone(report["reported_delay"])

    def test_selecting_train_updates_display(self):
        app = AppTest.from_file(
            str(PROJECT / "dashboard.py"),
            default_timeout=30,
        ).run()

        self.assertEqual(len(app.exception), 0)

        # Select the second case study: December 5, train 5229.
        app.selectbox(key="timeline_example").select(1).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)

        metrics = {
            metric.label: metric.value
            for metric in app.metric
        }

        self.assertEqual(metrics["Stored reports"], "27")
        self.assertEqual(metrics["Special or unknown reports"], "8")

        special_tables = [
            element.value
            for element in app.dataframe
            if list(element.value.columns)
            == ["Local time", "Raw value", "Status"]
        ]

        self.assertEqual(len(special_tables), 1)
        self.assertEqual(len(special_tables[0]), 8)
        self.assertTrue(
            (special_tables[0]["Raw value"] == "999").all()
        )


if __name__ == "__main__":
    unittest.main()