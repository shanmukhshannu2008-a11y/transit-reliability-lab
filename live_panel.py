"""Manual-refresh live observations panel."""

from datetime import datetime, timezone
import time
from zoneinfo import ZoneInfo

import streamlit as st

from live_feed import SOURCE_URL, display_rows
from live_cache import fetch_shared_snapshot as fetch_snapshot


def render_live():
    st.divider()
    st.header("Current Paoli/Thorndale reports")
    st.write(
        "Request a snapshot from SEPTA TrainView. "
        "This section displays observations only—not model predictions."
    )
    st.caption(
        "No automatic polling. Requests are limited to one attempt per "
        "60 seconds in this browser session."
    )

    if st.button("Fetch current reports", key="fetch_live_reports"):
        now = time.monotonic()
        last_attempt = st.session_state.get("live_last_attempt")
        remaining = (
            60 - (now - last_attempt)
            if last_attempt is not None
            else 0
        )

        if remaining > 0:
            st.info(
                f"Please wait about {int(remaining) + 1} seconds "
                "before clicking again."
            )
        else:
            st.session_state["live_last_attempt"] = now

            try:
                with st.spinner("Requesting SEPTA reports…"):
                    snapshot = fetch_snapshot()
                    # Validate display conversion before replacing old data.
                    display_rows(snapshot)

                st.session_state["live_snapshot"] = snapshot
                st.session_state.pop("live_error", None)
            except (OSError, ValueError, TypeError) as error:
                st.session_state["live_error"] = (
                    f"{type(error).__name__}: {error}"
                )

    error = st.session_state.get("live_error")
    snapshot = st.session_state.get("live_snapshot")

    if error:
        st.warning(
            "The last request failed. Any reports below are from the "
            "previous successful request, not a new refresh."
        )
        with st.expander("Request error details"):
            st.code(error)

    if snapshot is None:
        st.info("No snapshot loaded. Click Fetch current reports to begin.")
        return

    collected = datetime.fromisoformat(snapshot["collected_at"])
    eastern = collected.astimezone(ZoneInfo("America/New_York"))
    age_seconds = max(
        0,
        (datetime.now(timezone.utc) - collected).total_seconds(),
    )

    st.write(
        f"**Collected:** {eastern.strftime('%Y-%m-%d %I:%M:%S %p %Z')}"
    )
    st.caption(
        f"Snapshot age when this page last rendered: "
        f"{age_seconds / 60:.1f} minutes. "
        "This is our collection time—not the timestamp of SEPTA's "
        "underlying observation. The display does not refresh itself."
    )

    rows = display_rows(snapshot)

    st.write(
        f"**{len(rows)} matching reports** out of "
        f"{len(snapshot['trains'])} total reports."
    )

    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info(
            "No matching reports were returned in this snapshot. "
            "This does not establish that no trains are operating."
        )

    st.caption(
        "Special and unknown values are not numeric delays. Empty quality "
        "notes do not guarantee accuracy or freshness. Snapshots in this "
        "panel are held in session memory, not saved to the collection archive."
    )
    st.caption(
        "Responses, including request failures, may be reused for 60 seconds "
        "across visitors to this running app. Clicking Fetch may return a "
        "cached snapshot; check its collection time."
    )
    st.markdown(f"[Source: SEPTA TrainView]({SOURCE_URL})")