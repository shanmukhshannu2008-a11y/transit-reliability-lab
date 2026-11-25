"""Historical train-report timeline for the dashboard."""

import json
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import streamlit as st


PROJECT = Path(__file__).resolve().parent


def load_examples():
    path = PROJECT / "docs/TIMELINE_EXAMPLES.json"
    bundle = json.loads(path.read_text())

    if bundle["schema_version"] != 1:
        raise ValueError("Unsupported timeline data format.")

    examples = bundle["examples"]

    if not examples:
        raise ValueError("No timeline examples found.")

    for example in examples:
        reports = example["reports"]

        if not reports:
            raise ValueError("An example contains no reports.")

        timestamps = []

        for report in reports:
            timestamp = datetime.fromisoformat(report["timestamp"])
            timestamps.append(timestamp)

            if timestamp.date().isoformat() != example["date"]:
                raise ValueError("Report date does not match its example.")

            raw = report["raw_late"]
            delay = report["reported_delay"]
            status = report["status"]

            if status == "numeric":
                if (
                    type(delay) is not int
                    or not 0 <= delay <= 997
                    or type(raw) is not int
                    or raw != delay
                ):
                    raise ValueError("Invalid numeric delay.")
            elif delay is not None:
                raise ValueError("Special statuses must not have numeric delays.")

        if timestamps != sorted(timestamps):
            raise ValueError("Timeline reports are not chronological.")

    return examples


def render_timeline():
    st.divider()
    st.header("Explore a train’s reported delay")
    st.caption(
        "Three deliberately selected case studies—not a representative "
        "sample. These are historical reports, not live predictions."
    )

    try:
        examples = load_examples()
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error("Timeline examples could not be loaded.")
        st.code(str(error))
        return

    selected = st.selectbox(
        "Historical example",
        options=range(len(examples)),
        format_func=lambda index: (
            f"{examples[index]['date']} — "
            f"Train {examples[index]['train']}"
        ),
        key="timeline_example",
    )

    example = examples[selected]
    reports = example["reports"]
    numeric = [r for r in reports if r["status"] == "numeric"]
    special = [r for r in reports if r["status"] != "numeric"]

    st.write(example["reason"])

    left, right = st.columns(2)
    left.metric("Stored reports", len(reports))
    right.metric("Special or unknown reports", len(special))

    if numeric:
        times = [
            datetime.fromisoformat(r["timestamp"])
            for r in numeric
        ]
        delays = [r["reported_delay"] for r in numeric]

        fig, ax = plt.subplots(figsize=(11, 4))
        ax.scatter(times, delays, color="#0072B2", s=26)

        # Preserve the full report window, including special statuses.
        first = datetime.fromisoformat(reports[0]["timestamp"])
        last = datetime.fromisoformat(reports[-1]["timestamp"])

        if first < last:
            ax.set_xlim(first, last)

        ax.set_ylim(bottom=-2)
        ax.set_xlabel("Source-local time (America/New_York)")
        ax.set_ylabel("Reported delay (minutes)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.grid(alpha=0.2)
        fig.tight_layout()

        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("This example contains no numeric delay reports.")

    st.caption(
        "Each dot is one stored numeric report. Gaps do not establish "
        "unchanged delay. Special statuses are listed separately below."
    )

    if special:
        st.subheader("Special-status reports")
        st.dataframe(
            [
                {
                    "Local time": r["timestamp"].replace("T", " "),
                    "Raw value": str(r["raw_late"]),
                    "Status": r["status"],
                }
                for r in special
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "999 is treated as a special status—not 999 minutes late. "
            "Its operational interpretation remains provisional."
        )

    with st.expander("All stored reports for this example"):
        st.dataframe(
            [
                {
                    "Local time": r["timestamp"].replace("T", " "),
                    "Raw value": str(r["raw_late"]),
                    "Reported delay": r["reported_delay"],
                    "Status": r["status"],
                }
                for r in reports
            ],
            hide_index=True,
            width="stretch",
        )

    st.caption(
        "Source: fulldecent/septa-regionalrail-otp, CC-BY-4.0. "
        "Selected and transformed from the reviewed 2025 archive."
    )
    st.markdown(
        "[View source dataset]"
        "(https://huggingface.co/datasets/fulldecent/septa-regionalrail-otp)"
    )
    