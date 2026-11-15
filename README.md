# Transit Reliability Lab

A project investigating transit data quality and arrival reliability,
starting with SEPTA's Paoli/Thorndale line, which I ride.

## Current functionality

- Fetch a snapshot from SEPTA's TrainView API.
- Save the response with a UTC collection timestamp.
- Display Paoli/Thorndale train records.
- Flag missing current stops and an unverified `late` value of 999.
- Run three basic assertions for the quality-check function.

## Run

Requires Python 3.10 or newer. Live collection uses the standard library; historical analysis requires the optional dependency below.

python3 collect_snapshot.py

Snapshots are saved in data/raw/, which is excluded from Git.

## Current limitations

- Collection sessions run locally and require the computer to remain awake.
- Collection time is not the train observation time.
- Historical SEPTA developer guidance identifies 999 as cancelled or suspended. The parser treats it as a status rather than a numeric delay; current operational meaning has not been independently confirmed.
- These records do not establish actual station arrival times.
- A small median-change regression model has been fitted; broader validation remains outstanding.

## Next steps

Verify feed semantics, compare saved observations, and establish
a defensible method for measuring arrival outcomes.

## Data source

SEPTA TrainView:
https://www3.septa.org/api/TrainView/index.php

This is an independent student project, not affiliated with SEPTA.

## Inspect saved snapshots

Pass a train number to examine its records across locally saved snapshots:

    python3 inspect_snapshots.py 9517
    python3 inspect_snapshots.py 5300

Show usage instructions:

    python3 inspect_snapshots.py --help

This reads saved files without contacting SEPTA. Records from different
dates are separate observations; a train number alone does not identify
one unique journey across dates.

## Collect a session

Collect three snapshots, waiting 60 seconds after each completed
attempt before starting the next:

    python3 collect_session.py --count 3 --interval 60

The count must be at least 1 and the interval at least 60 seconds.
Keep the computer awake and the terminal open during collection.
Press Control+C to stop early.

Failed or timed-out attempts are counted, and the session continues
to the next attempt. Each collector run has a 45-second timeout.
Raw snapshots remain excluded from Git.

## Historical observed-delay experiment

The historical pilot covers regional rail, not a verified Paoli/Thorndale subset.
It forecasts a later **reported delay**, not an actual station arrival.
The archive omits unchanged updates, so the evaluated sample is conditional on
having a stored update 8–12 minutes later. See docs/HISTORICAL_DATA_REVIEW.md
for attribution, download provenance, and source limitations.

Install optional analysis dependencies in a virtual environment:

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements-analysis.txt

With the reviewed 2025 archive at data/raw/historical-review/2025.parquet:

    .venv/bin/python audit_historical.py
    .venv/bin/python baseline_delay.py
    .venv/bin/python -m unittest discover -s tests -v

The persistence baseline predicts that reported delay stays unchanged.
Development results: December 1–4 MAE 2.658 minutes (34,254 pairs);
December 5 validation MAE 2.482 minutes (8,238 pairs).
These are conditional observed-update scores, not arrival accuracy.
December 6–7 has not been scored. A first median-change regression model is now available (see below).
Full rules and caveats: docs/EXPERIMENT_PLAN.md.
Generated reports and downloaded data stay excluded from Git.


## First learned model

    .venv/bin/python train_delay_model.py

Learns median future delay changes from December 1–4, grouped by current delay
and the direction of the previous valid report. Sparse groups fall back to
coarser training groups. December 5 validation uses the same 8,238 examples for
all methods: persistence MAE 2.4820, delay-only model 2.4416, history model 2.4408
minutes. The history model reduces error by about 1.7% versus persistence;
history itself adds almost no improvement over delay alone. This is exploratory
conditional reported-delay performance, not actual arrival accuracy.
December 6–7 remains unscored. No hyperparameter search was performed.
See docs/EXPERIMENT_PLAN.md for feature rules and limitations.


## Walk-forward development evaluation

    .venv/bin/python walk_forward.py

Train from November 17, 2025 through the day preceding each validation date,
November 24–December 5. Models are fitted afresh with fixed settings. Pooled
MAE: persistence 3.0084 minutes, delay-only 2.7987, delay-and-history 2.6952.
The history model wins on 8 of 12 days; improvement is uneven and much comes
from November 24. These are conditional reported-delay development results,
not independent final-test or arrival accuracy. December 6–7 remains unscored.
See docs/WALK_FORWARD_RESULTS.json for daily scores, coverage, and parameters.
