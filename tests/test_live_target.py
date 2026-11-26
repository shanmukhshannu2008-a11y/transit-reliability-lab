import unittest
from datetime import datetime, timedelta, timezone

from audit_live_target import match_live_target


class LiveTargetTests(unittest.TestCase):
    def snapshots(self, values):
        start = datetime(2026, 11, 26, 15, tzinfo=timezone.utc)
        return [
            (
                start + timedelta(minutes=minute),
                {} if value is None else {"A": value},
            )
            for minute, value in enumerate(values)
        ]

    def test_selects_ten_minutes_not_eight(self):
        values = [0] * 13
        values[8] = 8
        values[10] = 10
        snapshots = self.snapshots(values)

        result = match_live_target(snapshots, 0, "A")

        self.assertEqual(result["status"], "eligible")
        self.assertEqual(result["outcome_delay"], 10)
        self.assertEqual(result["horizon_minutes"], 10)

    def test_twelve_minute_boundary_is_accepted(self):
        snapshots = self.snapshots([0] * 13)
        snapshots = [
            entry for index, entry in enumerate(snapshots)
            if index not in (10, 11)
        ]

        result = match_live_target(snapshots, 0, "A")

        self.assertEqual(result["status"], "eligible")
        self.assertEqual(result["horizon_minutes"], 12)

    def test_report_after_twelve_minutes_is_not_used(self):
        snapshots = self.snapshots([0] * 14)
        start = snapshots[0][0]

        snapshots = snapshots[:10] + [
            (start + timedelta(minutes=9, seconds=30), {"A": 0}),
            (start + timedelta(minutes=12, seconds=1), {"A": 0}),
        ]

        result = match_live_target(snapshots, 0, "A")

        self.assertEqual(
            result["status"],
            "no_report_in_10_to_12_minute_window",
        )

    def test_special_outcome_is_not_skipped(self):
        values = [0] * 13
        values[10] = 999

        result = match_live_target(self.snapshots(values), 0, "A")

        self.assertEqual(result["status"], "nonnumeric_outcome")

    def test_incomplete_followup_is_not_scored(self):
        result = match_live_target(self.snapshots([0] * 12), 0, "A")

        self.assertEqual(
            result["status"],
            "collection_ended_before_12_minutes",
        )

    def test_disappearance_after_outcome_still_rejects_window(self):
        values = [0] * 13
        values[11] = None

        result = match_live_target(self.snapshots(values), 0, "A")

        self.assertEqual(result["status"], "interrupted_followup")


if __name__ == "__main__":
    unittest.main()