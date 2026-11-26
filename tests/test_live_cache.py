import unittest
from unittest.mock import patch

from live_cache import cached_result, fetch_shared_snapshot


class LiveCacheTests(unittest.TestCase):
    def setUp(self):
        cached_result.clear()
        self.addCleanup(cached_result.clear)

    def test_reuses_success_without_changing_collection_time(self):
        snapshot = {
            "collected_at": "2026-11-26T00:00:00+00:00",
            "trains": [],
        }

        with patch(
            "live_cache.fetch_snapshot",
            return_value=snapshot,
        ) as fetch:
            first = fetch_shared_snapshot()
            second = fetch_shared_snapshot()

        self.assertEqual(first, second)
        self.assertEqual(second["collected_at"], snapshot["collected_at"])
        self.assertEqual(fetch.call_count, 1)

    def test_failure_is_cached(self):
        with patch(
            "live_cache.fetch_snapshot",
            side_effect=OSError("offline"),
        ) as fetch:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, "offline"):
                    fetch_shared_snapshot()

        self.assertEqual(fetch.call_count, 1)

    def test_callers_cannot_mutate_cached_snapshot(self):
        snapshot = {
            "collected_at": "2026-11-26T00:00:00+00:00",
            "trains": [],
        }

        with patch("live_cache.fetch_snapshot", return_value=snapshot):
            first = fetch_shared_snapshot()
            first["trains"].append({"trainno": "changed"})

            second = fetch_shared_snapshot()

        self.assertEqual(second["trains"], [])

    def test_new_fetch_can_recover_after_cache_is_cleared(self):
        snapshot = {
            "collected_at": "2026-11-26T00:01:00+00:00",
            "trains": [],
        }

        with patch(
            "live_cache.fetch_snapshot",
            side_effect=[OSError("offline"), snapshot],
        ) as fetch:
            with self.assertRaises(ValueError):
                fetch_shared_snapshot()

            cached_result.clear()
            recovered = fetch_shared_snapshot()

        self.assertEqual(recovered, snapshot)
        self.assertEqual(fetch.call_count, 2)


if __name__ == "__main__":
    unittest.main()