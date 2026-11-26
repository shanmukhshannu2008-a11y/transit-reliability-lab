"""Display saved evaluations of recorded live-feed snapshots."""

import json
import math
from pathlib import Path

import streamlit as st


PROJECT = Path(__file__).resolve().parent


def load_summary(path):
    report = json.loads(path.read_text())

    if report["schema_version"] != 1:
        raise ValueError("Unsupported live-evaluation format.")

    if report["collection_date"] != path.stem:
        raise ValueError("Report date does not match its filename.")

    overall = report["overall"]
    if type(overall["examples"]) is not int or overall["examples"] <= 0:
        raise ValueError("Expected a positive evaluated-example count.")

    for field in ("persistence_mae", "model_mae"):
        value = overall[field]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("Invalid error metric.")

    if sum(row["examples"] for row in report["by_train"].values()) != overall["examples"]:
        raise ValueError("Per-train counts do not match the overall count.")

    return report


def render_live_evaluation():
    st.divider()
    st.header("Does the historical model transfer to live reports?")
    st.write(
        "We tested the saved historical model on snapshots collected later "
        "from the live feed. This is a retrospective evaluation—not a "
        "continuously updating accuracy monitor."
    )

    folder = PROJECT / "docs/live_evaluations"
    paths = sorted(folder.glob("*.json"))

    if not paths:
        st.info("No recorded live-evaluation summaries are available yet.")
        return

    selected = st.selectbox(
        "Recorded collection date",
        options=[path.stem for path in paths],
        key="live_evaluation_date",
    )

    try:
        report = load_summary(folder / f"{selected}.json")
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error("The live-evaluation summary could not be loaded.")
        st.code(str(error))
        return

    overall = report["overall"]
    baseline = overall["persistence_mae"]
    model = overall["model_mae"]

    first, second, third = st.columns(3)
    first.metric("Evaluated live examples", overall["examples"])
    second.metric("Persistence MAE", f"{baseline:.3f} min")
    third.metric("Historical model MAE", f"{model:.3f} min")

    if model > baseline:
        st.warning(
            "The historical model performed worse than persistence "
            "on this collection date."
        )
    elif model < baseline:
        st.info(
            "The historical model performed better than persistence "
            "on this collection date. This alone does not establish "
            "reliable live performance."
        )
    else:
        st.info("The two methods had equal MAE on this collection date.")

    st.write(f"**Deployment decision:** {report['deployment_decision']}")

    st.subheader("Results by train number")
    st.dataframe(
        [
            {
                "Train": train,
                "Examples": scores["examples"],
                "Persistence MAE": round(scores["persistence_mae"], 3),
                "Model MAE": round(scores["model_mae"], 3),
            }
            for train, scores in sorted(report["by_train"].items())
        ],
        hide_index=True,
        width="stretch",
    )

    st.caption(
        f"{report['snapshot_count']} saved snapshots on this collection date. "
        "Examples overlap and are not independent journeys. "
        "Historical and live experiments use different sampling and targets; "
        "their error scores are not directly comparable."
    )

    with st.expander("Target definition, exclusions, and limitations"):
        st.write("**Target:**", report["target_rule"])
        st.write("**History:**", report["history_rule"])

        st.dataframe(
            [
                {"Exclusion reason": reason, "Anchors": count}
                for reason, count in sorted(report["exclusions"].items())
            ],
            hide_index=True,
            width="stretch",
        )

        for limitation in report["limitations"]:
            st.write(f"• {limitation}")