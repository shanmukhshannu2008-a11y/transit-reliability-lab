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

Requires Python 3.10 or newer. No third-party packages are required.

python3 collect_snapshot.py

Snapshots are saved in data/raw/, which is excluded from Git.

## Current limitations

- Collection is manual: each run requests one snapshot.
- Collection time is not the train observation time.
- Historical SEPTA developer guidance identifies 999 as cancelled or suspended. The parser treats it as a status rather than a numeric delay; current operational meaning has not been independently confirmed.
- These records do not establish actual station arrival times.
- No machine-learning model has been trained yet.

## Next steps

Verify feed semantics, compare saved observations, and establish
a defensible method for measuring arrival outcomes.

## Data source

SEPTA TrainView:
https://www3.septa.org/api/TrainView/index.php

This is an independent student project, not affiliated with SEPTA.