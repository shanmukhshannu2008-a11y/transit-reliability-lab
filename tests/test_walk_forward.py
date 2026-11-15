import unittest
from datetime import date
try:
    import duckdb
except ImportError:
    duckdb = None


@unittest.skipIf(duckdb is None, 'Requires optional analysis dependencies')
class WalkForwardTests(unittest.TestCase):
    def row(self, day, outcome):
        return dict(day=date.fromisoformat(day), initial=4, outcome=outcome,
                    horizon=600, delay_bin=2, trend='missing')

    def test_expanding_fit_uses_only_prior_days(self):
        from walk_forward import evaluate_folds
        rows = [self.row('2025-11-17',6), self.row('2025-11-24',100),
                self.row('2025-11-25',8), self.row('2025-12-06',999)]
        folds = evaluate_folds(rows, date(2025,11,24), date(2025,11,26))
        self.assertEqual([f['training_pairs'] for f in folds], [1,2])
        self.assertEqual(folds[0]['parameters']['delay_and_history']['global_change'],2)
        self.assertEqual(folds[1]['parameters']['delay_and_history']['global_change'],49)
        self.assertEqual(folds[0]['metrics']['delay_and_history']['mae_minutes'],94)
        self.assertIsNone(folds[0]['by_trend']['rising']['persistence']['mae_minutes'])

    def test_future_labels_do_not_change_earlier_fold(self):
        from walk_forward import evaluate_folds
        rows = [self.row('2025-11-17',6), self.row('2025-11-24',7), self.row('2025-11-25',8)]
        before = evaluate_folds(rows, date(2025,11,24), date(2025,11,26))[0]
        rows[-1]['outcome'] = 900
        after = evaluate_folds(rows, date(2025,11,24), date(2025,11,26))[0]
        self.assertEqual(before, after)

    def test_reserved_dates_and_empty_fold_rejected(self):
        from walk_forward import evaluate_folds
        with self.assertRaises(ValueError):
            evaluate_folds([], date(2025,12,5), date(2025,12,7))
        with self.assertRaises(ValueError):
            evaluate_folds([], date(2025,11,24), date(2025,11,25))
