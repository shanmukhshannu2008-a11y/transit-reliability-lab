import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from live_snapshot_data import load_snapshots_for_date


class LiveSnapshotDataTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name)
        self.raw = self.project / "data/raw"
        self.raw.mkdir(parents=True)

        patcher = patch("live_snapshot_data.PROJECT", self.project)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_snapshot(self, name, timestamp, trains):
        path = self.raw / f"trainview_{name}.json"
        path.write_text(json.dumps({
            "collected_at": timestamp,
            "trains": trains,
        }))

    def test_selects_eastern_date_not_utc_date(self):
        self.write_snapshot(
            "evening",
            "2026-11-26T00:20:00+00:00",
            [],
        )

        rows = load_snapshots_for_date(date(2026, 11, 25))
        self.assertEqual(len(rows), 1)

        with self.assertRaises(ValueError):
            load_snapshots_for_date(date(2026, 11, 26))

    def test_preserves_empty_snapshots_and_sorts_by_time(self):
        self.write_snapshot(
            "a",
            "2026-11-26T20:01:00+00:00",
            [{"trainno": "001", "line": "Paoli/Thorndale", "late": 0}],
        )
        self.write_snapshot(
            "z",
            "2026-11-26T20:00:00+00:00",
            [],
        )

        rows = load_snapshots_for_date(date(2026, 11, 26))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][1], {})
        self.assertEqual(rows[1][1], {"001": 0})

    def test_duplicate_train_number_rejected(self):
        train = {
            "trainno": "001",
            "line": "Paoli/Thorndale",
            "late": 0,
        }
        self.write_snapshot(
            "duplicate_train",
            "2026-11-26T20:00:00+00:00",
            [train, train],
        )

        with self.assertRaises(ValueError):
            load_snapshots_for_date(date(2026, 11, 26))

    def test_duplicate_collection_time_rejected(self):
        for name in ("a", "b"):
            self.write_snapshot(
                name,
                "2026-11-26T20:00:00+00:00",
                [],
            )

        with self.assertRaises(ValueError):
            load_snapshots_for_date(date(2026, 11, 26))

    def test_timestamp_requires_timezone(self):
        self.write_snapshot("no_timezone", "2026-11-26T20:00:00", [])

        with self.assertRaises(ValueError):
            load_snapshots_for_date(date(2026, 11, 26))


if __name__ == "__main__":
    unittest.main()