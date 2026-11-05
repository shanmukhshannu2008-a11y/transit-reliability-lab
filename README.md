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

- Collection sessions must be started manually and run only while the computer is awake.
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

## Collect and inspect

```bash
python3 collect_session.py --count 3 --interval 60
python3 inspect_snapshots.py 9517
```

The session waits at least 60 seconds after each attempt. Use Control+C to stop.
Inspection reads saved snapshots; a train number can recur on different dates.

## Export observations

```bash
python3 export_observations.py
python3 -m unittest discover -s tests -v
```

The exporter reads local snapshots only and writes
`data/processed/observations.csv`. Each row is one matching train record in
one snapshot. It retains repeated observations and source filenames plus
zero-based record indices. Collection timestamps are not arrival times.
`raw_late_json` retains the original value and its JSON type. Blank parsed
delay means no numeric value, not zero. Status interpretation inherits the
current parser; it is not a complete verified code specification.

Malformed snapshots stop the export without replacing a previous output.
Raw and processed datasets are excluded from Git. Tests use temporary synthetic
fixtures and make no network calls.

## Project notes

- [Progress journal](docs/PROJECT_JOURNAL.md)
- [Verified progress brief](docs/VERIFIED_PROGRESS_BRIEF.md)


## Audit collection coverage

```bash
python3 audit_coverage.py
python3 audit_coverage.py --gap-seconds 180
```

Reads original snapshots so files with no matching trains still count. Saves
`data/processed/coverage.json` and prints daily counts, statuses, first/last
collection times and gaps. Dates use America/New_York collection dates, not
verified transit service dates. Distinct train numbers are not journey counts.
The configurable gap threshold is a diagnostic choice, not an API guarantee.
An elapsed first-to-last span includes gaps and is not continuous coverage.
