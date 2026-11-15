# Historical observed-delay pilot

Recorded November 8, 2026 with the first baseline run, before ML training.

## Question and target

Can a model improve on predicting that a train's current reported delay will
remain unchanged at its next stored update within an 8–12 minute window?
This is an exploratory regional-rail task, not actual arrival prediction.
Route linkage for Paoli/Thorndale is unresolved.

## Selection rules

- Reviewed 2025 archive; SHA-256 enforced by baseline_delay.py.
- Local source times 06:00 inclusive to 22:00 exclusive.
- Pair within the same source service date and train number. These keys are
  provisional grouping identifiers, not independently verified journeys.
- Choose the first stored update at or after +8 minutes; accept through +12.
- Select the outcome before filtering status values, so invalid outcomes are
  never skipped in favor of a later valid value.
- Provisional numeric range 0–997. Exclude 998 as unresolved and 999 as special.
  Reject pairs with intervening nonnumeric/special values. Do not forward fill.
- No numeric outlier clipping. Development values span 0–119, with 294 code-999
  rows and no code-998, negative, null, or greater-than-999 values.

## Chronological evaluation

December 1–4, 2025: training/development. December 5: validation.
December 6–7: reserved test dates; no prediction metrics computed.
The earlier feasibility audit already examined aggregate eligibility for all
seven dates. Thus the test dates were not entirely unseen during data exploration.
Persistence has no fitted parameters; its training score is descriptive.
Future learned models must fit preprocessing and parameters only on training
records, using features available at the anchor time. No random row split.

## First baseline result

| Split | Numeric anchors | Eligible pairs | Coverage | MAE (minutes) |
|---|---:|---:|---:|---:|
| Dec 1–4 | 45,732 | 34,254 | 74.90% | 2.658 |
| Dec 5 | 11,151 | 8,238 | 73.88% | 2.482 |

MAE is mean(abs(predicted delay minus observed later reported delay)).
Validation signed mean error is -0.783 minutes: on average this baseline
underpredicts the eligible later reports. Median absolute error is 2 minutes.
Seven training pairs were excluded for intervening special status values.
Daily and horizon-specific metrics are saved in the ignored JSON report.

## Interpretation and next experiment

The archive omits unchanged values. Missing updates do not distinguish unchanged
delay from missed collection. This biases eligibility toward changing reports;
these scores cannot establish all-train or exact-ten-minute performance.
Pairs overlap and are not independent samples. One development week and a
weekday-validation/weekend-test split limit generalization. Minutes are the
working unit supported by upstream code, pending maintainer confirmation.

Next: construct features from past reports only, inspect examples manually,
and compare a simple fitted model against persistence on the identical eligible
validation rows. Report coverage beside error and examine daily/horizon variation.
Keep test metrics reserved until feature choices and evaluation rules are fixed.
Broader date coverage and live-data validation remain necessary before strong
claims. See HISTORICAL_DATA_REVIEW.md for source evidence and attribution.


## First fitted model — November 8

Implemented a median-change regression model: the learned target is later
reported delay minus current reported delay. Prediction adds the learned change
to current delay and floors at zero. This is supervised learning: group changes
come from labeled training examples, not hand-written predicted changes.

Feature rules fixed before the first model run: current delay bins 0, 1–3,
4–7, 8–15, 16+; trend falling/unchanged/rising from the immediately previous
stored report on the same train/date, provided it is numeric and at most
30 minutes old; otherwise missing. Never skip special reports to find an older
numeric one. A group needs 30 training examples; otherwise use its delay-only
median, then the global training median. No future horizon or outcome is a
feature. Preprocessing uses past reports before filtering for available labels.
No hyperparameter search or validation-based refit was performed.

| Method | Training MAE | Validation MAE |
|---|---:|---:|
| Persistence | 2.6584 | 2.4820 |
| Learned delay-only | 2.5393 | 2.4416 |
| Learned delay + history | 2.5194 | 2.4408 |

All methods use identical rows: 34,254 training and 8,238 validation examples.
The relative validation reduction versus persistence is about 1.7%; history
adds less than 0.001 minute over delay alone. This is not evidence of meaningful
operational improvement or statistical significance. No model-selection claim
or test-set result. Weekend test dates remain unscored.

Reproduce with `.venv/bin/python train_delay_model.py`. Parameters and daily
metrics are saved in data/processed/model_development.json (ignored). A compact
aggregate report is versioned in docs/MODEL_DEVELOPMENT_RESULTS.json.
Next: inspect errors and learned groups, then broaden chronological development
coverage with a documented plan before evaluating the reserved test dates.


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
