# MNEME P0.4 FakeHost integrated receipt

Status: **PASS (network-free integration control).**

The P0.4 runner now joins the immutable P0.3 prepared run with writable P0.2
forks, finite developmental schedules, boundary checkpoints, private frozen
evaluation copies, and external evaluation receipts.  Developmental requests
are built only from the declared fixture record; accepted history is never
added to later prompts.  Evaluation uses `FrozenEvaluationView` and does not
write to the subject store or checkpoint.

Validation on 2026-09-18:

* `pytest -q`: 95 passed.
* `ruff check .`: passed.
* `mypy src/mneme`: passed.
* Focused runner tests: pause/resume exact-once behavior, no-history prompt
  construction, uncertain-operation non-regeneration, and prepared-order/
  host-fingerprint rejection passed.
* A prepared fixture-pack run was executed through the public runner seam;
  it completed one developmental call and two evaluation calls and produced a
  sanitized baseline report.

The runner persists execution state and a journal under `execution/<run-id>/`,
keeps these records outside the immutable prepared-run tree, and reconstructs
fixture data from digest-pinned published inputs.  Re-execution uses stable
operation/check coordinates and P0.2/P0.3 idempotency records.

The bounded real `google/gemma-4-E4B-it` acceptance is recorded separately in
`MNEME_P0.4_Real_Gemma_Baseline_Receipt.md`.
