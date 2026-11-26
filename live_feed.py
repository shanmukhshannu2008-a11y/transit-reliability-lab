"""Read current TrainView reports without saving files or making predictions."""

import json
from datetime import datetime, timezone
from urllib.request import urlopen


SOURCE_URL = "https://www3.septa.org/api/TrainView/index.php"


def fetch_snapshot():
    with urlopen(SOURCE_URL, timeout=20) as response:
        trains = json.load(response)

    if not isinstance(trains, list):
        raise ValueError("Expected a list of train reports.")

    if not all(isinstance(train, dict) for train in trains):
        raise ValueError("The response contains a malformed train report.")

    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source_url": SOURCE_URL,
        "trains": trains,
    }


def display_rows(snapshot):
    rows = []

    for train in snapshot["trains"]:
        line = str(train.get("line") or "").lower()

        if "paoli" not in line and "thorndale" not in line:
            continue

        raw = train.get("late")
        flags = []

        if raw in (999, "999"):
            delay = None
            status = "Special status 999"
        elif raw in (998, "998"):
            delay = None
            status = "Unresolved status 998"
        elif type(raw) is int and 0 <= raw <= 997:
            delay = raw
            status = "Numeric report"
        else:
            delay = None
            status = "Unknown value"

        current = str(train.get("currentstop") or "").strip()

        if not current:
            flags.append("Missing current stop")

        rows.append({
            "Train": str(train.get("trainno") or ""),
            "Line": str(train.get("line") or ""),
            "Destination": str(train.get("dest") or ""),
            "Current stop": current,
            "Next stop": str(train.get("nextstop") or ""),
            "Reported delay (min)": delay,
            "Raw delay value": json.dumps(raw),
            "Status": status,
            "Quality notes": "; ".join(flags),
        })

    return rows