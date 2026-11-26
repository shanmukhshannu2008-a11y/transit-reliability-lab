"""Manual prediction demo using the saved model."""

import streamlit as st

from predict_delay import prepare_features
from prediction_runtime import load_model


def render_prediction():
    st.divider()
    st.header("Try a reported-delay prediction")

    st.write(
        "Enter example reports to see what the saved model predicts. "
        "This demo does not fetch live train information."
    )
    st.caption(
        "Experimental estimate for an eligible stored update 8–12 minutes "
        "later—not a station-arrival forecast or a travel-planning tool."
    )

    try:
        model = load_model()
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error("The saved prediction model could not be loaded.")
        st.code(str(error))
        return

    st.caption(
        f"Training period: {model.training_start} through the day before "
        f"{model.training_end_exclusive}. "
        "The comparison charts above evaluate multiple separately trained models."
    )

    with st.form("manual_prediction"):
        current = st.number_input(
            "Current reported delay (minutes)",
            min_value=0,
            max_value=997,
            value=6,
            step=1,
        )

        use_history = st.checkbox(
            "Include a previous numeric report",
            value=True,
        )

        previous = st.number_input(
            "Previous reported delay (minutes)",
            min_value=0,
            max_value=997,
            value=4,
            step=1,
        )

        gap = st.number_input(
            "Minutes between the previous and current reports",
            min_value=0.01,
            value=5.0,
            step=1.0,
        )

        st.caption(
            "Use the immediately previous report from the same train and "
            "service date. Uncheck history if unavailable or special-status. "
            "History older than 30 minutes is treated as missing. "
            "Previous delay and gap are ignored when history is unchecked."
        )

        submitted = st.form_submit_button("Predict reported delay")

    if submitted:
        try:
            features = prepare_features(
                current=int(current),
                previous=int(previous) if use_history else None,
                gap_minutes=float(gap) if use_history else None,
            )
            prediction = model.predict(features)
        except (ValueError, KeyError, TypeError) as error:
            st.error(str(error))
            return

        st.metric(
            "Predicted later reported delay",
            f"{prediction:.1f} min",
        )
        st.write(
            f"Current reported delay: **{current} minutes** · "
            f"History category: **{features['trend']}**"
        )
        st.caption(
            "A single model estimate, not a confidence interval. "
            "No training or live API request was performed."
        )