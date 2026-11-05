# Verified project progress brief

As of November 2, 2026. Prepared for reuse in a resume discussion or LinkedIn draft; not published or sent to another task.

Project: Transit Reliability Lab
Repository: https://github.com/shanmukhshannu2008-a11y/transit-reliability-lab

Motivation: Shanmukh rides the Paoli/Thorndale line and is investigating the reliability of its public train data as a foundation for ML.

Implemented and published:
- Python collector preserving timestamped TrainView snapshots locally.
- Paoli/Thorndale filtering and checks for missing stops and special status values.
- Saved-data inspection with a train-number command-line argument.
- Separation of late=999 from ordinary numeric delay using historical developer guidance.
- Finite repeated collection with wait intervals, subprocess timeout handling, and summary counts.

Evidence: published main commit 908f956; user-shared live run collected three snapshots successfully; independent review checked syntax, existing parser assertions, CLI validation, and simulated session failure/timeout/stop behavior.

Learning: HTTP/JSON, Python dictionaries and loops, timestamps, filesystem persistence, CLI arguments, subprocesses, basic testing, Git authorship and commits, and separating observations from inferred meanings.

Current limitation: no trained model, no measured predictive improvement, no verified actual arrival labels, no continuously hosted service. The project is an early data-engineering foundation, not a finished ML product.

Next: validate a prediction target, build a reproducible analysis table and automated tests, then compare baselines and models on later dates.


November 4 local update (not yet committed or published): added a deterministic
snapshot-to-CSV exporter and seven passing fixture-based tests. Nine local
snapshots produced 24 Paoli/Thorndale observations, five flagged. Every row
retains provenance. No ML accuracy or arrival-truth claims follow from this.
