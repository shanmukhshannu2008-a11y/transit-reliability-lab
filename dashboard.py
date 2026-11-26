"""Historical model results dashboard. No training or live requests."""

import json
import math
from datetime import date, timedelta
from pathlib import Path

import streamlit as st


PROJECT = Path(__file__).resolve().parent
REPORT_PATH = PROJECT / "docs/TREE_DEVELOPMENT_RESULTS.json"

METHODS = {
    "persistence": "Persistence",
    "recent_trend": "Recent trend",
    "learned_history": "Median-change model",
    "decision_tree": "Decision tree",
}


def load_report():
    report = json.loads(REPORT_PATH.read_text())
    folds = sorted(report["folds"], key=lambda fold: fold["date"])

    expected_dates = [
        str(date(2025, 11, 24) + timedelta(days=offset))
        for offset in range(12)
    ]

    if [fold["date"] for fold in folds] != expected_dates:
        raise ValueError("Expected 12 daily folds from Nov 24–Dec 5, 2025.")

    total = 0

    for fold in folds:
        count = fold["validation_pairs"]

        if type(count) is not int or count <= 0:
            raise ValueError("Each fold must have a positive example count.")

        total += count

        for method in METHODS:
            score = fold["metrics"][method]
            error = score["mae_minutes"]

            if (
                isinstance(error, bool)
                or not isinstance(error, (int, float))
                or not math.isfinite(error)
                or error < 0
            ):
                raise ValueError(f"Invalid error value for {method}.")

            if score["pairs"] != count:
                raise ValueError("Models must use identical example counts.")

    if total != 92474 or report["validation_pairs"] != total:
        raise ValueError("Example counts differ from the reviewed experiment.")

    # Check that the saved overall results agree with the daily results.
    for method in METHODS:
        calculated = pooled_mae(folds, method)
        saved = report["pooled_mae_minutes"][method]

        if not math.isclose(calculated, saved, rel_tol=1e-9):
            raise ValueError(f"Inconsistent overall score for {method}.")

    return folds


def pooled_mae(folds, method):
    count = sum(fold["validation_pairs"] for fold in folds)

    return sum(
        fold["metrics"][method]["mae_minutes"]
        * fold["validation_pairs"]
        for fold in folds
    ) / count


def main():
    st.set_page_config(
        page_title="Transit Reliability Lab",
        page_icon="🚆",
        layout="wide",
    )

    st.title("Transit Reliability Lab")
    st.write(
        "Can we predict whether a late train will fall further behind "
        "or recover some time?"
    )
    st.markdown(
        "I started this project because I ride SEPTA’s Paoli/Thorndale line. "
        "Using historical regional-rail reports, I compare simple prediction "
        "rules with machine-learning models to estimate how a train’s reported "
        "delay might change roughly ten minutes later.\n\n"
        "**Explore this dashboard** to compare model performance across days "
        "and inspect selected train histories. These are historical experiments, "
        "not live arrival forecasts."
    )
    st.info(
        "Historical development results • Regional rail • "
        "Not live tracking or verified station-arrival predictions"
    )

    try:
        folds = load_report()
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error("The reviewed results bundle is missing or invalid.")
        st.code(str(error))
        st.write(
            "Check docs/TREE_DEVELOPMENT_RESULTS.json before continuing."
        )
        st.stop()

    total = sum(fold["validation_pairs"] for fold in folds)
    best = min(METHODS, key=lambda method: pooled_mae(folds, method))

    first, second, third = st.columns(3)
    first.metric("Validation days", len(folds))
    second.metric("Eligible examples", f"{total:,}")
    third.metric("Lowest pooled error", f"{pooled_mae(folds, best):.3f} min")

    st.subheader("Overall model comparison")
    st.caption(
        "MAE is average absolute prediction error. Lower is better. "
        "Pooled scores weight days by their number of examples."
    )

    comparison = [
        {
            "Model": label,
            "MAE (minutes)": round(pooled_mae(folds, method), 4),
        }
        for method, label in METHODS.items()
    ]
    st.dataframe(
        sorted(comparison, key=lambda row: row["MAE (minutes)"]),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Daily performance")

    selected = st.multiselect(
        "Models to display",
        options=list(METHODS),
        default=list(METHODS),
        format_func=lambda method: METHODS[method],
    )

    if selected:
        chart = {
            "Date": [date.fromisoformat(fold["date"]) for fold in folds],
        }

        for method in selected:
            chart[METHODS[method]] = [
                fold["metrics"][method]["mae_minutes"]
                for fold in folds
            ]

        st.line_chart(
            chart,
            x="Date",
            y=[METHODS[method] for method in selected],
            y_label="MAE (minutes)",
        )
    else:
        st.write("Select at least one model to display.")

    chosen_date = st.selectbox(
        "Inspect a validation day",
        options=[fold["date"] for fold in folds],
    )
    chosen = next(fold for fold in folds if fold["date"] == chosen_date)

    st.caption(f"{chosen['validation_pairs']:,} eligible examples on this day")
    st.dataframe(
        [
            {
                "Model": label,
                "MAE (minutes)": round(
                    chosen["metrics"][method]["mae_minutes"], 4
                ),
            }
            for method, label in METHODS.items()
        ],
        hide_index=True,
        width="stretch",
    )

    st.subheader("How much does November 24 affect the result?")
    other_days = [
        fold for fold in folds if fold["date"] != "2025-11-24"
    ]

    for label, subset in [
        ("Official result: all 12 days", folds),
        ("Sensitivity check: other 11 days", other_days),
    ]:
        baseline = pooled_mae(subset, "persistence")
        learned = pooled_mae(subset, "learned_history")
        improvement = 100 * (baseline - learned) / baseline
        st.write(
            f"**{label}:** median-change model reduces MAE "
            f"by {improvement:.2f}% versus persistence."
        )

    st.caption(
        "November 24 remains in the official evaluation. Excluding it from "
        "scoring does not remove it from later folds' training history."
    )

    with st.expander("Evaluation method and limitations"):
        st.markdown(
            """
- Each model trains on earlier dates and is evaluated on a later day.
- Outcomes are stored reported-delay updates 8–12 minutes later.
- The archive omits unchanged reports, so eligible examples are selective.
- Examples overlap; they are not independent train journeys.
- Historical route mapping is unresolved: these are not Paoli-only results.
- December 6–7 remains reserved and unscored.
- These development results do not establish real-world arrival accuracy.
            """
        )

    st.caption(
        "Source: project analysis of the fulldecent/septa-regionalrail-otp "
        "historical archive. See docs/HISTORICAL_DATA_REVIEW.md for provenance."
    )


if __name__ == "__main__":
    from timeline_panel import render_timeline
    from prediction_panel import render_prediction

    main()
    render_timeline()
    render_prediction()