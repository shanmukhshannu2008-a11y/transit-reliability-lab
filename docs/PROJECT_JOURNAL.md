# Transit Reliability Lab — Progress Journal

Last updated: November 8, 2026 (America/New_York).
Owner: Shanmukh Aravapalli. GitHub: shanmukhshannu2008-a11y.
Repository: https://github.com/shanmukhshannu2008-a11y/transit-reliability-lab

## Purpose

Investigate whether public SEPTA data can support useful, rigorously evaluated predictions for the Paoli/Thorndale line, which Shanmukh rides. Develop technical understanding alongside a substantial portfolio project. The intended distinctive contribution is measuring the effect of missing or stale observations on prediction quality and uncertainty, not claiming to invent transit prediction.

Time budget: 6–7 hours weekly around Drexel coursework. Target: a defensible demonstration before March 2027 co-op applications. No model has been trained. Actual arrival labels remain unresolved.

## Evidence policy

Commit dates and file contents below were checked against a fresh GitHub clone on November 2. Live run results are attributed to terminal output shared by Shanmukh. Do not turn planned features, simulated checks, or feed values into claims about measured real-world prediction accuracy. This retrospective journal was written November 2; earlier entries were not written contemporaneously.

## October 14 — First collector

Published commit: 74eacae, Add SEPTA snapshot collector with basic data quality checks.

Built a Python script that requests TrainView, saves the original response with a UTC collection timestamp, filters Paoli/Thorndale records, and flags missing current stops and late=999. Excluded raw snapshots from Git. Resolved Python HTTPS certificate setup. Practiced delay, absolute prediction error, and MAE on explicitly fictional examples.

Shared terminal evidence: five snapshots between 15:56:11 and 16:05:09 UTC. Train 9517 reported Suburban Station then Gray 30th Street, with late values 4, 4, 3, 4, 5. Train 5300 showed an empty current stop and late=999.

Lesson: collection time is not source update time. Repeated stop fields do not establish that a train is stationary. A feed status is not automatically an observed arrival outcome.

## October 16 — Replay and status interpretation

Published commits:
- 11e7772: Document collector usage and current data limitations.
- 147710f: Add saved snapshot inspection for a selected train.
- 81af9c6: Separate special train status from numeric delay values.

Built inspection of saved snapshots and parse_lateness. The parser preserves raw data and represents 999 as a separate cancelled_or_suspended status with numeric delay None. Shared output verifies this behavior across the five historical snapshots.

Evidence for interpretation: a 2021 SEPTA developer discussion says 999 was borrowed from rail to indicate cancellation or suspension. This historical explanation is not independent confirmation of the operational state of train 5300 in 2026.
Source: https://groups.google.com/g/septadev/c/ezUUfmLWBKQ

Lesson: missing numeric data must not become zero. Keep raw evidence alongside derived interpretations.

## October 27 — Command-line inspection

Current published commit: 33899de, Allow selecting a train when inspecting saved snapshots.
Original identifier before author-email correction: f9bead6.

Added an argparse train-number argument and help text. Author date remains October 27, 2026, 13:10:06 -04:00. Author email now matches the supplied GitHub noreply address. These metadata were verified November 2. Contribution-calendar display itself was not checked.

Lesson: Git commit authorship and GitHub authentication are separate; a successful push does not ensure profile attribution.

## November 2 — Repeated collection and review

Published commit: 908f956, Add bounded collection sessions with timeout handling.

Implemented count and interval arguments, a 60-second minimum wait after each attempt, a 45-second child-process timeout, success/failure counts, and interruption handling. This is a manually started finite session, not a hosted background service.

Shared live evidence: three successful snapshots at 15:15:52, 15:16:52, and 15:17:52 UTC. Each included two Paoli/Thorndale trains (9509 and 9518), producing six train observations, not six distinct trains. Both reported stop transitions by the third snapshot.

Independent checks run against the published code on November 2:
- All four Python source files compiled successfully.
- Existing parse_lateness assertions passed.
- Invalid count was rejected before collection.
- Inspector --help rendered successfully.
- Mocked child-process failure followed by two successes: correct totals and continued attempts.
- Mocked timeout followed by two successes: correct totals and continued attempts.
- Mocked interruption during the wait: clean session stop with no next attempt.

The last three are simulated orchestration checks, not actual network-outage or operating-system process-kill tests. They were run as a review harness and have not been committed to the repository.

## Repository and local placement review

Original folder exists directly at /Users/shanmukharavapalli/Documents/transit-reliability-lab. This is a sensible dedicated project location; moving it is unnecessary.

The operating system denied reading its contents even after this session received folder permissions. Therefore the local working tree, unsaved changes, ignored files, and exact local/remote agreement could not be independently checked. No files in that original folder were changed.

GitHub was independently reachable using Git. main points to 908f956cbd303adbcc76f77414c6c7fcad3166f4. A temporary review clone was used, not a replacement working project.

Published files: .gitignore, README.md, collect_snapshot.py, collect_session.py, inspect_snapshots.py, transit_fields.py. No raw snapshots or .env files are tracked in the current published tree. This is not a full historical secret audit.

## Findings and priorities

1. README is outdated: it still describes manual-only collection and omits the session and inspector usage instructions. Fix documentation alongside the next change.
2. Collection code performs network work at module import time. Move executable work behind main() so it can be tested without live requests.
3. Existing assertions are useful first checks but are not a persistent automated test suite. Convert meaningful behavior checks to unittest tests and run them in CI.
4. Session currently exits successfully even if all child attempts fail. Define and test an exit-code policy before using a scheduler.
5. Parser handles 999 but is not a complete verified status-code specification. Do not assume every other integer is a valid measured delay; the 998 discussion concerns a different feed context.
6. Inspector groups matching train numbers across every date. Add a date filter or explicit journey grouping before treating these rows as one journey.
7. Snapshot validation checks only the outer list. Malformed rows and interrupted file writes need coverage and a clear policy.
8. We have no credible ML performance results yet. The critical next decision is whether actual arrival labels or another defensible target can be obtained.

## Next milestone — Data feasibility, 12–14 hours

Goal: produce a small reproducible dataset and a documented decision about what prediction task is supportable.

- 2 hours: inspect candidate arrival/historical sources, access conditions, timestamps, units, and linkage to train trips. Record evidence and unresolved questions.
- 3 hours: create a deterministic table exporter with source filename, collected_at, train number, line, stops, raw late, parsed value, status, and quality flags. Retain repeated observations; do not mistake them for independent events.
- 3 hours: refactor collection into testable functions and add fixtures plus tests for normal, malformed, timeout, and interruption cases. Never contact live SEPTA in ordinary unit tests.
- 2 hours: audit coverage, gaps, special statuses, and trip/date identity. Report observation counts separately from distinct journeys.
- 2–4 hours: specify a target, information available at prediction time, chronological evaluation split, and simple baseline. Run a pilot only if labels and enough data exist; otherwise document why it is blocked.

Acceptance gate: either demonstrate defensible labels and a baseline evaluation setup, or explicitly narrow the task to future reported delay. If neither is worthwhile, pivot before adding more interface features. No accuracy target is promised in advance.

## Learning method going forward

Work in larger milestones with small explanations at each design decision. Shanmukh owns meaningful implementation and can explain the assumptions, failures, and tradeoffs. Each milestone ends with evidence, documentation, and a coherent commit. No empty commits, invented results, or fabricated activity.

## Entry template

Date:
Question or objective:
Implemented:
Evidence and commit:
Tests performed (live / fixture / mocked):
What I learned and can explain:
Failures and limitations:
Next decision:


## November 4 — Journal placement and first analysis table

Original local project access now works. Copied this journal and the verified
progress brief into docs/ in the existing Documents/transit-reliability-lab
folder. No relocation or replacement checkout was necessary. The previously
reported access limitation remains a historical note about November 2.

Implemented export_observations.py and seven unittest cases. The exporter
preserves source filename and record index, timezone-aware collection time,
train identifiers as strings, raw lateness JSON, parsed status, and flags.
Repeated observations remain separate. It validates before writing and uses
a temporary file plus replacement so a failed export does not overwrite the
previous dataset. Added processed output to .gitignore and updated README.

Verified against actual local files: nine snapshots yielded 24 Paoli/Thorndale
observations, of which five have quality flags. These are not 24 unique trains
or 24 independently verified arrival events. Seven automated tests passed:
line filtering and repeated observations, special-status and raw-type
preservation, unknown versus zero, malformed-input preservation of a previous
export, timezone validation, missing input, and chronological ordering.

Learning focus: one row represents a train observation at collection time;
provenance makes derived results traceable; missing is different from zero;
fixtures make tests repeatable without the live service.

Changes are local and uncommitted at this entry. No push was performed.
Next: walk through one exported row together, audit time coverage and gaps,
and resolve available ground truth before choosing a prediction target.
The wider collector refactor and status-code verification remain outstanding.


## November 5 — Collection coverage audit

Implemented audit_coverage.py using raw snapshots and existing export validation.
Added five tests; all 12 exporter/audit tests passed. Tests cover local calendar
dates, long gaps, empty/nonmatching snapshots, repeated train identifiers,
threshold boundaries, duplicate timestamps, and missing input.

Actual local findings:
- October 14: 5 snapshots, 15 matching observations, 3 distinct train numbers;
  11:56:11–12:05:09 Eastern; elapsed span 8.97 minutes; largest gap 285.17 seconds.
  10 numeric statuses, 5 historical cancelled/suspended interpretations.
- November 2: 4 snapshots, 9 matching observations, 3 distinct train numbers;
  10:15:52–10:24:02 Eastern; elapsed span 8.18 minutes; largest gap 370.03 seconds.
  9 numeric statuses.
- Three consecutive-snapshot gaps exceed the project-selected 180-second
  threshold, including the gap between dates. This is not an API freshness test.

Conclusion: 24 observations across two short windows are sufficient for tool
verification, not credible training/evaluation. Elapsed spans include gaps;
we did not measure continuous monitoring, actual arrivals, or prediction accuracy.
Next priority: investigate outcome-label sources and define a feasibility
experiment before committing to a long collection campaign. A longer supervised
collection session can test pipeline stability, but does not solve label validity.

Learning focus: observation count versus unique train identifiers; local date
versus service date; elapsed range versus sampled coverage; reproducible audits.
This audit and its documentation are saved locally, not committed or pushed.


## November 5 — Historical source inspection

Inspected upstream scraper, export, and reporting code; saved a first-100-row
convenience sample plus checksums locally. Evidence supports minutes as the
working unit despite conflicting dataset-card wording. Confirmed that unchanged
values are omitted, making missing polls versus unchanged reports ambiguous.
Archive lacks route/station fields; date-compatible route linkage remains open.
Decision: exploratory only, not approved as general fixed-horizon ground truth.
See HISTORICAL_DATA_REVIEW.md for evidence, caveats, and next experiment.
No bulk download, model training, commit, push, or external message performed.


## November 8 — Bounded historical feasibility pilot

Added optional DuckDB environment, pinned dependency, historical audit, and four
fixture tests. Downloaded and checksum-verified one 8.25 MB 2025 partition;
kept all downloaded data ignored. Audited one daytime week (69,906 records).
51,887 / 69,611 numeric anchors have a numeric observed update under the 8–12
minute rule (74.54%). This is eligibility, not prediction accuracy. Scope is
regional rail; date-compatible Paoli/Thorndale mapping remains unresolved.

All 16 tests passed in .venv. Actual archive execution exposed and resolved a
SQL date/time type mismatch not covered by the matching-function fixtures.
Source evidence and limitations are in HISTORICAL_DATA_REVIEW.md. No model
trained, no performance improvement claimed, and no changes committed/pushed.
Learning: labels, conditional sampling, temporal matching, and the difference
between unit-level checks and running an entire analysis on actual input.


## November 8 — First development baseline

Implemented baseline_delay.py: predict unchanged reported delay at the first
stored update 8–12 minutes later. Audited December 1–5 values (57,177 rows,
numeric range 0–119, 294 code-999 rows). Conservatively excluded 998 and rejected
pairs crossing intervening special statuses. Verified archive checksum.

December 1–4: 34,254 eligible pairs, MAE 2.658 minutes.
December 5 validation: 8,238 eligible pairs, MAE 2.482 minutes, 73.88% eligibility.
December 6–7 was not scored; the earlier feasibility audit included aggregate
eligibility for those dates. No model has been trained and no improvement claimed.
This measures conditional future reported delay, not actual arrival accuracy.

Learning: persistence is the reference a learned model must beat; MAE measures
average error size; chronological splits prevent mixing later observations into
training. Overlapping pairs and missing unchanged updates limit interpretation.
All 21 tests passed, including five new baseline checks. The full baseline also
ran successfully on the reviewed archive. Rules and results recorded in
EXPERIMENT_PLAN.md. Changes remain local; no push.


## November 8 — First supervised model and ablation

Built train_delay_model.py, a median-change regressor with current-delay bins
and previous-report trend. Training only uses December 1–4. Compared persistence,
delay-only learning, and delay-plus-history on identical December 5 examples.
Validation MAEs: 2.4820, 2.4416, and 2.4408 minutes respectively. Approximately
1.7% reduction versus persistence; negligible added benefit from history.
These conditional scores do not establish actual arrival accuracy or significance.
Reserved December 6–7 remains unscored. No tuning search performed.

All 26 tests passed, including five new checks for past-only features, status/gap
handling, train/date isolation, median/fallback behavior, and end-to-end exclusion
of test dates and validation labels from fitting. Ran the complete model on the
checksum-verified archive. Saved reproducible aggregate results and learned
parameters in docs/MODEL_DEVELOPMENT_RESULTS.json.

Learning: features describe what is known at prediction time; labels describe
what happens later. An ablation removes one feature to check its contribution.
Here the history ablation shows that more features need not help. Next: inspect
mistakes and broaden date coverage before stronger modeling or final testing.
Prepared this work for the user's requested Git commit; raw data remains ignored.

## November 14 — Validation error analysis

Inspected the largest errors and source reports for trains 5229 and 5322.
Both showed abrupt reported-delay drops toward zero; 5229 subsequently
reported 999. Their operational causes remain unverified. Kept all
eligible examples in evaluation.

The worst 100 of 8,238 validation examples contributed 9.3% of total
absolute error. Compared with persistence, the model improved MAE for
falling-delay and missing-history groups, but slightly worsened MAE
for rising delays, the largest group. Only 34 examples had unchanged
previous delay, limiting interpretation.

Learned that aggregate improvements can hide subgroup weaknesses.
These are exploratory findings from one validation day, not evidence
of actual arrival accuracy. Reserved test dates remain unscored.

Next: check stability across more chronological development dates
before changing the model based on these findings.

## November 14 — Expanding-window development evaluation

Added walk_forward.py. Fixed protocol: training starts November 17, 2025;
validate each day November 24–December 5 using only preceding days. Fit fresh
models for each day; keep model rules unchanged. December 6–7 is never loaded
or scored. December 5 was previously inspected, so this is development analysis,
not independent final testing. All methods use identical eligible rows per day.
Coverage and trend-specific scores are saved alongside model parameters.

Across 12 days, pooled MAE: persistence 3.0084, delay-only 2.7987,
delay-plus-history 2.6952 minutes. History model beats persistence on 8/12 days.
Much of the improvement comes from November 24 (5.549 vs 3.734 minutes).
December 5 now worsens (2.482 vs 2.541) with the longer training window:
more training data does not guarantee improvement when patterns vary over time.
No significance, actual-arrival-accuracy, or Paoli-only claim. Overlapping pairs,
shared training windows, and outcome availability bias remain limitations.

All 29 tests pass, including new expanding-window, future-label isolation,
reserved-date boundary, and missing-fold checks. Also moved total-error summation
outside the printing loop. Reproducible report: docs/WALK_FORWARD_RESULTS.json.
Changes saved locally, not committed or pushed. Next: investigate November 24
and compare daily patterns before changing model settings.


### Walk-forward follow-up — influential-day analysis

November 24's rising-delay group contributed 20,627 minutes of summed
absolute-error reduction. Its top 10 train numbers contributed about
17.4% of that net reduction, so the gain extended beyond a few trains.

Inspected train 5318: reported delay increased from 1 to 119 minutes
over approximately 118 elapsed minutes. The cause remains unverified;
these records cannot distinguish operational delays from feed behavior.

Across all 12 validation days (92,474 examples), the history model
reduced MAE from 3.0084 to 2.6952 minutes, a 10.41% improvement.
Excluding November 24 from scoring left 80,886 examples across 11 days:
MAE decreased from 2.6444 to 2.5464 minutes, a 3.71% improvement.

November 24 remains in the official evaluation. This sensitivity check
does not remove it from the training history of subsequent folds.
Results show uneven development performance, not verified arrival
accuracy or independent final-test performance.

Next: save the evaluation work, then compare against a simple
recent-trend extrapolation baseline using only information available
at prediction time.


## November 25 — Recent-trend baseline

Added a baseline that extrapolates the previous reported-delay change
over a fixed 10-minute horizon. Uses only earlier reports from the
same train/date, falling back to persistence for invalid or missing
history or gaps over 30 minutes. Predictions are floored at zero.

Evaluated on the same 92,474 examples across 12 development days:
- Persistence MAE: 3.0084 minutes
- Recent-trend MAE: 5.6724 minutes
- Learned-history model MAE: 2.6952 minutes

Recent trend beat persistence only on November 24. Extending the
latest rate was generally unreliable in this sample. The causes
remain unresolved, and the 8–12-minute outcome window differs from
the baseline's fixed 10-minute forecast.

All 35 tests passed. Reserved test dates remain unscored.
Next: compare a small decision-tree regressor using the same folds.

### November 25 — First scikit-learn decision tree

Trained a decision-tree regressor on delay change using current delay,
previous delay change, time between reports, and a missing-history flag.
Fixed settings: maximum depth 4, minimum 100 examples per leaf,
squared-error training objective, random state 42.

Compared methods on identical examples across 12 walk-forward folds:
- Persistence MAE: 3.0084 minutes
- Recent-trend MAE: 5.6724 minutes
- Learned median-change model MAE: 2.6952 minutes
- Decision-tree MAE: 2.7881 minutes

The tree improved on persistence by approximately 7.3%, but performed
worse than the simpler median-change model. Increased model flexibility
did not improve pooled development MAE in this experiment.

Fixed report serialization by converting NumPy integer values to Python
integers. All 40 tests passed; saved report checks confirmed 12 folds
and 92,474 validation examples. Reserved test dates remain unscored.

Next: visualize daily performance to communicate variability.

### November 25 — Historical results dashboard

Built a local Streamlit dashboard using a versioned aggregate results
bundle. Added model comparisons, an interactive daily chart, a date
selector, sensitivity results, and evaluation limitations.

Validated report dates, example counts, and consistency between daily
and pooled scores. Manually checked model selection, date changes,
and the limitations section.

Added three automated dashboard tests. All 43 project tests passed.
The dashboard requires no raw archive or model retraining.
It is running locally; public deployment and the train timeline remain
outstanding.

### November 25 — Historical train timelines

Added three selected case studies containing 166 stored reports.
Packaged the examples with source attribution, archive checksum,
selection windows, and limitations.

The dashboard displays numeric reports as dots without connecting
missing intervals. Special statuses appear separately; code 999 is
never plotted as a numeric delay. These are archived observations,
not model predictions.

Manually verified train selection and special-status display.
Added tests for example counts, separation of special statuses,
and dashboard selection behavior. All 46 tests passed.
The timeline runs from its bundled examples without the raw archive.


### November 25 — Public dashboard deployment

Deployed the historical dashboard to Streamlit Community Cloud.
Verified summary metrics, model/date controls, and train 5229's
special-status display in a private browser window.

The hosted app uses committed aggregate reports and selected timeline
examples. It requires neither the full archive nor a local server.
It displays historical results; live prediction is not implemented.

### November 25 — Saved model and standalone predictions

Trained the median-change model on 34,254 examples from December 1–4,
2025, and saved its parameters, feature policy, and training metadata.

Reloaded the model and verified identical predictions on all 8,238
December 5 validation examples. Added a command-line predictor for
manually supplied current and previous reports.

Added five tests covering history categories, invalid inputs,
missing/stale history, and saving/loading with known predictions.
All 51 tests passed. Reserved test dates remain unscored.

Prediction does not retrain or read the archive, but currently imports
training modules. Next: separate the runtime from training dependencies,
then add an explicitly labeled manual prediction demo to the dashboard.


### November 25 — Lightweight prediction runtime and dashboard demo

Separated saved-model inference from training-library imports.
Confirmed command-line prediction works with site-packages disabled.
Verified identical predictions against the original saved-model loader
on all 8,238 December 5 validation examples, without retraining.

Added a manual prediction form to the dashboard with numeric-history
and missing-history paths. Added automated form tests and ran the suite
successfully. The form uses the December 1–4 model and does not fetch
live reports. Reserved test dates remain unscored.

Local interaction checks passed. Public deployment verification pending.

### November 25 — Live observations panel and shared caching

Added on-demand SEPTA TrainView reports for Paoli/Thorndale.
Displayed collection timestamps separately from unknown feed-observation
freshness. Special and unknown values are not treated as numeric delays.

Manually verified session cooldown, preservation of the last successful
snapshot during network failure, and recovery after connectivity returned.

Added a 60-second shared cache for successful responses and failures
within the running app. This is not a rate limiter across multiple
server processes. Dashboard snapshots are not persisted to the archive.

All 62 tests passed. New tests cover feed validation, status handling,
cache reuse, cached failures, copy isolation, and recovery after clearing
the cache. Public live-feed verification passed: the hosted app displayed a snapshot
collected November 25 at 8:11:17 p.m. EST, with 27 total reports and one
Paoli/Thorndale match. This confirms hosted connectivity and display,
not the accuracy or freshness of SEPTA's underlying observations.

Live reports are displayed only; the historically trained model is not
yet applied to them because sampling and feature compatibility remain
unresolved.