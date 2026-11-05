import csv
import json
import tempfile
import unittest
from pathlib import Path

from export_observations import export_observations


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "observations.csv"

    def save(self, name, trains, timestamp="2026-11-02T15:00:00+00:00"):
        (self.root / name).write_text(json.dumps({
            "collected_at": timestamp, "trains": trains,
        }), encoding="utf-8")

    def train(self, **changes):
        return {"line": "Paoli/Thorndale", "trainno": "0012",
                "currentstop": "Devon", "nextstop": "Strafford",
                "late": 2, **changes}

    def test_repeated_observations_preserved_other_lines_filtered(self):
        trains = [self.train(), self.train(line="Airport")]
        self.save("trainview_a.json", trains)
        self.save("trainview_b.json", trains)
        count, rows = export_observations(self.root, self.output)
        self.assertEqual((count, len(rows)), (2, 2))
        self.assertEqual(rows[0]["train_number"], "0012")
        self.assertNotEqual(rows[0]["source_file"], rows[1]["source_file"])

    def test_status_is_not_numeric_and_csv_keeps_raw_type(self):
        self.save("trainview_a.json", [self.train(late=999, currentstop=""),
                                      self.train(late="999")])
        export_observations(self.root, self.output)
        with self.output.open(newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(rows[0]["reported_delay"], "")
        self.assertEqual(rows[0]["status"], "cancelled_or_suspended")
        self.assertIn("missing_current_stop", rows[0]["quality_flags"])
        self.assertEqual(rows[0]["raw_late_json"], "999")
        self.assertEqual(rows[1]["raw_late_json"], '"999"')

    def test_unknown_does_not_become_zero(self):
        self.save("trainview_a.json", [self.train(late=None), self.train(late=0)])
        _, rows = export_observations(self.root, self.output)
        self.assertIsNone(rows[0]["reported_delay"])
        self.assertEqual(rows[1]["reported_delay"], 0)

    def test_malformed_record_preserves_previous_export(self):
        self.output.write_text("previous export", encoding="utf-8")
        self.save("trainview_a.json", [42])
        with self.assertRaisesRegex(ValueError, "not an object"):
            export_observations(self.root, self.output)
        self.assertEqual(self.output.read_text(), "previous export")

    def test_timestamp_without_timezone_rejected(self):
        self.save("trainview_a.json", [self.train()], "2026-11-02T15:00:00")
        with self.assertRaisesRegex(ValueError, "timezone"):
            export_observations(self.root, self.output)

    def test_missing_input_rejected(self):
        with self.assertRaisesRegex(ValueError, "No trainview"):
            export_observations(self.root, self.output)

    def test_order_uses_timestamp_not_filename(self):
        self.save("trainview_a.json", [self.train()], "2026-11-02T16:00:00+00:00")
        self.save("trainview_b.json", [self.train()], "2026-11-02T15:00:00+00:00")
        _, rows = export_observations(self.root, self.output)
        self.assertEqual(rows[0]["source_file"], "trainview_b.json")


if __name__ == "__main__":
    unittest.main()
