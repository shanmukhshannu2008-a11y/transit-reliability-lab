import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
try:
    import duckdb
except ImportError:
    duckdb = None


@unittest.skipIf(duckdb is None, 'Requires optional analysis dependencies')
class ModelTests(unittest.TestCase):
    def setUp(self):
        self.c = duckdb.connect()
        self.addCleanup(self.c.close)
        self.c.execute('CREATE TABLE observations(service_date DATE,train_number VARCHAR,stamp TIMESTAMP,lateness INTEGER)')

    def add(self, time, value, train='A', day='2025-12-01'):
        self.c.execute('INSERT INTO observations VALUES (?,?,?,?)', [day,train,day+' '+time,value])

    def features(self):
        from baseline_delay import build_pairs
        from train_delay_model import feature_rows
        build_pairs(self.c)
        return feature_rows(self.c)

    def test_features_do_not_change_with_future_label(self):
        self.add('09:55:00',2); self.add('10:00:00',4); self.add('10:10:00',7)
        before = self.features()[0]
        self.c.execute("UPDATE observations SET lateness=80 WHERE stamp=TIMESTAMP '2025-12-01 10:10:00'")
        after = self.features()[0]
        self.assertEqual(before['trend'], 'rising')
        self.assertEqual(before['delay_bin'], after['delay_bin'])
        self.assertEqual(before['trend'], after['trend'])
        self.assertNotEqual(before['outcome'], after['outcome'])

    def test_previous_special_or_old_report_is_missing(self):
        self.add('09:55:00',999); self.add('10:00:00',4); self.add('10:10:00',5)
        self.add('09:00:00',2,train='B'); self.add('10:00:00',4,train='B'); self.add('10:10:00',5,train='B')
        self.assertTrue(all(r['trend']=='missing' for r in self.features()))

    def test_history_does_not_cross_day_or_train(self):
        self.add('09:55:00',2,train='B'); self.add('09:55:00',2,day='2025-11-30')
        self.add('10:00:00',4); self.add('10:10:00',5)
        self.assertEqual(self.features()[0]['trend'], 'missing')

    def test_learned_median_and_fallback_ignore_prediction_label(self):
        from train_delay_model import MedianChangeModel
        rows = [dict(initial=4,outcome=y,delay_bin=2,trend='rising') for y in (5,6,100)]
        model = MedianChangeModel(min_count=3).fit(rows)
        row = dict(initial=4,delay_bin=2,trend='rising',outcome=-999)
        self.assertEqual(model.predict(row),6)
        row['trend']='missing'
        self.assertEqual(model.predict(row),6)
        row['delay_bin']=0
        self.assertEqual(model.predict(row),6)

    def test_full_run_excludes_test_and_does_not_fit_validation(self):
        from train_delay_model import run
        for day,value in [('2025-12-01',6),('2025-12-05',99),('2025-12-06',200)]:
            self.add('10:00:00',4,day=day);self.add('10:10:00',value,day=day)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'fixture.parquet'
            self.c.execute('COPY (SELECT service_date,train_number,CAST(stamp AS TIME) AS time,lateness FROM observations) TO ? (FORMAT PARQUET)',[str(path)])
            with patch('train_delay_model.EXPECTED_SHA',hashlib.sha256(path.read_bytes()).hexdigest()):
                report = run(path)
        self.assertEqual(report['parameters']['delay_and_history']['global_change'],2)
        self.assertEqual(report['splits']['train']['pairs'],1)
        self.assertEqual(report['splits']['validation']['pairs'],1)
        self.assertEqual(report['splits']['validation']['metrics']['delay_and_history']['mae_minutes'],93)


if __name__ == '__main__':
    unittest.main()
