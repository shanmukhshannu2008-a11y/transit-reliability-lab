from collections import defaultdict
from datetime import date

import duckdb

from baseline_delay import PROJECT, build_pairs
from train_delay_model import (
    load_development,
    feature_rows,
    MedianChangeModel,
)

target_day = date(2025, 11, 24)

with duckdb.connect() as connection:
    load_development(
        connection,
        PROJECT / "data/raw/historical-review/2025.parquet",
        start=date(2025, 11, 17),
    )
    build_pairs(connection)
    rows = feature_rows(connection)

training = [row for row in rows if row["day"] < target_day]
model = MedianChangeModel(True).fit(training)

gains = defaultdict(lambda: {"count": 0, "reduction": 0})

for row in rows:
    if row["day"] != target_day or row["trend"] != "rising":
        continue

    baseline_error = abs(row["initial"] - row["outcome"])
    model_error = abs(model.predict(row) - row["outcome"])

    group = gains[row["train"]]
    group["count"] += 1
    group["reduction"] += baseline_error - model_error

ranked = sorted(
    gains.items(),
    key=lambda item: item[1]["reduction"],
    reverse=True,
)

print(f"Train numbers with rising-delay examples: {len(ranked)}")
print(f"Net error reduction: {sum(g['reduction'] for g in gains.values()):.1f}")

print("\n10 largest contributions:")
for train, group in ranked[:10]:
    print(
        f"Train {train} | examples={group['count']} | "
        f"error reduction={group['reduction']:+.1f}"
    )