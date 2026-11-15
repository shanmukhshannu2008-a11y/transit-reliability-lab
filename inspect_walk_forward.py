import json
from pathlib import Path

project = Path(__file__).resolve().parent
report_path = project / "data/processed/walk_forward.json"
report = json.loads(report_path.read_text())


def summarize(label, folds):
    total_examples = sum(fold["validation_pairs"] for fold in folds)

    print(f"\n{label}")
    print(f"Days: {len(folds)} | Examples: {total_examples}")

    scores = {}

    for method in ("persistence", "delay_only", "delay_and_history"):
        total_error = sum(
            fold["metrics"][method]["mae_minutes"]
            * fold["validation_pairs"]
            for fold in folds
        )
        scores[method] = total_error / total_examples
        print(f"{method}: MAE {scores[method]:.4f} minutes")

    improvement = (
        (scores["persistence"] - scores["delay_and_history"])
        / scores["persistence"]
        * 100
    )
    print(f"History model improvement: {improvement:.2f}%")


summarize("Official result — all validation days", report["folds"])

other_days = [
    fold
    for fold in report["folds"]
    if fold["validation_date"] != "2025-11-24"
]

summarize(
    "Sensitivity check — excluding November 24",
    other_days,
)

print("\nNovember 24 remains included in the official evaluation.")