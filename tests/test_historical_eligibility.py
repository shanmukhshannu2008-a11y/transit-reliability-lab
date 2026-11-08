import unittest
try:
    import duckdb
except ImportError:
    duckdb = None


@unittest.skipIf(duckdb is None, 'Optional historical analysis requires requirements-analysis.txt')
class HistoricalTests(unittest.TestCase):
    def setUp(self):
        self.c = duckdb.connect()
        self.addCleanup(self.c.close)
        self.c.execute('CREATE TABLE observations(service_date DATE, train_number VARCHAR, stamp TIMESTAMP, lateness INTEGER)')

    def add(self, time, late, train='A', date='2025-12-01'):
        self.c.execute('INSERT INTO observations VALUES (?,?,?,?)',[date,train,date+' '+time,late])

    def result(self):
        from audit_historical import eligibility
        return eligibility(self.c)

    def test_boundary_and_no_future_fill(self):
        self.add('10:00:00',4)
        self.add('10:08:00',5)
        self.assertEqual(self.result(),(2,1,1,0))

    def test_gap_beyond_window_rejected(self):
        self.add('10:00:00',4)
        self.add('10:12:01',5)
        self.assertEqual(self.result(),(2,0,0,0))

    def test_special_event_is_not_skipped(self):
        self.add('10:00:00',4)
        self.add('10:09:00',999)
        self.add('10:10:00',5)
        self.assertEqual(self.result(),(2,1,0,1))

    def test_train_and_date_boundaries(self):
        self.add('10:00:00',4)
        self.add('10:10:00',5,train='B')
        self.add('10:10:00',5,date='2025-12-02')
        self.assertEqual(self.result(),(3,0,0,0))


if __name__ == '__main__':
    unittest.main()
