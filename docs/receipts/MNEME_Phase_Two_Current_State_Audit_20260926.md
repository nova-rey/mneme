# MNEME Phase Two current-state audit

Date: 2026-09-26  
Audited commit: `435538bdb22f5dc97a72e59ae6f7088c081f314e`  
Remote: `origin/main` at the same commit

## Disposition

Phase Two is not complete. P2.1 and P2.2 have accepted engineering receipts,
and the current tree passes the full offline validation suite. P2.3 remains
`WAITING` on the unresolved pilot-adequacy review dependency. The required
separated-support/consolidation opportunity was not demonstrated, and the
cross-thread v6 supplement was `INCONCLUSIVE` because the MNEME twin had no
eligible learned route at readout. No Phase Two release tag was created and
Phase Three has not begun.

## Gate status

* **P2.1:** accepted by the existing prerequisite, learner-trace,
  own-output, publication, and semantic-review receipts. The learner and
  publication path are replayable and covered by the current test suite.
* **P2.2:** accepted by the six-scenario, feedback/rebuild, identity,
  fork/revocation, recovery, and modeled-advance receipts. The current schema
  and recovery paths remain provider-free in this audit.
* **P2.3 engineering:** the accepted pilot and later evidence establish
  production-shaped execution, persistence, coordinate resume, provenance,
  evaluation isolation, and artifact/replay checks. The specialist-derived
  and cross-thread evidence did not change that historical pilot disposition.
* **P2.3 adequacy:** unmet. No qualifying separated support caused a live
  consolidation transition. The v6 matched readout is not a substitute: its
  learner snapshot had zero positive support/accessibility and no eligible
  route, so it contained no MNEME treatment effect to compare.
* **P2.3 research:** exploratory evidence is inconclusive. The v6 paired
  outputs showed sampling differences, but both twins were effectively
  no-memory for the tested readout.

## Call-accounting reconciliation

The scientific review packet recorded a baseline of **353 returned calls**
before the cross-thread v6 work. The subsequent preserved v6 work adds:

| Segment | Calls | Persistence/disposition |
| --- | ---: | --- |
| Original cross-thread v6 execution | 82 | Returned and persisted |
| Learner-eligibility corrected local M readouts | 18 | Returned and persisted; the 18 original controls were reused |
| Corrected two-stage Qwen blind evaluation | 2 | Returned and persisted |
| First blind-evaluation persistence attempt | 1 | Provider returned; local `TokenUsage` serialization failed before persistence; no result was recoverable and no developmental state changed |
| **Additional calls/attempts** | **103** | **82 + 18 + 2 + 1** |

The reconciled campaign total is therefore **456 returned/attempted calls**
(353 + 103). Of those, 455 have persisted result evidence and one returned
provider attempt is recorded only by the corrected evaluation receipt because
the local persistence failure occurred after the provider response. The
unpersisted attempt is not treated as successful evidence.

The queue's prior operational contingency ceiling was 399 calls. The current
ledger is 57 calls beyond that ceiling. This is an accounting and authority
blocker, not a reason to make more calls: no additional provider execution is
performed by this audit. Historical calls and receipts remain unchanged.

## Validation

At audited commit `435538b`:

* `pytest -q`: **441 passed**;
* Ruff: **passed**;
* strict mypy over `src/mneme`: **passed**;
* wheel/fresh-install package smoke: **passed**;
* work-queue status: 11 `DONE`, P2.3 `WAITING`, no `READY`, `RUNNING`, or
  `VALIDATING` packages;
* work-queue validation: **valid**;
* hard-idle census: P2.3 waits on
  `review:p2.3-pilot-adequacy-after-normalization`.

No provider calls were made during this audit. Historical P2.3 pilot,
supplement, specialist, and v6 evidence are preserved; none is reclassified
as a passed adequacy gate.

## Required review before further execution

The project needs an explicit decision on both facts recorded here: whether
the unmet adequacy criterion remains `COMPLETED_INADEQUATE`, and how the
already-observed 456-call cumulative ledger is reconciled against the former
399-call contingency ceiling. Until that decision is recorded, P2.3 remains
waiting and no Phase Two closure or Phase Three work is justified.
