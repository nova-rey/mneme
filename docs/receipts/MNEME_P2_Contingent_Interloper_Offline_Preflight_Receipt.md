# P2 contingent-conversation offline wire/preflight receipt

- **Document:** `P2-SUPPLEMENT-INTERLOPER-01`
- **Date:** 2026-09-24
- **Provider calls:** 0
- **Historical P2.3 state:** preserved; no old receipts or call ledger entries changed
- **Implementation:** `src/mneme/experiments/contingent.py`
- **Offline result:** PASS for the wire/preflight boundary

## Checks

The disposable authored-data check exercised the existing P0.2 continuity,
P1/P2 interpretation/publication, learner, and frozen-comparator boundaries.
The focused suite passed **39 tests**:

```text
PYTHONPATH=src pytest -q \
  tests/test_development_learner.py \
  tests/test_phase_two_publication.py \
  tests/test_phase_two_pilot_runtime.py \
  tests/test_contingent.py
39 passed
```

The new adapter has deterministic coordinates for partner, subject,
extraction, assessment, evaluation, checkpoint, and empty-ancestor operations.
The partner and assessor roles are separate ledger roles even when they share a
Qwen fingerprint. Interactive context includes only the latest four complete
pairs; open-loop generation includes prior partner messages but no subject
answer. Subject requests carry `synthetic_environment_model` origin metadata
without administrative IDs. Evaluation uses private checkpoint copies and no
partner context.

The fixture check confirms three distinct chapter prompts and a 24-turn
schedule. Existing learner/publication tests cover target carryover,
opportunity accounting, actual-exposure gating, consolidation transitions,
and dependent replay ancestry; the supplement adds schedule, role-isolation,
bounded-context, prompt, and origin-boundary tests. No defect requiring a
threshold, alias, route, or learner-coefficient change was found in this gate.

Ruff and strict mypy also pass in the local validation environment. No hosted
request was made. Live execution remains a separate bounded step under the
supplement's 300-call envelope.
