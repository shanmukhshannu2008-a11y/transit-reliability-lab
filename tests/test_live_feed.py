import io
import json
import unittest
from datetime import datetime
from unittest.mock import patch

from live_feed import fetch_snapshot, display_rows


class LiveFeedTests(unittest.TestCase):
    def test_fetch_valid_response(self):
        trains = [{"trainno": "123", "line": "Paoli/Thorndale", "late": 0}]
        response = io.BytesIO(json.dumps(trains).encode())

        with patch("live_feed.urlopen", return_value=response) as request:
            snapshot = fetch_snapshot()

        self.assertEqual(snapshot["trains"], trains)
        self.assertIsNotNone(
            datetime.fromisoformat(snapshot["collected_at"]).tzinfo
        )
        self.assertEqual(request.call_args.kwargs["timeout"], 20)

    def test_malformed_responses_rejected(self):
        for payload in ({"error": "unavailable"}, [None], ["bad record"]):
            with self.subTest(payload=payload):
                response = io.BytesIO(json.dumps(payload).encode())

                with patch("live_feed.urlopen", return_value=response):
                    with self.assertRaises(ValueError):
                        fetch_snapshot()

    def test_network_failure_propagates(self):
        with patch("live_feed.urlopen", side_effect=OSError("offline")):
            with self.assertRaises(OSError):
                fetch_snapshot()

    def test_special_and_unknown_values_are_not_numeric(self):
        for value in (999, "999", 998, "998", None, True, -1, "5"):
            with self.subTest(value=value):
                snapshot = {
                    "trains": [{
                        "line": "Paoli/Thorndale",
                        "late": value,
                    }]
                }
                row = display_rows(snapshot)[0]

                self.assertIsNone(row["Reported delay (min)"])
                self.assertNotEqual(row["Status"], "Numeric report")
                self.assertEqual(
                    row["Raw delay value"], json.dumps(value)
                )

    def test_line_filter_zero_and_missing_stop(self):
        snapshot = {
            "trains": [
                {
                    "trainno": "001",
                    "line": "Paoli/Thorndale",
                    "late": 0,
                    "currentstop": "",
                },
                {
                    "trainno": "002",
                    "line": "Another Line",
                    "late": 5,
                },
            ]
        }

        rows = display_rows(snapshot)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Train"], "001")
        self.assertEqual(rows[0]["Reported delay (min)"], 0)
        self.assertEqual(rows[0]["Quality notes"], "Missing current stop")


if __name__ == "__main__":
    unittest.main()