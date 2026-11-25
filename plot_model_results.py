"""Plot saved development results without retraining models."""

import json
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Save images without opening a separate window.
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


PROJECT = Path(__file__).resolve().parent

METHODS = {
    "persistence": ("Persistence", "#555555", "--"),
    "recent_trend": ("Recent trend", "#D55E00", ":"),
    "learned_history": ("Median-change model", "#0072B2", "-"),
    "decision_tree": ("Decision tree", "#009E73", "-."),
}


def main():
    source = PROJECT / "data/processed/tree_development.json"
    report = json.loads(source.read_text())

    folds = sorted(report["folds"], key=lambda fold: fold["date"])
    dates = [date.fromisoformat(fold["date"]) for fold in folds]

    fig, ax = plt.subplots(figsize=(12, 6.5))

    for method, (label, color, style) in METHODS.items():
        daily_errors = [
            fold["metrics"][method]["mae_minutes"]
            for fold in folds
        ]
        pooled_error = report["pooled_mae_minutes"][method]

        ax.plot(
            dates,
            daily_errors,
            label=f"{label} — pooled MAE {pooled_error:.3f}",
            color=color,
            linestyle=style,
            marker="o",
            markersize=4,
            linewidth=2,
        )

    ax.set_title(
        "Predicting reported train delay: daily development results",
        fontsize=15,
        pad=16,
    )
    ax.set_xlabel("Validation date (2025)")
    ax.set_ylabel("Mean absolute error (minutes) — lower is better")
    ax.set_ylim(bottom=0)
    ax.set_xticks(dates)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=9, loc="upper right")
    ax.set_ylim(0, 8)

    fig.text(
        0.5,
        0.025,
        "12 walk-forward folds • 92,474 eligible examples • "
        "Pooled MAE weights days by example count\n"
        "Conditional reported-delay outcomes 8–12 minutes later; "
        "not verified arrivals. Reserved test dates unscored.",
        ha="center",
        fontsize=9,
        color="#444444",
    )

    fig.tight_layout(rect=(0, 0.10, 1, 1))

    output = PROJECT / "docs/figures/model_comparison.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved chart: {output}")


if __name__ == "__main__":
    main()

