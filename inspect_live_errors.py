"""Inspect saved live-session predictions without rerunning evaluation."""

import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
path = PROJECT / "data/processed/live_session_evaluation.json"
report = json.loads(path.read_text())

for row in report["examples"]:
    if row["train"] != "9550":
        continue

    baseline_error = abs(row["current_delay"] - row["outcome_delay"])
    model_error = abs(row["prediction"] - row["outcome_delay"])

    print(
        f"{row['anchor_utc']} | "
        f"current={row['current_delay']} | "
        f"history={row['history_category']} | "
        f"prediction={row['prediction']} | "
        f"later={row['outcome_delay']} | "
        f"extra error={model_error - baseline_error:+.1f}"
    )