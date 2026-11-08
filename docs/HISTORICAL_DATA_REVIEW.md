# Historical data feasibility review

Reviewed November 5, 2026. Decision: exploratory use only; not yet approved
for a general ten-minute forecast evaluation.

## Sources and evidence

Dataset and attribution: William Entriken, SEPTA Regional Rail On-Time
Performance Report; dataset metadata lists CC BY 4.0.
https://huggingface.co/datasets/fulldecent/septa-regionalrail-otp

Downloaded the first 100 viewer rows and inspected upstream source code.
These are a convenience sample, not representative of the archive. Local
copies and SHA-256 checksums are in ignored data/raw/historical-review/.
No downloaded code was executed. No full archive was downloaded.

- The scraper directly casts the feed's late field to an integer.
  https://github.com/fulldecent/septa-regionalrail-otp/blob/main/website/scrape-trainview.php
- The report labels those values as minutes.
  https://github.com/fulldecent/septa-regionalrail-otp/blob/main/website/schedule-detail.php
- The Hugging Face export casts lateness to INT32 without unit scaling.
  https://huggingface.co/datasets/fulldecent/septa-regionalrail-otp/blob/main/export-from-scraper.py

Working interpretation: minutes. This is code-based evidence, not maintainer
confirmation of every historical batch. The dataset card's seconds description
conflicts with the other evidence; do not multiply or divide values blindly.

## Critical sampling limitation

The upstream insertLateness method skips a new record when the last stored
value for that train/service day is unchanged. Therefore absent rows are not
proof of missing polls, or proof of unchanged delay. The public fields do not
provide a per-poll heartbeat to distinguish the two.
https://github.com/fulldecent/septa-regionalrail-otp/blob/main/website/common.php

Forward-filling without limits could manufacture target labels. Evaluating only
anchors with an observed change near ten minutes instead selects a biased
subset of trips whose delays change. Any such pilot must be labeled as
conditional on observed updates and report label eligibility, not presented as
accuracy across all trains and times.

## Time and route handling

The archive uses service dates with a nominal 03:00 boundary. Its scraper
computes the service date using Los Angeles local date and observation time
using New York time. Do not assume a calendar-date join; investigate daylight
saving transition behavior and ambiguous local times before conversion.
The sample has no station, line, coordinates, or actual arrival fields. Historical
route assignment requires matching schedules for the relevant dates, not a
modern train-number guess. Train numbers in the scraper are cast to integers,
so leading zeros may already be lost upstream.

## Next bounded experiment

1. Inspect a recent, contiguous archive subset and establish its coverage.
2. Resolve date-compatible Paoli/Thorndale route mapping; if unavailable,
   explicitly scope any archive pilot to regional rail rather than mislabel it.
3. Measure eligible observed future updates at 10 minutes +/- 2 minutes,
   retaining the actual horizon. Reject cross-day and special-status pairs.
4. Report selection bias and eligibility rates. Never infer that no row means
   an on-time train or a confirmed unchanged label.
5. Use regularly collected, sufficiently dense snapshots for a prospective
   fixed-horizon test. These measure reported delay, not verified arrival time.
6. Chronological training/validation/test partitions; no overlapping journeys
   across splits, no future values as input, and an unchanged-delay baseline.

No model trained, performance reported, or source issue posted in this review.


## November 8 pilot evidence

Downloaded only the 2025 partition (8,253,297 bytes); verified its SHA-256 against
Hugging Face metadata. Read with DuckDB 1.4.3 in an isolated local .venv.
The year contains 3,505,561 rows across 365 service dates and 20,909 status-999
rows. This does not demonstrate uninterrupted coverage on those dates.

Pilot: December 1–7, 06:00–before 22:00 local time. 69,906 rows; 570 distinct
train numbers. Of 69,611 candidate numeric anchors, 51,887 (74.54%) had a numeric
stored update under the documented 8–12 minute rule; 20 had a matched 999 status.
The remaining anchors lacked an eligible numeric pair. The daytime restriction
avoids overnight conversion in this pilot, not in the general archive.

No forward filling, trained model, or accuracy score. No route-based filtering:
we checked current SEPTA GTFS release metadata, which is insufficient for 2025
trip mapping. Matching historical schedules remains outstanding. The known
change-only sampling bias prevents interpreting pair availability as population
coverage. Numeric classification remains provisional (integers 0..998).

Implementation: audit_historical.py, requirements-analysis.txt, and four optional
fixture tests for time-window boundaries, missing outcomes, special-status
preservation, and cross-train/date isolation. All 16 project tests pass in .venv.
An initial date/time SQL type mismatch was caught by running on the actual
archive and corrected; unit tests alone had not exercised file ingestion.

Decision: approve the archive for conditional observed-update exploration only.
Before claiming fixed-horizon prediction quality, collect regular prospective
snapshots and specify independent chronological validation and label eligibility.
