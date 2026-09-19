# MNEME append-only engineering log

## 2026-09-17

- Initialized the MNEME repository and ingested the supplied project documents.
- Established P0.1 scope: host contracts, FakeHost, Gemma boundary, qualification, and repository hygiene.

## 2026-09-17

- Added the P0.1 work-queue package and moved it through candidate and validation review.
- Verified the cheap validation path: 7 tests, Ruff, and strict mypy pass.
- Completed the P0.1 queue package after recording all declared validation receipts; live Gemma remains credential-gated.

## 2026-09-17 remediation

- Separated generation-affecting request material from administrative run metadata.
- Removed unverified native structured-output claims, added representative schema checks, honest fallback rendering metadata, and offline provider failure coverage.
- Added mypy to CI. P0.1 implementation is substantially complete but remains WAITING on external live Gemma qualification.

## 2026-09-17 P0.1 remediation

- Proved FakeHost generation ignores administrative metadata while retaining visible-input and seed effects.
- Tightened structured qualification to separate JSON parsing from three representative schema validations.
- Exercised FakeHost failure reporting and added offline HTTP, timeout, malformed-response, provider-error, and response-shape coverage for Gemma.
- Marked Gemma rendering as the explicit MNEME fallback transcript and removed its unverified native structured-output capability claim.

## 2026-09-17 DeepInfra preparation

- Resolved `google/gemma-4-E4B-it` revision `ee0ef6023621cff504d758262d4e04895a5af4a2` as the downloadable local reference and recorded the model checksum.
- Added the credential-free DeepInfra OpenAI-compatible backend, offline provider-boundary tests, setup instructions, and live qualification command.
- Selected DeepInfra as the inexpensive live P0.1 backend; hosted exact-weight equivalence remains unknown and P0.1 stays WAITING on credentialed qualification.

## 2026-09-18 live P0.1 qualification

- Ran the bounded DeepInfra qualification with the user-provided credential; the credential was process-only and did not enter artifacts.
- Basic generation, multi-turn chat transport, and all three structured JSON schema cases passed; seed control remained correctly unsupported.
- Tightened structured prompts to require JSON-only output and deterministic temperature before the successful live run.

## 2026-09-18 P0.1 closure

- Credentialed DeepInfra qualification passed for `google/gemma-4-E4B-it`: basic generation, multi-turn transport, and 3/3 structured schema cases.
- Resolved the external live-qualification dependency and marked the P0.1 work package DONE; no P0.2 work was started.

## 2026-09-18 P0.2 plan approval and save

- Saved the complete approved P0.2 plan at `docs/Approved Plans/MNEME_P0.2_Durable_Lineage_History_Checkpoints_Plan.md` and linked it from the documentation index.
- Incorporated the three approval amendments: no future-mechanism Python contracts or fixtures; storage and export/copy permissions only; accepted-history digest terminology without behavioral-equivalence claims.
- Preserved the approved architecture, transaction lifecycle, acceptance demonstration, and four implementation chunks, adjusting only consequential scope, schema, and test wording.
- Validated the existing work queue: P0.1 remains DONE. The controller has no planning/approval state, so the queue is unchanged; plan approval is recorded here and in the saved plan.
- Documentation/planning changes only. No P0.2 production implementation was started; explicit implementation authorization is still required.

## 2026-09-18 P0.2 implementation

- Added the approved P0.2 SQLite state layer: immutable lineage records, accepted episodes, monotonic revisions, manifests, pending operations, host/run provenance, idempotent acceptance, stale-base rejection, and process-failure uncertainty handling.
- Added database-aware checkpoint and backup publication, read-only checkpoint inspection, independent child forks with copied ancestry, storage/export permission enforcement, schema checks, and CLI state commands.
- Added FakeHost storage, lifecycle, digest, checkpoint, fork, permission, idempotency, stale-state, read-only, and uncertain-operation tests; no future-phase Python contracts were introduced.
- Ordinary validation currently passes: 35 tests, Ruff, and strict mypy. P0.2 remains open pending the full acceptance demonstration, bounded real-Gemma receipt, final audit, and serialized queue validation.

## 2026-09-18 P0.2 external acceptance gate

- The full FakeHost acceptance demonstration completed and its receipt was saved under `docs/receipts/` with a local machine-readable artifact at `artifacts/p02_acceptance.json`.
- The bounded real-Gemma persistence demonstration could not run because `DEEPINFRA_TOKEN` is absent in this environment. P0.2 is therefore retained in the work queue as `WAITING` on `external:gemma-p02-acceptance`; it is not marked DONE.

## 2026-09-18 P0.2 audit correction

- Enforced the approved one-active-writer rule with an OS advisory lock around SQLite transactions and checkpoint copies.
- Corrected fork ancestry to record the durable checkpoint ID rather than a filename-derived label.
- Updated the approved plan status to show implementation underway and the real-Gemma gate still pending.
- Completed the remaining read-only CLI surface for checkpoint and operation listing/inspection plus explicit store recovery; validation remains network-free and no later-phase behavior was added.

## 2026-09-18 P0.2 acceptance closure

- Ran the bounded real DeepInfra Gemma interaction through a fresh P0.2 store; one episode was accepted at revision 1 with `google/gemma-4-E4B-it` and `DeepInfra` provenance.
- Reopened the real-model store read-only, verified the accepted revision, host fingerprint, foreign-key/integrity checks, and sanitized receipt; no credential or raw conversation was retained in the receipt.
- Completed the approved P0.2 acceptance demonstration and all declared checks: 35 tests, Ruff, strict mypy, FakeHost demonstration, and real-Gemma demonstration.
- Marked P0.2 DONE in the work queue. No P0.3, Phase 1, learning, association, personality, self-model, extraction, or neural-intervention work was started.

## 2026-09-18 P0.3 plan approval and save

- Saved the complete approved P0.3 plan at `docs/Approved Plans/MNEME_P0.3_Experiment_Contracts_Experimental_Isolation_Plan.md` and linked it from the documentation index.
- Incorporated the approved experiment-identity clarification: the human/scientific identity is the declared experiment name plus `contract_revision`; the canonical SHA-256 digest identifies the exact immutable contents of that revision and does not replace the scientific identity.
- Preserved the approved P0.3 architecture, experiment contract, dataset/split model, random streams, capability preflight, budget model, evaluation isolation, lifecycle, artifacts, acceptance demonstration, checkpoint-boundary corrections, and four implementation chunks.
- Recorded P0.3 as having an approved implementation plan only; implementation is not complete and no P0.3 production code was started.

## 2026-09-18 P0.3 checkpoint and evaluation boundary

- Added narrow checkpoint identity and write guards: published checkpoints are not writable through ordinary state APIs, read-only opens do not create directories, and readers bind to the unique current checkpoint descriptor.
- Preserved copied parent history and immutable-row triggers during checkpoint forks, with regression coverage for ancestry, checkpoint selection, read-only behavior, and developmental-state write prevention.

## 2026-09-18 P0.3 implementation and acceptance closure

- Implemented the approved P0.3 laboratory protocol: immutable versioned experiment contracts with scientific identity distinct from content digests and run IDs, fixture split/family validation, HMAC-separated scientific random streams, capability/fingerprint and budget preflight, filesystem laboratory artifacts, resumable/idempotent check records, and the FakeHost frozen evaluation boundary.
- Added the narrow P0.2 checkpoint corrections: exact checkpoint descriptor binding, rejection of ordinary writable checkpoint opens, read-only opens without directory creation, and preserved inherited fork history/triggers.
- Completed the FakeHost acceptance demonstration recorded in `docs/receipts/MNEME_P0.3_Fake_Acceptance_Receipt.md`: fork isolation, split/capability/budget rejection, paired evaluation with unchanged checkpoint state, restart inspection, and idempotent retry.
- Validation passed: 64 pytest tests, Ruff, and strict mypy. No network or paid inference was used; no P0.4 runner or Phase 1 developmental mechanism was started.
- Verified the public experiment CLI end to end, including prepared-run creation, frozen FakeHost check publication, restart/inspection verification, and hyphenated action dispatch.

## 2026-09-18 P0.3 audit remediation and acceptance reconciliation

- Reconciled the initial P0.3 closure evidence after independent audit found execution-path gaps. Fixture-pack loading and per-file/content/family provenance are now enforced through CLI preflight; checkpoint bindings are exact and spec-relative; controlled sampling requires seed control; hard budgets require integer limits; and resolved dataset orderings are persisted.
- Hardened subject-specific frozen evaluation to use the prepared FakeHost contract and resolved evaluation seed, reject the wrong checkpoint, return the exact idempotent receipt, and keep evaluation artifacts outside developmental state. Complete run verification now covers payloads, snapshots, manifests, and evaluation receipts.
- Updated the machine-readable and Markdown FakeHost receipts, work queue, and approved-plan status. Validation passes: 73 pytest tests, Ruff, and strict mypy; no P0.4 runner or Phase 1 mechanism was started.

## 2026-09-18 P0.3 final integrity hardening

- Bound published artifact verification to its run path and receipt identities, rejected duplicate payload paths, and added regression coverage proving a completed-check retry returns the requested check rather than another receipt.
- Final validation remains 73 pytest tests, Ruff, and strict mypy; P0.3 remains limited to experiment contracts and frozen evaluation isolation.

## 2026-09-18 P0.3 final validation count reconciliation

- Added the exact-check retry regression to the durable test evidence and reconciled the work queue candidate to `fb07134`; the complete suite now passes 74 tests, with Ruff and strict mypy still clean.

## 2026-09-18 P0.3 bound snapshot fail-closed remediation

- Corrected `run_isolation_check()` so a subject-bound private snapshot must exist as a regular non-symlink file and the supplied checkpoint path must resolve to that exact prepared copy before evaluation proceeds.
- Added regression coverage for missing bound snapshots, alternate valid copies with the same checkpoint identity, and successful use of the correct bound snapshot. Focused tests, full pytest, Ruff, and strict mypy pass.

## 2026-09-18 P0.3 remediation evidence reconciliation

- Updated the FakeHost receipts and P0.3 work-queue evidence for the fail-closed bound-private-snapshot fix. P0.3 remains DONE with 77 passing tests, Ruff, and strict mypy.

## 2026-09-18 P0.4 integrated no-learning runner

- Added the bounded P0.4 execution primitive over the approved P0.1-P0.3 contracts: digest-pinned fixture publication, writable subject forks, exact-once developmental acceptance, durable execution journals, uncertain-operation recovery, boundary checkpoints, private read-only evaluation, and sanitized baseline reporting.
- FakeHost integration validation passes with 95 pytest tests, Ruff, and strict mypy. The real `google/gemma-4-E4B-it` baseline is recorded separately after the bounded credential-backed run.

## 2026-09-18 P0.4 validation gate

- Recorded the P0.4 candidate and network-free validation in `.codex/work-queue.json`: FakeHost integrated execution, restart/resume evidence, pytest, Ruff, and strict mypy pass.
- P0.4 was resumed after the external credential gate resolved. The bounded real baseline completed six calls (two developmental, four evaluation) with 249 provider-reported total tokens; provider cost and prompt/completion subtotals were unavailable.

## 2026-09-19 Phase Zero closure

- Completed the P0.4 real Gemma baseline with two sibling subjects, repeated held-out probes, unchanged evaluation snapshots, exact-once restart re-entry, and sanitized human/machine receipts.
- Phase Zero is complete and tagged `mneme-phase-zero`. The laboratory remains explicitly no-learning: history is durable but behaviorally inert, and no Phase One mechanism was started.
- The persistent work queue now records P0.4 `DONE` with all required validation and the Phase Zero closure receipt.
