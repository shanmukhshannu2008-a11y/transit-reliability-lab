import json
from pathlib import Path
import tempfile
import unittest
from audit_coverage import audit


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, name, stamp, trains=None):
        if trains is None:
            trains = [{"trainno": "001", "line": "Paoli/Thorndale", "late": 0,
                       "currentstop": "Devon"}]
        (self.root / f"trainview_{name}.json").write_text(json.dumps({
            "collected_at": stamp, "trains": trains,
        }))

    def test_local_dates_and_long_gap_not_continuous_coverage(self):
        self.save("a", "2026-10-15T01:00:00+00:00")
        self.save("b", "2026-11-02T15:00:00+00:00")
        result = audit(self.root)
        self.assertEqual([d["local_date"] for d in result["days"]], ["2026-10-14", "2026-11-02"])
        self.assertTrue(result["consecutive_snapshot_gaps"][0]["over_threshold"])
        self.assertTrue(all(d["elapsed_span_seconds"] == 0 for d in result["days"]))

    def test_empty_and_nonmatching_snapshots_still_count(self):
        self.save("a", "2026-11-02T15:00:00+00:00", [])
        self.save("b", "2026-11-02T15:01:00+00:00", [{"line": "Airport"}])
        day = audit(self.root)["days"][0]
        self.assertEqual((day["snapshots"], day["observations"]), (2, 0))
        self.assertEqual(day["snapshots_without_matching_trains"], 2)

    def test_repeated_train_not_counted_as_multiple_trains(self):
        self.save("a", "2026-11-02T15:00:00+00:00")
        self.save("b", "2026-11-02T15:01:00+00:00")
        day = audit(self.root)["days"][0]
        self.assertEqual((day["observations"], day["distinct_train_numbers"]), (2, 1))
        self.assertEqual(day["statuses"], {"numeric": 2})

    def test_threshold_boundary_and_duplicate_timestamps(self):
        self.save("a", "2026-11-02T15:00:00+00:00")
        self.save("b", "2026-11-02T15:03:00+00:00")
        self.save("c", "2026-11-02T15:03:00+00:00")
        result = audit(self.root)
        self.assertFalse(any(g["over_threshold"] for g in result["consecutive_snapshot_gaps"]))
        self.assertEqual(result["duplicate_collection_timestamps"], 1)

    def test_missing_input_and_invalid_threshold(self):
        with self.assertRaises(ValueError):
            audit(self.root)
        with self.assertRaises(ValueError):
            audit(self.root, 0)


if __name__ == "__main__":
    unittest.main()
