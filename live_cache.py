"""Share a TrainView request result for 60 seconds."""

import streamlit as st

from live_feed import fetch_snapshot, display_rows


@st.cache_data(ttl=60, max_entries=1, show_spinner=False)
def cached_result():
    try:
        snapshot = fetch_snapshot()
        display_rows(snapshot)
        return {"snapshot": snapshot, "error": None}
    except (OSError, ValueError, TypeError) as error:
        # Return the failure so it is cached, rather than raising here.
        return {
            "snapshot": None,
            "error": f"{type(error).__name__}: {error}",
        }


def fetch_shared_snapshot():
    result = cached_result()

    if result["error"] is not None:
        raise ValueError(result["error"])

    return result["snapshot"]