import unittest
try:
    import duckdb
except ImportError:
    duckdb=None


@unittest.skipIf(duckdb is None,'Requires optional analysis dependencies')
class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.c=duckdb.connect()
        self.addCleanup(self.c.close)
        self.c.execute('CREATE TABLE observations(service_date DATE,train_number VARCHAR,stamp TIMESTAMP,lateness INTEGER)')

    def add(self,time,value,day='2025-12-01',train='A'):
        self.c.execute('INSERT INTO observations VALUES (?,?,?,?)',[day,train,day+' '+time,value])

    def rows(self):
        from baseline_delay import build_pairs
        build_pairs(self.c)
        return self.c.execute('SELECT initial,outcome,eligibility FROM pairs ORDER BY anchor_time').fetchall()

    def test_known_metric_and_empty(self):
        from baseline_delay import metrics
        self.assertEqual(metrics([(4,7,600),(2,1,600)])['mae_minutes'],2)
        self.assertEqual(metrics([(4,7,600),(2,1,600)])['mean_error_minutes'],-1)
        self.assertIsNone(metrics([])['mae_minutes'])

    def test_status_between_endpoints_rejects_pair(self):
        self.add('10:00:00',4); self.add('10:05:00',999); self.add('10:10:00',5)
        self.assertEqual(self.rows()[0],(4,5,'intervening_status'))

    def test_first_outcome_not_skipped(self):
        self.add('10:00:00',4); self.add('10:08:00',998); self.add('10:10:00',5)
        self.assertEqual(self.rows()[0],(4,998,'non_numeric_outcome'))

    def test_twelve_minutes_inclusive(self):
        self.add('10:00:00',4); self.add('10:12:00',5)
        self.assertEqual(self.rows()[0],(4,5,'eligible'))

    def test_cross_date_or_train_not_paired(self):
        self.add('10:00:00',4);self.add('10:10:00',5,train='B')
        self.add('10:10:00',6,day='2025-12-02')
        self.assertTrue(all(r[2]=='no_nearby_update' for r in self.rows()))


if __name__=='__main__':
    unittest.main()
