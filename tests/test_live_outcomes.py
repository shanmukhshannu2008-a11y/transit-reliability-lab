import unittest
from datetime import datetime, timedelta, timezone

from audit_live_outcomes import classify, retained_keys
from compare_live_outcomes import first_outcome


class LiveOutcomeTests(unittest.TestCase):
    def snapshots(self, values):
        start = datetime(2026, 11, 26, 15, tzinfo=timezone.utc)
        return [
            (
                start + timedelta(minutes=minute),
                {} if value is None else {"A": value},
            )
            for minute, value in enumerate(values)
        ]

    def test_sampling_changes_outcome_on_same_anchor(self):
        snapshots = self.snapshots([5] * 9 + [6] * 4)
        retained = retained_keys(snapshots)

        full = first_outcome(snapshots, 0, "A", retained, False)
        changed = first_outcome(snapshots, 0, "A", retained, True)

        self.assertEqual(full, (snapshots[8][0], 5))
        self.assertEqual(changed, (snapshots[9][0], 6))

        for mode in (False, True):
            self.assertEqual(
                classify(snapshots, 0, "A", retained, mode),
                "numeric_outcome_available",
            )

    def test_unchanged_reports_are_not_missing_full_feed_outcomes(self):
        snapshots = self.snapshots([0] * 13)
        retained = retained_keys(snapshots)

        self.assertEqual(
            classify(snapshots, 0, "A", retained, False),
            "numeric_outcome_available",
        )
        self.assertEqual(
            classify(snapshots, 0, "A", retained, True),
            "no_update_in_8_to_12_minute_window",
        )

    def test_collection_end_is_not_an_outcome_failure(self):
        snapshots = self.snapshots([0] * 12)
        retained = retained_keys(snapshots)

        self.assertEqual(
            classify(snapshots, 0, "A", retained, False),
            "collection_ended_before_12_minutes",
        )

    def test_disappearance_interrupts_followup(self):
        values = [0] * 13
        values[5] = None
        snapshots = self.snapshots(values)
        retained = retained_keys(snapshots)

        self.assertEqual(
            classify(snapshots, 0, "A", retained, False),
            "interrupted_followup",
        )

    def test_first_special_outcome_is_not_skipped(self):
        snapshots = self.snapshots([0] * 8 + [999] + [1] * 4)
        retained = retained_keys(snapshots)

        self.assertEqual(
            classify(snapshots, 0, "A", retained, True),
            "nonnumeric_outcome",
        )

    def test_intervening_special_status_rejects_numeric_pair(self):
        values = [0] * 13
        values[4] = 999
        snapshots = self.snapshots(values)
        retained = retained_keys(snapshots)

        self.assertEqual(
            classify(snapshots, 0, "A", retained, False),
            "intervening_special_or_unknown",
        )

    def test_twelve_minute_boundary_is_inclusive(self):
        snapshots = self.snapshots([0] * 12 + [1])
        retained = retained_keys(snapshots)

        self.assertEqual(
            classify(snapshots, 0, "A", retained, True),
            "numeric_outcome_available",
        )


if __name__ == "__main__":
    unittest.main()