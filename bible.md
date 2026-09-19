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

## 2026-09-19 developmental dynamics amendment archive

- Archived the supplied `MNEME_Developmental_Dynamics_Amendment_2026-09-19.md` unchanged under `docs/research/` with SHA-256 `f5240ec906d40d5e49892b644b6a8ae653f3572bc4694003da217c8b7062d88f`.
- The document is reference material only. No implementation, scope change, or normative decision was taken from it.

## 2026-09-19 Phase One plan approval and save

- Saved the complete approved plan at `docs/Approved Plans/MNEME_Phase_One_Graph_Wrapper_Preview_Plan.md`, preserving the P1.1/P1.2/P1.3 structure, stop–audit–push gates, acceptance demonstrations, 27-call live ceiling, and Phase Two boundary.
- Incorporated the three approval corrections: confidence/salience are evidence annotations rather than persistent ranking/accessibility weights (`0.70` remains admission/uncertainty only); lineage revision, episode ordinal/count, graph revision and self-view version are explicitly distinct; new instances may opt in once with `instance create --development-enabled --host gemma-deepinfra`, with inspectable/revocable policy and no implicit legacy reuse.
- Updated the documentation index and reconciled the amendment description with the approved Phase One allocation. The original amendment and prior archive entry are unchanged; the amendment now informs the approved design allocation without authorizing implementation or bringing adaptive learning into Phase One.
- The queue has no planning-approval state, so `.codex/work-queue.json` remains unchanged with P0.1–P0.4 `DONE`. Approval is recorded in the plan and this entry; implementation packages await explicit authorization.
- Documentation validation checked all 16 plan sections, the three corrections and their consequential test/CLI wording, whitespace, index target, and unchanged amendment/Phase Zero receipts/tag. No production code or tests changed; no new test execution or paid calls are claimed for this documentation save.
- No Phase One production implementation was started. P1.1, P1.2 and P1.3 remain awaiting explicit implementation authorization.

## 2026-09-19 P1.1 residue-to-graph foundation validation

- Completed the approved P1.1 foundation package: bounded source-backed residue validation, persisted interpretation attempts with one explicit repair, fail-closed uncertain recovery, exact host binding, immutable graph snapshots, durable resolution decisions, source provenance, explicit interpretation opt-in, schema 1→2 migration, ancestry-ordered readers, staged checkpoint forks, and slot-relative extraction-cache contracts.
- Stop–audit gate passed with 138 pytest tests, Ruff, strict mypy across 31 source files, `git diff --check`, valid work-queue schema, and an offline FakeHost demonstration covering accepted episode/interpretation revisions, graph revision, restart verification, checkpoint/fork verification, and inherited history.
- P1.1 remains limited to residue-to-graph foundation. No response influence, retrieval, identity development, adaptive dynamics, P1.2, P1.3, or Phase Two work was started.

## 2026-09-19 P1.1 acceptance closure

- P1.1 passed the stop–audit–push gate in commit `4529b1e`: the full suite reports 138 passing tests, Ruff and strict mypy pass, and the offline foundation demonstration verifies restart, publication, checkpoint, fork, and inherited-history behavior.
- The work queue records P1.1 `DONE` with its validation receipt. P1.2 remains locked until a new package is explicitly dispatched; no response influence, retrieval, identity, or Phase Two implementation began in this gate.

## 2026-09-19 P1.2 implementation dispatch

- Added and claimed the approved P1.2 package on accepted base `8a0d758`, covering the shared response controller, fixed bounded retrieval/influence boundary, deliberate identity/self-view continuity, explicit correction/declaration records, and evaluation isolation.
- P1.2 is the only active Phase One package. P1.3 and Phase Two remain undispatched.

## 2026-09-19 P1.2 candidate implementation

- Implemented the approved P1.2 response and identity boundary: schema 2→3 persistence with local episode-count migration, fixed bounded route selection and typed influence traces, exact-once controller retries, deliberate and one-call host-mediated naming, child-local self-view rebinding, explicit reversible corrections/declarations, process-local chat, and opt-in runner controller integration.
- Added CLI identity/chat surfaces and corrected file-path instance creation so the documented `--store ...sqlite3` workflow creates a database file rather than a directory.
- Stop-gate candidate validation is green: 148 pytest tests, Ruff, strict mypy, `git diff --check`, focused P1.2/runner/storage tests, and a CLI create/adopt/show smoke. No P1.3 or Phase Two implementation was started.

## 2026-09-19 P1.2 acceptance closure

- P1.2 passed the stop–audit–publish gate in tested code `8e9ed7a`: the complete suite reports 148 passing tests, focused P1.2/runner/storage tests report 21 passing tests, Ruff and strict mypy pass, and the offline FakeHost demonstration verifies exact-once retries, host-mediated naming, correction reversal, fork self-view rebinding, restart, and chat recovery.
- The approved file-path instance creation workflow was smoke-tested alongside identity adoption and JSON inspection. The sanitized receipt is `docs/receipts/MNEME_P1.2_Response_Identity_Receipt.md` with its machine-readable companion.
- The work queue records P1.2 `DONE`. P1.3 remains undispatched until this accepted gate is used as its dependency; no Phase Two mechanism was started.

## 2026-09-19 P1.3 implementation dispatch

- Added and claimed the approved P1.3 package on accepted P1.2 gate `b46e8c728e2dbf80e553b14b4de99713e6610a1bf`, covering inspection, matched frozen no-memory/lexical/graph comparisons, provenance and isolation reporting, packaged fixtures, runbook and release evidence.
- P1.3 is the only active Phase One package. Adaptive dynamics, individuality claims, and Phase Two remain excluded.

## 2026-09-19 P1.3 candidate implementation

- Added read-only checkpoint inspection with separately labeled lineage, accepted-episode, graph, and self-view counters; matched fixed no-memory, lexical, and graph treatments; deterministic coordinate/request digests; state/file invariance checks; idempotent private comparison artifacts; and a comparison CLI over the existing experiment surface.
- Added the Phase One preview runbook and regression coverage for treatment coordinates, administrative-metadata isolation, frozen-state invariance, and counter inspection. The candidate currently passes 153 pytest tests, Ruff, and strict mypy; no Phase Two mechanism was added.

## 2026-09-19 P1.3 candidate audit correction

- Hardened completed comparison re-entry: a valid sanitized comparison artifact now validates checkpoint, provenance, coordinates, and matched seeds before returning without a host call. Conflicting requests fail closed. The artifact remains free of raw provider output while retaining output digests for audit.
- Offline audit now demonstrates 12 matched frozen readouts, unchanged checkpoint/file state, distinct counters, sanitized artifacts, and completed re-entry against a host that would fail if called.

## 2026-09-19 Phase One live acceptance blocker

- Tightened the existing interpretation request boundary to state the exact residue record shape, forbid markdown fences, and bound provider output to two concepts, one edge, and one route; added a regression test for that contract. Offline validation now reports 154 passing tests, Ruff, and strict mypy across 37 source files.
- The bounded DeepInfra Phase One action was attempted in three isolated runs. Eighteen provider calls were used. P1.1 published supported edges after repair, but the required route evidence was absent and the first P1.2 interpretation remained invalid after its sole repair because the provider returned unsupported concept/relationship kinds.
- The remaining nine calls cannot restart the complete 23-call gate within the approved 27-call ceiling, and the plan forbids automatic repeated sampling after a failed required result. The sanitized blocker receipt is `docs/receipts/MNEME_Phase_One_Live_Acceptance_Blocker.md` with its JSON companion. No Phase One release tag or closure was created; Phase Two remains untouched.
- The blocker receipt records the available persisted usage (186 input, 3,793 output, 3,979 total tokens across seven generation records); complete-call usage and cost were unavailable after failed process exits.

## 2026-09-19 Phase One extraction budget repair

- Bound interpretation extraction and its explicit repair request to the approved `max_new_tokens=1536` cap and added a contract regression asserting the request carries that cap. No live calls were made for this repair; the prior live blocker remains unchanged.

## 2026-09-19 Phase One comparison subject-coordinate propagation

- Corrected the comparison CLI to pass the supplied subject slot into the frozen comparison coordinate and include it in artifact provenance. Added a regression covering the forwarded coordinate, returned results, and provenance. Focused CLI/comparison tests (11) and Ruff pass.

## 2026-09-19 Phase One offline gate-driver candidate

- Added the approved `mneme demo phase-one --gate p1.1|p1.2|p1.3 --host fake --workspace PATH` surface. The driver composes existing continuity, interpretation, response, identity, checkpoint/fork, and frozen-comparison services; emits integrity-checked private gate manifests; enforces preceding-gate evidence; and supports completed-gate re-entry without rerunning host calls.
- The offline fixture demonstrates two source-backed P1.1 interpretations, host-mediated naming, fixed route use and correction suppression, checkpoint/fork self-view inheritance, and four identity-disabled P1.3 probes across three treatments (12 readouts) with checkpoint invariance. The approved live budget flag is parsed but live execution remains explicitly blocked by this offline driver; no live call is claimed.
- Focused gate-driver tests (5), Ruff, strict mypy, and `git diff --check` pass. No Phase Two mechanism was added.

## 2026-09-19 Phase One gate-driver authored control correction

- Corrected the offline residue fixture to provide explicit admission confidence on edge and route records. Extended P1.3 with an isolated forked authored-control child, a labeled authored route publication, and a checkpoint used for the four-probe matched comparison. The source P1.2 checkpoint remains preserved as a separate artifact.
- The corrected FakeHost gate sequence passes five focused gate-driver tests and produces 12 readouts with authored-control provenance, identity disabled, checkpoint invariance, and host-free completed re-entry. No live call or Phase Two mechanism was added.

## 2026-09-19 Phase One comparison re-entry audit

- Sanitized frozen-comparison artifacts now retain normalized output digests alongside output digests. Completed re-entry returns no synthesized or raw output, skips the host, and allows summary measurements to compare retained digests without treating a redaction marker as model text. Unsupported or incomplete sanitized artifacts fail closed.
- Added regressions for host-free re-entry, summary equivalence, sanitized serialization, and missing derived output evidence. Comparison-focused tests (6), Ruff, and strict mypy pass in the clean-base validation worktree; no Phase Two mechanism was added.

## 2026-09-19 Phase One terminal artifact re-entry audit

- Hardened the integrated runner so a completed run records and revalidates its terminal boundary checkpoint, exact private evaluation snapshot path, checkpoint identity/digests, and every required evaluation result before returning COMPLETE. Missing, corrupt, stale, alternate-path, or wrong-slot terminal evidence now fails closed; prepared subject-slot coverage is also enforced.
- Added focused regressions for missing/corrupt terminal checkpoints, missing/corrupt evaluation results, alternate private snapshot paths, and missing prepared subject slots. The focused runner suite reports 11 passing tests; Ruff and strict mypy pass for the changed runner/tests.

## 2026-09-19 Phase One residue admission boundary

- Tightened graph admission so concepts, relationships, and routes require source spans and confidence at or above the approved 0.70 admission/uncertainty threshold. Confidence remains evidence for validation and admission only; it is not a route-ranking weight. Empty residues remain valid.
- Publication now revalidates the residue against the accepted episode's source slots before graph writes, preventing manually constructed or deserialized residues from bypassing source provenance and admission checks. Added focused regressions for missing spans/confidence, below-threshold material, threshold acceptance, and publication bypass attempts.
- Focused residue, publication, and controller tests (37), Ruff, and strict mypy pass. The offline gate fixture still requires its worker-side residue confidence update; no Phase Two mechanism was added.

## 2026-09-19 Phase One policy and revocation boundary candidate

- Added a scoped Phase One policy authority with explicit selected-host bindings at development-enabled instance creation, inspectable permissions, append-only grant/revoke records, and read-only consultation from working stores and copied checkpoints.
- Added schema 3→4 migration that establishes the authority reference, clears legacy interpretation/recall/provider-reuse grants, and requires explicit reauthorization. Missing or corrupt authority fails closed; old checkpoint copies retain the authority reference and therefore cannot bypass later scope revocation.
- Integrated policy checks at storage acceptance, bound-host development/context dispatch, interpretation permission, identity adoption, controller recall/provider reuse, and frozen comparison memory treatments. Focused policy tests pass; broader validation remains with the assigning owner because the shared tree contains parallel gate-driver changes.

## 2026-09-19 Phase One policy authority implementation candidate

- Implemented schema v4 policy metadata and the `PolicyService` authority: selected host fingerprints are persisted at explicit development-enabled creation; `permission show`, `grant`, and `revoke` expose the narrow Phase One boundary; and migrated stores remain deny-by-default until explicit grant.
- Added focused regression coverage for selected-host binding, missing-authority fail-closed behavior, grant/revoke persistence, old-checkpoint revocation visibility, provider-reuse gating, interpretation/recall gating, and v3 migration.
- Tested policy/storage/interpretation/comparison coverage: 35 passing tests; Ruff and strict mypy pass for the owned files. Controller/service integration remains visible in the shared working tree for canonical integration with parallel gate-driver changes.

## 2026-09-19 Phase One policy authority historical-checkpoint compatibility

- Preserved read-only opening of schema-3 historical checkpoints after the schema-4 authority extension. Pre-authority copies expose storage/export state but deny interpretation, recall, and provider reuse because no current revocation authority is available.
- Validated 14 focused storage/policy tests, strict mypy for the policy/storage modules, and Ruff for those modules. No historical Phase Zero artifact was rewritten.

## 2026-09-19 Phase One controller binding and replay provenance correction

- Hardened prepared controller turns against lineage, manifest, graph, self-view, and host fingerprint drift before any provider dispatch; accepted operation coordinates remain idempotent on retry.
- Marked process-local prior chat messages as replayed provenance so prior user text remains model context without becoming fresh independent evidence. Added regressions for stale-state rejection, host drift rejection, exact-once safety, and replay source-binding provenance.
- Bound-host interpretation now consults the current provider-reuse authority before dispatch, so revocation cannot leave an old selected provider path usable.

## 2026-09-19 Phase One permission CLI compatibility

- Added the documented store migration entrypoint and compatibility forms for explicit scoped permission grants/revocations, while preserving schema-4 authority storage and fail-closed legacy behavior.

## 2026-09-19 Phase One evaluation binding correction

- Integrated evaluation now requires and checks the exact bound private snapshot path before opening a frozen view; an alternate copy or an omitted binding fails closed.
