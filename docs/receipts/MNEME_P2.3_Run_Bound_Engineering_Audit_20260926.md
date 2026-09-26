# MNEME P2.3 run-bound engineering audit

Date: 2026-09-26  
Audited historical execution chain: `p2-pilot-recovery-20260924p` → `p2-pilot-recovery-20260924q` → `p2-pilot-recovery-20260924r`  
Provider calls during audit: none  
Disposition: **ENGINEERING AUDIT NOT PASSED / HISTORICAL EVIDENCE INSUFFICIENT FOR THE STRONG AUDIT**

## Purpose

This receipt applies the current durable `audit_pilot_run()` checks to the
preserved P2.3 continuation artifacts. It does not rewrite or augment those
artifacts, and it does not reclassify the historical scientific result.

The audited continuation is split across immutable run directories. The q run
contains the developmental, extraction, assessment, and early evaluation
artifacts; the r run contains the resumed evaluation tail. The current audit
implementation is run-bound and does not silently combine separate runs into a
single passing inventory.

## Preserved artifact evidence

| run | status in artifact | direct JSON inventory | run verification |
|---|---:|---:|---:|
| `p2-pilot-recovery-20260924q` | `RUNNING` | development 8, extraction 8, assessment 14, evaluation 38; 59 valid reservations | failed |
| `p2-pilot-recovery-20260924r` | `COMPLETE` | development 0, extraction 0, assessment 0, evaluation 109; 107 returned reservations | passed |

The q and r state ledgers report the same final developmental counters
(`development_completed=58`, `extractions_valid=48`,
`assessments_completed=48`, `evaluations_completed=144`,
`admitted_relationships=23`), but those counters do not replace the missing
run-bound artifact inventory.

The q/r run-manifest and pilot-state file digests were retained during this
audit:

* q `run-manifest.json`: `91028c4ed6d0969ce63d56e6aa60b9e26ab679ad888411636b2684129fabfbe8`
* q `pilot/state.json`: `1adf20955638b07d613b3ed8bfaeb950578c17729f0a2660fa0d2e79189148c9`
* r `run-manifest.json`: `bebbe3ee200613c18735007cec6aba4806aef4274fb98359ae879644d1052570`
* r `pilot/state.json`: `df5bd74b22aa48a99a62fe3dc5c5989900025785753a898a48e6595f2908ebe9`

## Run-bound audit result

The current audit was executed read-only against r with the preserved subject
stores. It produced `FAIL`, with these results:

| check | result | reason |
|---|---|---|
| durable pilot run | PASS | r's published tree verifies under its historical artifact rules |
| call coordinates | PASS | no unexpected coordinates in the audited r ledger |
| terminal reservations | PASS | audited r reservations are terminal |
| unique reservations | PASS | 107 unique reservations in the audited r tree |
| development coordinates | FAIL | r contains no development artifacts/reservations; they are in q and predecessors |
| extraction coordinates | FAIL | r contains no extraction artifacts/reservations |
| evaluation coordinates | FAIL | r contains 107 direct evaluation reservations versus the full 144-coordinate schedule |
| host provenance | PASS | returned host fields in r match their reserved/configured bindings |
| study-progress ledger | FAIL | the audited run's ledger is a continuation fragment, not a standalone full-schedule inventory |
| assessment reservations | FAIL | r contains no assessment reservations; those are in prior runs |
| artifact inventory | FAIL | the single-run inventory lacks development, extraction, assessment, and the first evaluation segment |
| evaluation-isolation receipts | PASS | all evaluation receipts present in r have equal before/after developmental digests |
| subject authority and replay | FAIL | the preserved run predates prepared subject/replay snapshots; those snapshots are unavailable |

The q predecessor cannot be promoted to a pass: its persisted status is
`RUNNING`, its published tree contains the zero-byte
`pilot/reservations/evaluation-s0-p6-r1.json` left by the documented
filesystem interruption, and it predates the prepared subject/replay snapshot
required by the strong audit. The r continuation contains the completed
`evaluation-s0-p6-r1` coordinate and its result matches that intended resumed
coordinate, but the current single-run audit does not combine continuation
inventories and therefore cannot prove the full pilot by itself.

The q/r pair shares experiment contract digest
`650faa6cf317aa459f8031b2385d7dbb0337590b0e783e274e17b94630f5bf5e`.
The q state also records an idempotent reuse of `development-s1-e16` from its
predecessor; that reuse is historical evidence, not a second provider
generation or duplicate developmental credit.

## Interpretation

This is an **evidence limitation**, not a claim that the historical pilot did
not execute. The existing counters, scientific receipts, and historical
`COMPLETED_INADEQUATE` disposition remain authoritative. The strong engineering
acceptance claim is not retroactively granted because the continuation split
pre-dates the current run-bound snapshot and inventory contract.

No provider calls were made. No historical artifact was modified. The central
separated-support/consolidation criterion and cumulative campaign accounting
remain unresolved independently of this audit.
