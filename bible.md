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

## 2026-09-19 Phase One adversarial audit remediation receipt

- Recorded the offline Phase One audit remediation receipt and machine-readable evidence. P1.1/P1.2/P1.3 FakeHost gates pass with 12 frozen readouts, authored-control child snapshot, exact replay/terminal-artifact checks, source-backed admission, and current permission revocation enforcement.
- Added a dedicated `P1.LIVE` work-queue package waiting on the external DeepInfra acceptance gate. The approved live budget has 18 calls consumed across three failed attempts; no new provider call, release tag, or Phase One closure claim was made.
- Added the remediation receipt to the documentation index without changing the normative specification or Phase One scope.
- GitHub Actions CI for `f3aed96` completed successfully after the remediation documentation push.
- Updated the approved Phase One plan status to reflect accepted offline implementation and the still-waiting external live gate; no scientific plan text or Phase Two scope changed.
- Revalidated the current head at 188 passing tests and corrected the remediation receipt's stale 187-test count.

## 2026-09-19 Phase One live acceptance remediation

- Corrected the strict extraction boundary to expose every validator-owned concept and relationship vocabulary, require raw JSON only, and preserve fail-closed handling for malformed or invented values. Added regression fixtures for the six observed live-output failure forms.
- Added immutable naming-generation accounting linked to the accepted identity event, including request/result, host/provider/model provenance, finish reason, latency, and nullable usage. Added schema 5 with explicit v4-to-v5 migration while preserving read-only historical checkpoint access and private fork migration.
- Added read-only live usage accounting that counts developmental generations, each persisted extraction attempt/repair, and naming without double-counting or inventing unknown usage. Historical 18-call evidence remains unchanged; DeepInfra access is recorded as functional.
- Offline remediation validation passed: 196 pytest tests, Ruff, strict mypy, fresh isolated package install/CLI smoke, and focused naming/extraction regressions. No new provider call was made; one fresh bounded live run remains separately authorized.

## 2026-09-19 Phase One fresh live acceptance failure

- Ran one newly authorized fresh DeepInfra Phase One acceptance attempt from remediation commit `0f8bdfe539665503df0456275b521b463b80e8ab`. DeepInfra and the credential were functional; all four dispatched calls returned provider responses.
- P1.1 accepted two bounded response episodes, then the initial extraction and its sole permitted repair both failed the same strict source-span validation (`residue.core_concepts[1].source_spans[0]`). The run stopped immediately after the repair. P1.2 and P1.3 received zero calls.
- The sanitized failure receipt is `docs/receipts/MNEME_Phase_One_Live_Acceptance_Fresh_Failure_Receipt.md` with JSON companion. No acceptance criterion was weakened, no additional live call was made, no Phase One release tag was created, and Phase Two remains untouched.

## 2026-09-19 Phase One extractor quotation remediation

- Replaced the model-facing extraction requirement for numeric Unicode offsets with exact source-slot quotations. MNEME now resolves each unique verbatim quotation deterministically into canonical `source_slot`, `start`, and `end` code-point spans, rejecting missing, paraphrased, ambiguous, overlapping, or wrong-slot evidence without fuzzy matching.
- The interpretation provider boundary rejects graph-bearing numeric-only `source_spans`; direct canonical/internal residue callers retain numeric-span compatibility. The deterministic Phase One fixture now uses the same quotation contract.
- Added adversarial quotation, Unicode, ambiguity, deterministic replay, repair, and numeric-provider-output regressions while preserving malformed JSON and hidden-enum fixtures. Full offline validation reports 209 passing tests, Ruff pass, strict mypy pass, and fresh-install package/CLI smoke pass.
- Published `docs/receipts/MNEME_Phase_One_Extractor_Quote_Remediation_Receipt.{md,json}` and linked it from the approved Phase One plan, documentation index, and waiting live package. No DeepInfra call was made; P1.2, P1.3, and Phase Two remain untouched.

## 2026-09-19 Phase One extractor quotation remediation CI

- Remote `main` at `fae92e4` passed the required GitHub Actions CI run `35470638619`: pytest, Ruff, and mypy all passed. The machine-readable remediation receipt now records that CI result; no live provider call was made.

## 2026-09-19 Phase One live acceptance resumed

- The corrected quotation-contract remediation is now authorized for one bounded live acceptance run. The `P1.LIVE` package moved from `WAITING` to `RUNNING` under the existing 27-call ceiling; historical live failures remain unchanged and no gate is pre-accepted.

## 2026-09-19 Phase One corrected-contract live attempt

- The first bounded run under the quotation contract dispatched four DeepInfra calls: two accepted responses and two valid source-backed extractions. It stopped at P1.1 because both residues contained supported edges but zero route candidates; the required route criterion therefore failed. P1.2/P1.3 received zero calls.
- Preserved sanitized evidence in `docs/receipts/MNEME_Phase_One_Live_Acceptance_Quote_Run_Failure_Receipt.{md,json}`. Added the narrow offline prompt clarification that a returned supported edge must include a route candidate, reran the full offline suite (209 tests, Ruff, strict mypy), and returned `P1.LIVE` to `WAITING` for new authorization. No historical receipt was rewritten and no Phase Two work began.

## 2026-09-19 Phase One live review evidence bundle

- Published `docs/receipts/MNEME_Phase_One_Live_Acceptance_Quote_Run_Review_Evidence.md` as a sanitized addendum to the preserved corrected-contract live failure receipt. It exposes both exact developmental inputs, persisted DeepInfra responses, extractor source slots and full constrained template, valid residue JSON, resolution decisions, graph snapshots, and the zero-route decision without changing historical evidence or acceptance criteria.
- Updated the Phase One runbook and documentation index so future live gates preserve a human-reviewable input/output/provenance path rather than only hashes and pass/fail summaries. Credentials, authorization headers, unrelated private content, and secret-bearing metadata remain excluded.
- No provider calls were made and no P1.1 behavior, graph behavior, acceptance criterion, P1.2/P1.3 work, or Phase Two scope changed.

## 2026-09-19 Phase One route discovery and live fixture correction

- Corrected graph publication so bounded deterministic route discovery derives directed, source-evidenced paths of up to three edges from accepted graph edges. Explicit `route_candidates` remain optional source-backed groupings; absent route candidates no longer prevent path discovery. Direction, eligibility, cycle prevention, canonical ordering, eight-route bounds, and per-edge provenance are preserved.
- Added regressions for cross-interpretation A→B→C discovery without a model route candidate, repeated/disconnected/directionally invalid edges, explicit alias-key joining, insertion-order independence, evidence eligibility, route bounds, duplicate suppression, and persisted route provenance.
- Replaced the offline Phase One fixture with two distinct ordinary hiking/weather experiences joined by the concrete bridge concept `rain jacket`, and added `configs/p1.1-live-fixture.json` plus `docs/receipts/MNEME_P1.1_Live_Fixture_Preview.md`. The executable fixture contains inputs only; the preview is a human sanity check, not an exact extraction answer key.
- Updated the extractor prompt, Phase One runbook, demo, documentation index, and waiting live-package notes. Historical live receipts remain unchanged. Full validation passed: 217 pytest tests, Ruff, strict mypy across 40 source files, fresh package/CLI smoke, and the complete FakeHost P1.1→P1.2→P1.3 demonstration. No DeepInfra call was made; new live authorization remains required.

## 2026-09-19 Phase One bounded live driver

- Added `src/mneme/live_phase_one.py`, a thin bounded driver for the approved P1.1→P1.2→P1.3 schedule. It reuses the existing continuity, interpretation/publication, controller, identity, checkpoint, frozen-evaluation, and comparison services; reserves each call before dispatch; records sanitized private call accounting; stops on required failure; and never retries uncertain provider outcomes.
- Wired `mneme demo phase-one --gate p1.1 --host gemma-deepinfra --live-budget phase-one-v1` to the complete live schedule. The previous refusal-only branch remains fail-closed for attempts to start at P1.2 or P1.3.
- Added a full 23-call FakeHost control of the live path, including the bridged P1.1 route, naming, route application, correction, cold-start probe, checkpoint invariance, 12 matched P1.3 readouts, and host-free comparison re-entry. Validation passed: 218 pytest tests, Ruff, strict mypy across 41 source files. No DeepInfra call was made in this implementation commit; `P1.LIVE` remains waiting for live authorization.

## 2026-09-19 Phase One live authorization transition

- The active continuation authorization covers the already approved bounded `phase-one-v1` run at live-driver commit `7f69a49f230987c01a3d1c3e5e630469ec5a0eab`. The prior 18-call attempts and later four-call route/fixture failure remain historical evidence and are not reclassified.
- Updated only the persistent queue state for `P1.LIVE`: the rerun dependency is resolved for this authorized execution and the package is `RUNNING`. No provider call has been dispatched yet.

## 2026-09-19 Phase One bridged live run stop

- The bounded bridged-fixture run tested commit `44e9d75ddd16eebe757f0c7975a07636c0f9b318` and dispatched eight DeepInfra calls. P1.1 passed: both natural developmental examples produced valid source-supported edges and deterministic publication derived a two-edge route with provenance from both interpretations.
- P1.2 naming durably adopted `Gemma4`, and the relevant response was accepted with a traced route payload. Its extraction returned an edge whose evidence paraphrased the immutable source; the one permitted repair returned another paraphrase. Strict quotation validation rejected both, so P1.2 failed and P1.3 received zero calls. DeepInfra and the credential were functional; no transport retry or replacement sampling occurred.
- Preserved sanitized evidence in `docs/receipts/MNEME_Phase_One_Live_Bridged_Run_Failure_Receipt.{md,json}` and returned `P1.LIVE` to `WAITING` on a new explicit live authorization. Private `live_summary.json` and SQLite artifacts remain outside Git. No release tag or Phase Two work began.

## 2026-09-19 Phase One extraction prompt clarification

- Added a narrow fail-closed instruction to the extraction prompt: before returning a concept or relationship, Gemma must verify each evidence quotation is a contiguous substring of its referenced source; unsupported paraphrases are omitted rather than rewritten into evidence. The validator and acceptance criteria are unchanged, and model-output sources remain explicitly covered.
- Added prompt regression assertions and reran the offline validation before any further provider call. The prior bridged-run artifacts remain unchanged and P1.LIVE stays waiting for fresh authorization.

## 2026-09-19 Phase One corrected-contract run authorization

- The active continuation authorizes one new bounded `phase-one-v1` study from corrected commit `534183a5b0a5dabf8c8f64a18ab25844d0625a60`. It is a new run because the prior P1.2 interpretation exhausted its initial-plus-one-repair ledger; no prior response, result, receipt, or store will be rewritten or retried in place.
- The queue transition records `P1.LIVE = RUNNING` for this one run. Dispatch remains capped at 27 calls, with no transport retries and immediate stop on another required failure.

## 2026-09-19 P1.1 corrected live stop and extraction-source boundary

- Preserved the corrected-contract P1.1 live run from tested code `2cdf3ac` as a failed historical receipt: four DeepInfra calls returned, both extractions were structurally/source valid, but only one supported edge was accepted and no multi-hop route formed. P1.2/P1.3 were not attempted; provider and credential were functional.
- Added a narrow source-purpose boundary for the live P1.1 fixture: extraction receives immutable external episode evidence only, while model output remains durably recorded and auditable without becoming independent developmental evidence for the fixture graph. Existing offline callers retain the prior eligible-source behavior.
- Added regression coverage for source-purpose filtering and recorded the private artifact digests in `docs/receipts/MNEME_Phase_One_Live_Corrected_P1.1_Failure_Receipt.{md,json}`. The live package is WAITING; no further provider call is authorized automatically.

## 2026-09-19 Phase One live continuation authorization

- The active Phase One continuation authorizes one fresh isolated `phase-one-v1` run from `08f8cd6`, after the offline source-purpose correction and full validation. The remaining ceiling from the latest 27-call authorization is 23 calls; prior live attempts remain immutable historical evidence.
- `P1.LIVE` is RUNNING for this bounded execution. No transport retries, favorable-output resampling, or automatic progression after a failed required criterion is permitted.

## 2026-09-19 Phase One continuation P1.1 live stop

- The fresh isolated continuation from `09bbf42` dispatched four DeepInfra calls and stopped at P1.1. Both extraction results passed strict validation; the first published `weather_check -> rain_jacket`, while the second published concepts without an edge, so deterministic route discovery correctly found no multi-hop path.
- Preserved the sanitized receipt and private artifact digests in `docs/receipts/MNEME_Phase_One_Live_Continuation_P1.1_Failure_Receipt.{md,json}`. DeepInfra and the credential were functional; P1.2/P1.3 received zero calls. `P1.LIVE` returned to WAITING without automatic retry or favorable-output resampling.

## 2026-09-19 Phase One publication edge-key collision remediation

- Audited the continuation P1.1 failure and found that Gemma returned a valid second relationship using the same interpretation-local key `e1`; publication copied the previous snapshot and silently skipped the colliding row. The missing route was therefore an infrastructure defect, not missing provider capability.
- Added deterministic collision-safe graph edge and explicit-route keys derived from relationship/evidence content, remapped route references, preserved local-key provenance, and added a regression proving reused local keys still produce a two-edge route with both evidence records.
- Full offline validation passed: 221 pytest tests, Ruff, strict mypy, and fresh package/CLI smoke. No provider call was made for this remediation. The P1.LIVE package remains WAITING pending a fresh bounded run.

## 2026-09-20 Phase One collision-fixed live authorization

- Remote CI `35476530136` passed for `950f596`, including the collision-safe publication fix and the reused-local-key regression. The active goal authorizes one fresh bounded Phase One run from this commit with a 27-call ceiling; the prior eight live calls remain historical and are not reclassified.
- `P1.LIVE` is RUNNING for the corrected run. Stop-on-failure, no transport retries, and no favorable-output resampling remain in force.

## 2026-09-20 Phase One collision-fixed live stop

- The fresh run from `8465d4e` passed P1.1: collision-safe publication retained both reused-local-key edges and deterministic route discovery produced `weather_check -> rain_jacket -> shower` with provenance from both interpretations.
- P1.2 naming and response influence evidence were returned, but its initial extraction and one permitted repair failed strict quotation validation on model-output evidence. P1.3 received zero calls. The sanitized receipt is `docs/receipts/MNEME_Phase_One_Live_Collision_Fixed_P1.2_Failure_Receipt.{md,json}`.
- Added the narrow live-run source boundary to P1.2 developmental interpretation calls: host output remains recorded testimony, while extraction receives only immutable external evidence. Offline focused validation passed; no new provider call was made for this correction.

## 2026-09-20 Phase One live evidence-filter authorization

- Remote CI `35476828096` passed for `540ad06` after the P1.2 external-evidence-only extraction correction. The active goal authorizes one fresh bounded `phase-one-v1` run from this commit, capped at 27 calls with no retries or favorable-output resampling.
- `P1.LIVE` is RUNNING. All earlier P1.1/P1.2 failures remain immutable historical evidence.

## 2026-09-20 Phase One evidence-filtered live stop and probe receipt fix

- The fresh run from `7732449` passed P1.1 again and consumed ten returned calls. P1.2 naming, route influence, correction suppression, and valid external-only interpretations completed; the frozen cold-start probe did not contain the adopted `Gemma4` name, so P1.2 stopped before unrelated abstention and P1.3.
- Preserved `docs/receipts/MNEME_Phase_One_Live_Evidence_Filter_P1.2_Failure_Receipt.{md,json}`. The original run retained only the probe hash, exposing an evidence-publication defect; the live driver now persists partial P1.2 progress and the sanitized probe output before applying the name assertion. No provider call was made for this instrumentation correction.

## 2026-09-20 Phase One probe-evidence live authorization

- Full offline validation and CI passed for `d9ac1c6`, which persists partial P1.2 progress and cold-start probe output before assertions. One fresh bounded run is authorized from this commit to obtain reviewable evidence for the previously unpersisted cold-start criterion; the 27-call ceiling, stop-on-failure rule, and no-resampling rule remain in force.
- `P1.LIVE` is RUNNING. Earlier live runs and receipts remain unchanged.

## 2026-09-20 Phase One cold-start name comparison remediation

- The probe-evidence run from `8be338e` passed P1.1 and preserved the actual cold-start output `Gemma 4`. P1.2 stopped because the runner compared it byte-for-byte with the adopted spelling `Gemma4`; this was a deterministic formatting mismatch, not provider failure or absent identity recovery.
- Added `_name_matches` normalization for case-insensitive token adjacency across display spacing/punctuation, with regression rejection for distinct names. Preserved the run in `docs/receipts/MNEME_Phase_One_Live_Probe_Evidence_Failure_Receipt.{md,json}`. No provider call was made for the correction.

## 2026-09-20 Phase One normalized-name live authorization

- Full validation and CI passed for `56bee14`, including the recovered-name spacing regression. One fresh bounded `phase-one-v1` run is authorized from this commit with the 27-call ceiling and stop-on-failure/no-resampling rules.
- `P1.LIVE` is RUNNING; all prior provider results remain immutable.

## 2026-09-20 Phase One live acceptance closure

- The isolated bounded run from `68bebde87f22ffed06e3d07676274546a2477a45` returned 23 of 27 authorized DeepInfra calls with no retries or uncertain calls. P1.1, P1.2, and P1.3 all passed their approved live criteria: the natural two-experience route was derived from accepted edges with provenance from both experiences; identity adoption, cold-start recovery, correction suppression, and unrelated abstention were traced; and the frozen 12-readout comparison preserved the developmental checkpoint and state digest.
- Final audit verified exact-once developmental records, restart/reopen recovery, durable naming accounting, host provenance (`google/gemma-4-E4B-it`, hosted revision unknown), and separation of evaluation artifacts from developmental state. Usage was 6,829 tokens across 23 calls; provider cost was not supplied and remains unknown. The final sanitized receipt is `docs/receipts/MNEME_Phase_One_Live_Acceptance_Final_Receipt.md` with its JSON companion.
- Offline validation passed: 222 pytest tests, Ruff, strict mypy across 41 source files, and fresh-install CLI smoke. `P1.LIVE` is DONE; historical failed attempts remain unchanged and are not reclassified. Phase One is complete as the graph-wrapper preview, with no Phase Two work started. The approved `mneme-phase-one-graph-preview` release tag is created only after this closure commit is pushed and independently verified.

## 2026-09-20 Phase Two plan approval

- Approved the integrated `MNEME Phase Two — Self-Conditioned Developmental Runtime` plan at baseline `9c5619c8addd2172ddb64a51273183eba8d31ece`, incorporating Proposed Plan Amendment 01 and its targeted corrections. The plan preserves P2.1 → P2.2 → P2.3 stop–audit–publish gates, per-lineage SQLite/checkpoint architecture, pure replayable learning, source/dependence provenance, reviewed identity, and isolated evaluation.
- The approved learner plan makes contextual restraint affect actual serialized exposure, closes learned restraint at `E=-0.25` without deleting association support, distinguishes observed support from credited support and retention, maps current-input echoes to zero additional credit, restricts exploration to the highest query-coverage tier, and retains deterministic recovery through permitted evidence. The pilot fixture/split, production-equivalent three-call assessor qualification, and proposed live ceiling of 299 calls / 204,288 maximum output tokens are recorded in `docs/Approved Plans/MNEME_Phase_Two_Self_Conditioned_Developmental_Runtime_Plan.md`.
- This records plan approval only. No P2.1, P2.2, or P2.3 implementation, provider call, credential access, work-queue package, Phase Three work, or release tag was started. Phase Zero and Phase One tags and historical evidence remain unchanged.
- Repaired the Phase One queue record's `P1.LIVE.validation.results` shape from an obsolete array to the required schema-v1 object, preserving the same receipts and PASS evidence. This is queue bookkeeping only and does not alter Phase One artifacts or claims.

## 2026-09-20 Phase Two implementation campaign opened

- Added approved packages `P2.1`, `P2.2`, and `P2.3` to the persistent queue. `P2.1` is RUNNING under `/root/p21_supervisor`; `P2.2` waits on `package:P2.1`; `P2.3` waits on `package:P2.2`. The queue schema validates after repairing the historical `P1.LIVE` validation-results shape.
- Phase Two execution is authorized by the active goal, but no provider call or credential access is authorized yet. P2.1 is offline/FakeHost work; the proposed 299-call qualification/pilot ceiling remains unspent and requires the plan's qualification gate and live execution boundary.

## 2026-09-20 P2.1 learner foundation candidate

- Added the first bounded P2.1 vertical slice: a pure fixed-point replayable learner with explicit observation/dependence categories, bounded source pools/caps, support-versus-presence handling, contextual consequence state, learned exposure eligibility, and highest-coverage-only exploration. Added deterministic FakeHost-free tests for model-origin credit, current-input echo zero credit, unknown/presence handling, contextual closure/recovery, and mixed-coverage exploration.
- Added schema-6 storage scaffolding and explicit `learn` opt-in state for development operations, semantic bindings, observations, learner updates/values/snapshots, and assessor attempts. Schema migration remains explicit, backed up, and legacy learning-disabled. Focused validation passed: 19 storage/policy/learner tests, Ruff, and strict mypy. No provider call or credential access occurred; P2.1 remains in progress.

## 2026-09-20 P2.1 schema migration and learning-policy correction

- Completed the schema-5 to schema-6 migration path for learner manifest fields and retained explicit backup/fail-closed behavior. Development lifecycle records remain mutable while accepted learner records remain immutable. Learning permission is now accepted by the local authority ledger, explicitly grantable/revocable, and denied when that authority is unavailable. Focused schema, storage, policy, and migration validation passed; no provider calls or credentials were used. P2.1 remains in progress.

## 2026-09-20 P2.1 learner transition contract refinement

- Refined the pure learner into an immutable, fixed-point transition kernel with explicit global opportunities, dependence-group and rolling caps, observation/retention distinctions, attributable contextual consequences, idempotent operation coordinates, highest-coverage exploration, and weak/established/saturated restraint with recovery. The initial mapping API remains as a compatibility adapter while the production-facing `LearnerState`/`TransitionInput` contract carries the full Phase Two semantics. Focused learner, policy, and schema tests pass; no provider calls or credentials were used.

## 2026-09-20 P2.1 controller and atomic publication candidate

- Added the first production-boundary P2.1 slice: deterministic directed route discovery from accepted graph edges, fixed-v2 versus explicitly permitted learned-v1 selection, preserved system instructions, actual supplied-payload tracing, and highest-coverage exploration. Extended interpretation publication with optional atomic learner observations, stable semantic bindings, learner snapshots/values, manifest metadata, explicit learning-permission enforcement, unknown/no-credit recording, and idempotent retry behavior. Focused controller/publication/memory tests, Ruff, and strict mypy passed; no provider calls or credentials were used. P2.1 remains in progress pending full integration and adversarial validation.

## 2026-09-20 P2.1 stop-audit completion

- P2.1 passed its offline stop–audit gate and is DONE in the work queue. The candidate was validated with 236 pytest tests, Ruff, strict mypy, wheel build, and fresh-install CLI smoke. The audit retained evidence for fixed-point learner transitions, restraint/recovery, dependence caps, directed route discovery, actual payload tracing, schema-6 migration, atomic learner publication, unknown/no-credit behavior, explicit learning permission, and idempotent replay. No provider calls or credentials were used. P2.2 is now READY; P2.3 remains dependent on P2.2.

## 2026-09-20 P2.2 retention and authority candidate

- Extended the P2.2 offline slice with measured absence and modeled-advance retention counters, unsupported-streak evidence, bounded contextual consequence caps and recovery, schema 7 outcome/quarantine/identity-review records, reversible append-only quarantine authority, durable failed identity-review attempts, explicit quarantine CLI operations, and migration coverage. Focused and full offline validation passed (248 pytest, Ruff, strict mypy); no provider calls or credentials were used. P2.2 remains in progress pending fork/revocation integration and adversarial stop-audit.

## 2026-09-20 P2.2 fork and revocation boundary

- Completed the offline P2.2 boundary for fork inheritance and authority isolation: private child forks receive an independent learner snapshot/value projection and active quarantine decisions, while parent and child stores retain independent administrative identities and writable tips. Added a fork regression and kept historical parent records intact. The CLI now supports explicit learning opt-in and quarantine add/release operations. Full validation passed at 249 pytest tests, Ruff, and strict mypy; no provider calls or credentials were used. P2.2 remains in progress pending final stop-audit receipts.

## 2026-09-20 P2.3 offline assessor and pilot boundary

- Added the production-shaped Phase Two assessor contract and fixed Q1/Q2/Q3 qualification fixtures with strict source coverage, quotation, Unicode span, dependence, current-input echo, and replay/exposure ancestry validation. Added the durable pilot reservation/lifecycle ledger with hard call/output-token ceilings, idempotent coordinates, pause/resume, uncertain-call retention, and sanitized artifact publication.
- Completed the directly necessary P2.2 durability correction: contextual route consequence state and accepted outcome assessments now survive publication/reconstruction, and reviewed identity acceptance creates an atomic identity event/self-view transition. Full offline validation passed at 264 pytest tests, Ruff, and strict mypy across 46 source files. No provider call or credential access occurred; P2.3 live qualification and the proposed 299-call ceiling remain unrun.
- Recorded P2.3 as a VALIDATING candidate in the work queue with assessor-contract, pilot-ledger, offline-validation, and boundary-audit receipts. The package remains open at the live qualification boundary; no qualification or pilot call is implied by this queue state.
- Corrected the live assessor request boundary to use prompted raw JSON rather than DeepInfra's unsupported native response-format field, and added the fixed three-call qualification executor with durable result-before-validation receipts and no retry path. Offline validation now passes at 266 pytest tests, Ruff, and strict mypy across 47 source files; no provider call or credential access occurred.
- Reconciled the P2.3 candidate receipt to `954173c`, including the raw-JSON qualification correction and the 266-test offline validation result. P2.3 remains at the fixed qualification boundary and has not consumed the proposed pilot budget.

## 2026-09-20 P2.3 qualification stop

- Executed exactly the fixed three-call DeepInfra assessor qualification under `p2-developmental-pilot / contract_revision 1`. All three provider calls returned and were durably retained with usage (1,450 input, 279 output, 1,729 total tokens), proving provider/credential functionality. Gemma returned newline-delimited single-object text with unsupported enum values instead of the required raw JSON object containing an `assessments` array; all three cases failed structural validation. No retries, repairs, replacement calls, or pilot calls were made. P2.3 is stopped at qualification failure; the proposed 299-call pilot ceiling remains untouched.
- Reconciled the P2.3 queue notes and evidence references to the qualification failure receipt. The package remains WAITING on a reviewed correction/live authorization; Phase Two is not declared complete.

## 2026-09-20 P2.3 assessor contract candidate

- Added the production-shaped Phase Two semantic-assessor request/result contract and fail-closed validator. Qualification and pilot requests share source roles, immutable source slots, monitors, coverage declarations, memory exposure, replay ancestry, context, and prompt version; every monitor row is required, quotations are unique verbatim source evidence with deterministic code-point spans, absent requires complete available-source coverage, unknown records incomplete coverage, and recorded ancestry rejects claimed independence. Added fixed Q1/Q2/Q3 qualification fixtures and FakeHost-backed offline regression coverage. No provider calls or credentials were used; full integration and live qualification remain the parent P2.3 workstream's responsibility.

## 2026-09-20 P2.3 pilot lifecycle candidate

- Added the offline Phase Two pilot lifecycle ledger beside prepared experiment artifacts. It durably records PREPARED/QUALIFYING/QUALIFIED/RUNNING/PAUSED/COMPLETE/FAILED/UNCERTAIN state, bounded pre-dispatch reservations, DISPATCHED/RETURNED/FAILED/UNCERTAIN call outcomes, idempotent coordinates, output-token ceilings, qualification gating, sanitized report artifacts, and restart-safe integrity receipts. No provider calls or credentials were used; the live qualification and pilot remain outside this candidate.

## 2026-09-20 P2.3 assessor prompt remediation

- Corrected the production assessor prompt contract after the first qualification failure. Prompt version `p2-assessor-production-v2` now enumerates every validator-constrained enum and the complete top-level/row JSON structure, coverage rules, exact quotation requirements, and raw-JSON-only boundary. Validator strictness and qualification criteria were unchanged. Offline validation passed at 267 pytest tests, Ruff, and strict mypy across 47 source files; no provider call occurred during remediation. A fresh fixed three-call qualification attempt is the next gate; the prior three results remain unchanged and the 299-call pilot remains untouched.

## 2026-09-20 P2.3 remediation candidate reconciliation

- Reconciled the P2.3 offline candidate to remediation commit `bd573a6`, which contains the explicit assessor prompt v2 contract, its regression test, the sanitized remediation receipt, and the 267-test offline validation evidence. The package remains at the fresh qualification boundary; no additional provider call occurred in this bookkeeping update.

## 2026-09-20 P2.3 semantic qualification stop

- Executed the one fresh fixed three-call assessor qualification authorized after prompt remediation, from commit `888cb40`. DeepInfra returned and the ledger durably retained all three calls (2,533 input, 709 output, 3,242 total tokens); the credential and transport were functional, and no retries or pilot calls occurred. Raw JSON structure passed, but Q1 made an incomplete absence claim and marked an unrelated monitor present, Q2 marked the external rain-jacket relation present and failed the recorded replay/exposure dependence rule, and Q3 marked unavailable output absent instead of unknown. P2.3 remains WAITING on the assessor qualification dependency; the proposed 299-call pilot remains untouched. Sanitized receipts are `docs/receipts/MNEME_P2.3_Assessor_Qualification_V2_Failure_Receipt.md` and `.json`.

## 2026-09-20 P2.3 assessor ancestry-scope remediation

- Offline audit of the failed qualification found and corrected a validator defect: request-level replay/exposure ancestry was incorrectly applied to every monitor instead of only monitors referencing the ancestral source slots. The production prompt now defines the distinction among replay-linked, exposure-linked, current-input-echo, and independent evidence. Strict qualification assertions were preserved; the historical Q1/Q2/Q3 failures remain unchanged. Validation passed at 268 pytest tests, Ruff, and strict mypy across 47 source files with no provider call. A new qualification authorization is required; the 299-call pilot remains untouched.

## 2026-09-20 P2.3 ancestry remediation candidate reconciliation

- Reconciled the P2.3 offline candidate to `5eb95b9`, including the scoped-ancestry validator correction, production prompt clarification, 268-test validation, package smoke, and sanitized remediation receipt. P2.3 remains WAITING on a new assessor qualification authorization; no provider call occurred in this bookkeeping update.

## 2026-09-20 P2.3 validation timestamp reconciliation

- Updated the P2.3 queue validation timestamp to the completed 268-test ancestry-remediation gate. No implementation or provider state changed; P2.3 remains WAITING on external assessor qualification.

## 2026-09-20 P2.3 qualification v3 stop

- Executed the explicitly authorized fresh fixed Q1/Q2/Q3 qualification against clean main `905622f`. All three DeepInfra calls returned and were durably retained (2,866 input, 706 output, 3,572 total tokens); no retries, repairs, replacement samples, or pilot calls occurred. Q1 falsely marked the unrelated monitor present, Q2 falsely supported the rain-jacket candidate and used `replay_linked` instead of required `exposure_linked`, and Q3 marked a negated relation supported and unavailable output absent instead of unknown. Qualification failed and the pilot remained at zero calls. The sanitized receipts are `docs/receipts/MNEME_P2.3_Assessor_Qualification_V3_Failure_Receipt.md` and `.json`; repeated semantic failure is preserved for architectural review.

## 2026-09-20 P2.3 qualification v3 queue reconciliation

- Updated the P2.3 queue timestamp to the v3 qualification stop and preserved the package as `WAITING` on external assessor qualification. No additional provider call or pilot dispatch occurred.

## 2026-09-20 P2.3 qualification v4 stop

- Executed the newly authorized fresh fixed Q1/Q2/Q3 qualification against clean main `3386d945`. All three DeepInfra calls returned and were durably retained (2,866 input, 706 output, 3,572 total tokens); no retries, repairs, replacement samples, or pilot calls occurred. Q1 falsely marked the unrelated monitor present, Q2 falsely supported the rain-jacket candidate, and Q3 marked a negated relation supported and unavailable output absent instead of unknown. Qualification failed and the pilot remained at zero calls. The sanitized receipts are `docs/receipts/MNEME_P2.3_Assessor_Qualification_V4_Failure_Receipt.md` and `.json`; P2.3 remains stopped for architectural review of assessor suitability.

## 2026-09-20 Future developmental self-context architecture filed

- Filed `docs/architecture/future/MNEME_Developmental_Self_Context_Architecture.md` as future developer design context under its section 14 documentation-only instructions. Added discoverability and a non-blocking cross-reference in `docs/README.md`; no approved plan, frozen contract, runtime prompt, learner, test, budget, queue state, or inference operation changed.

## 2026-09-20 P2 assessor role-separation amendment

- Applied the additive `P2-ASSESSOR-SEPARATION-01` instruction. The developing Gemma binding remains unchanged; a separately fingerprinted DeepInfra Qwen assessor binding is now available through the existing Host boundary, with role-bound qualification accounting and fail-closed mixed-role reservations. Historical qualification receipts, learner semantics, frozen fixtures, budgets, and the P2.3 blocker remain unchanged. No provider call occurred in this offline correction.

## 2026-09-20 P2 assessor role-separation offline gate

- Pushed correction `7de05a25077ae09c1579e7b4a2632985df1c6d74`. The offline gate passed at 275 pytest tests, Ruff, strict mypy across 47 source files, wheel/install CLI smoke, and CI run `35529994781`. The designated Qwen assessor binding is ready for the one authorized qualification attempt; Gemma remains the developing host and no provider call occurred during remediation.

## 2026-09-20 P2 separated-assessor qualification stop

- Executed the one authorized Qwen assessor qualification from configuration commit `a3a8ee6`. Qwen returned Q1 successfully (848 input, 371 output, 1,219 total tokens), but its structurally valid result classified the externally supplied latch evidence as `replay_linked` instead of the frozen required `external_supported`. The run stopped immediately after Q1; Q2/Q3 and the pilot were not dispatched. The credential and provider were functional. The sanitized receipts are `docs/receipts/MNEME_P2.3_Assessor_Qualification_Qwen_V1_Failure_Receipt.md` and `.json`; P2.3 remains blocked on semantic assessor suitability.

## 2026-09-20 P2 assessor/provenance resolution correction

- Applied the additive `P2-ASSESSOR-PROVENANCE-RESOLUTION-01` correction without changing the approved Phase Two plan, Gemma developing host, separated assessor role, learner semantics, budgets, or historical evidence. The assessor contract is now `p2-assessor-v2` / `p2-assessor-production-v3` and returns semantic observations plus source correspondence only; deterministic `p2-provenance-v1` resolution derives developmental dependence from authoritative source roles, memory exposure, replay ancestry, and immutable bindings. Raw assessor output, semantic observations, and derived provenance are persisted separately, with all applicable ancestry roots retained and minimum remaining multi-root caps applied by the learner.
- Offline validation passed at 280 pytest tests, focused provenance/qualification/learner regressions, Ruff, strict mypy across 47 source files, and wheel/install smoke. No provider call or pilot call occurred. The historical Qwen Q1 failure remains unchanged, and P2.3 remains WAITING on a fresh explicit qualification authorization. Evidence: `docs/receipts/MNEME_P2_Assessor_Provenance_Resolution_Offline_Receipt.md` and `.json`.

## 2026-09-20 P2 assessor/provenance queue reconciliation

- Reconciled the P2.3 candidate to `e993d68` and CI run `35534420124` (passed). The queue records the new semantic/provenance contract versions and offline receipt while retaining `WAITING` on `external:p2-assessor-qualification`. No provider call, pilot dispatch, or acceptance-criterion change occurred.

## 2026-09-20 P2.3 corrected qualification Q1 stop

- Executed the authorized corrected Q1/Q2/Q3 qualification from clean main `0abd74e`. Q1 returned from the designated DeepInfra Qwen assessor and was durably persisted before validation (781 input, 331 output, 1,112 total tokens). The latch semantic was correct, but Qwen marked the available model-output echo absent and incorrectly marked the unrelated monitor present. Qualification stopped after Q1; Q2/Q3 and the pilot were not dispatched, and no retry or repair was made. The sanitized evidence is `docs/receipts/MNEME_P2.3_Assessor_Qualification_Provenance_V2_Failure_Receipt.md` and `.json`. Historical failures remain unchanged; P2.3 stays WAITING for review.

## 2026-09-20 P2.3 corrected qualification queue reconciliation

- Reconciled P2.3 to evidence commit `266fed2`, preserving `WAITING` on `external:p2-assessor-qualification`. The queue now points to the one-call Q1 semantic stop; Q2/Q3 and pilot calls remain undispatched. No acceptance criteria, model, contract, or historical receipt was changed.

## 2026-09-20 P2.3 assessor prompt semantics remediation

- Audited the corrected Q1 failure and found two prompt omissions: source `available=true` was not explicitly distinguished from current-input membership, and partial monitor relations did not state candidate-field inheritance. Added only those model-facing clarifications and bumped the prospective prompt version to `p2-assessor-production-v4`; schema, Q1/Q2/Q3 cases, expected outcomes, resolver, learner, and acceptance criteria remain unchanged. Offline validation passed at 280 pytest tests, Ruff, strict mypy, wheel build, and fresh-install CLI smoke with no provider call. The historical Q1 failure remains preserved; one fixed qualification under the new prompt is the next bounded verification.

## 2026-09-20 P2.3 prompt remediation queue reconciliation

- Reconciled P2.3 to correction commit `d28c9e5`. The queue records the prompt-semantics offline gate as PASS while retaining the historical Q1 qualification failure and `WAITING` on `external:p2-assessor-qualification`. No provider call or pilot dispatch occurred during remediation; the proposed 299-call ceiling is unchanged.

## 2026-09-20 P2.3 prompt v4 qualification stop

- Executed one fixed Q1/Q2/Q3 qualification from the prompt-v4 remediation boundary. Q1 returned and was durably retained (877 input, 343 output, 1,220 total tokens). Qwen correctly rejected the unrelated monitor and supported the latch, but still marked the available model-output echo absent. Q2/Q3 and the pilot were not dispatched; no retry, repair, or resampling occurred. The sanitized receipts are `docs/receipts/MNEME_P2.3_Assessor_Qualification_PromptV4_Failure_Receipt.md` and `.json`. This repeated semantic assessor failure is preserved as the P2.3 blocker.

## 2026-09-20 P2.3 prompt v4 queue reconciliation

- Reconciled P2.3 to evidence commit `71b6323`, retaining `WAITING` on `external:p2-assessor-qualification`. The queue records the prompt-v4 Q1 semantic stop and preserves the historical v2 failure and offline remediation; Q2/Q3 and pilot calls remain zero.

## 2026-09-20 P2.3 complete monitor proposition correction

- Applied the additive request-contract correction after the prompt-v4 Q1 stop. Assessor schema `p2-assessor-v3` and prompt `p2-assessor-production-v5` now require complete self-contained `{from, to, relation}` propositions for candidates and every monitor; partial mappings are rejected and normalized copies prevent post-construction mutation from producing partial provider payloads. Q1/Q2/Q3 semantics, source texts, expected outcomes, provenance resolver, learner, and acceptance criteria remain unchanged. Offline validation passed at 283 pytest tests, Ruff, strict mypy, wheel build, and fresh-install CLI smoke with no provider call. Historical evidence remains unchanged; one fixed live qualification under the new contract is authorized by the standing bounded-verification rule.

## 2026-09-20 P2.3 complete monitor proposition queue reconciliation

- Reconciled P2.3 to correction commit `037736e`. The queue records the schema-v3/prompt-v5 offline gate as PASS while preserving all historical qualification failures and `WAITING` on `external:p2-assessor-qualification`. No provider call or pilot dispatch occurred during correction.

## 2026-09-20 P2.3 assessor source-role contract remediation

- Applied the additive request-contract correction after the v5 Q2 stop. Assessor schema `p2-assessor-v4` and prompt `p2-assessor-production-v6` now serialize explicit `required_source_slots`, `evidence_source_slots`, and `correspondence_source_slots`; Q1 echo and Q2 shade identify model-output occurrence evidence separately from external/memory antecedents. The deterministic provenance resolver, semantic cases, learner, acceptance criteria, and historical evidence remain unchanged. Offline validation passed at 284 pytest tests, Ruff, strict mypy, wheel/install smoke, and zero provider calls. Evidence: `docs/receipts/MNEME_P2.3_Assessor_Source_Role_Contract_Remediation_Receipt.md` and `.json`.

## 2026-09-20 P2.3 assessor source-role queue reconciliation

- Reconciled P2.3 to correction commit `831d726` and CI run `35539129367` (passed). The queue records schema v4/prompt v6 source-role binding and its offline receipt while retaining `WAITING` on `external:p2-assessor-qualification`; the proposed 299-call ceiling and all historical failures remain unchanged. No provider call occurred during the correction.

## 2026-09-20 P2.3 source-role v6 qualification stop

- Executed the one fixed Q1/Q2/Q3 qualification from clean main `46593a6`. All three DeepInfra Qwen calls returned and were durably retained (3,190 input, 804 output, 3,994 total tokens; provider cost unavailable). Q1 and Q2 passed, including deterministic `external_supported`, `current_input_echo`, and `exposure_linked` resolution. Q3 returned `absent` for an unavailable model-output source where the contract requires `unknown`; strict validation rejected it and the run stopped. No retry, repair, resampling, model substitution, or pilot call occurred. The sanitized receipts are `docs/receipts/MNEME_P2.3_Assessor_Qualification_Source_Role_V6_Failure_Receipt.md` and `.json`; P2.3 remains stopped for assessor suitability review.

## 2026-09-20 P2.3 source-role v6 queue reconciliation

- Reconciled the P2.3 queue to the v6 qualification failure receipt and removed the stale duplicate qualification result entry so the queue now exposes the current Q1/Q2-pass, Q3-fail evidence. Package remains `WAITING` on `external:p2-assessor-qualification`; no pilot call was made.

## 2026-09-20 P2.3 v6 evidence candidate pointer

- Pointed the P2.3 candidate at the published v6 failure-evidence commit `2ebab41`; the queue remains `WAITING` on `external:p2-assessor-qualification` and records the final queue reconciliation at `c253314`. No new provider or pilot call occurred.

## 2026-09-20 P2.3 v6 qualification audit correction

- Audited the persisted v6 Q3 result and found the failure receipt had incorrectly described the negated dial row as correct. The raw model output marked `dial → stops → ticking` supported despite an explicit negation, and marked unavailable output absent instead of unknown. Added an append-only audit correction without rewriting the original receipt, changing criteria, or making a provider call. Evidence: `docs/receipts/MNEME_P2.3_Assessor_Qualification_Source_Role_V6_Audit_Correction.md` and `.json`.

## 2026-09-20 P2.1 learner-accounting correction

- Corrected the Phase Two learner publication boundary so induced observations receive credit only when the corresponding memory/replay material was actually exposed, stable semantic edge bindings are used as learner keys across extractor-local key reuse, and production `learned-v1` selection reconstructs persisted contextual route consequences before applying restraint. Consequence exposure caps now share one absolute per-origin across positive and negative assessments. Added FakeHost regressions for zero-credit omitted exposure, stable binding reuse, persisted route closure, and signed cap accounting. Offline validation passed; no provider call occurred. Gate artifacts and queue disposition remain pending the serialized stop–audit–publish reconciliation.

## 2026-09-20 P2.2 authority and replay correction

- Added deterministic learner replay verification and quarantine-aware rebuilds that resolve observations through canonical semantic bindings, preserve global opportunity state, and append rebuilt materializations without rewriting accepted history. Quarantine/release now rebuild the learner tip; feedback proposals require an accepted operation and route, persist as immutable outcome records, and accept through an append-only superseding assessment. Added learner/identity/feedback inspection surfaces and FakeHost regressions for replay equality, quarantine restoration, signed feedback, and failed identity-result durability. Offline validation passed; no provider call occurred. P2.3 qualification remains the external stop gate.

## 2026-09-20 P2.3 self-contained-monitor v7 qualification stop

- Verified the already-pushed self-contained monitor correction (`037736e`) offline on current main: 290 pytest tests, Ruff, strict mypy, wheel/fresh-install smoke, and explicit complete-proposition/fail-closed serialization checks passed. Executed exactly one fixed Q1/Q2/Q3 DeepInfra Qwen campaign under `p2-assessor-v4` / `p2-assessor-production-v6`; all three results were durably retained before validation. Q1 and Q2 passed, while Q3 failed the frozen negation semantic case because the assessor returned `absent`/`not_expressed` for the explicitly negated dial proposition expected as `present`/`unsupported`/`expressed`. Usage was 3,190 input, 819 output, 4,009 total tokens; provider cost was unavailable. No retry, repair, resampling, model substitution, or pilot call occurred. Evidence is preserved in `docs/receipts/MNEME_P2.3_Assessor_Qualification_Monitor_V7_Failure_Receipt.md` and `.json`; P2.3 remains waiting for assessor-suitability review.

## 2026-09-20 P2.3 polarity contract remediation

- Applied the additive semantic correction after the self-contained-monitor v7 Q3 stop. Assessor schema `p2-assessor-v5` and prompt `p2-assessor-production-v7` now separate proposition coverage (`present`/`absent`/`unknown`) from relation support (`supported`/`contradicted`/`unsupported`/`unknown`) and expression polarity (`affirmed`/`negated`/`not_expressed`/`unknown`), with fail-closed cross-field validation and exact evidence requirements. The learner observation boundary persists and replays semantic disposition; contradicted evidence earns no positive credit, is not converted to absence, and conflicting duplicate dispositions fail closed. Historical v4 results have an explicit archival reader and all historical receipts remain unchanged. Offline validation passed at 304 pytest tests, Ruff, strict mypy, wheel/fresh-install smoke, and zero provider calls. Evidence: `docs/receipts/MNEME_P2.3_Assessor_Polarity_Contract_Remediation_Receipt.md` and `.json`.

## 2026-09-20 P2.3 polarity v8 qualification pass

- Executed exactly one fixed Q1/Q2/Q3 DeepInfra Qwen qualification under `p2-assessor-v5` / `p2-assessor-production-v7` after the offline polarity correction. All three calls returned and were durably retained before validation: Q1/Q2 passed, and Q3 passed with `present` / `contradicted` / `negated` plus exact evidence for the dial negation; unavailable output remained `unknown`. Usage was 3,610 input, 790 output, 4,400 total tokens; provider cost unavailable. No retry, repair, resampling, model substitution, or pilot call occurred. Qualification evidence is preserved in `docs/receipts/MNEME_P2.3_Assessor_Qualification_Polarity_V8_Pass_Receipt.md` and `.json`; the bounded P2.3 pilot may proceed under the unchanged budget and stop rules.

## 2026-09-20 P2.3 bounded pilot runtime candidate

- Added an offline-only orchestration boundary that composes `PilotRun` reservations, `ContinuityService` developmental acceptance, interpretation result persistence/validation, `InterpretationPublisher`, and `FrozenEvaluationView` without introducing new semantic or learner rules. Stable coordinates are exact-once; uncertain provider calls are never regenerated; frozen evaluation publishes only external artifacts. Added four FakeHost regressions covering developmental idempotency, extraction/publication, frozen evaluation isolation, and private-snapshot binding. No provider call occurred.

## 2026-09-20 P2.3 partial pilot probe

- After the fixed polarity v8 assessor qualification passed, a bounded pilot probe used the existing PilotRuntime with the approved Gemma developing host. Exactly two post-qualification calls were dispatched at fixed coordinates: one development response and one extraction. Both provider results were returned and durably persisted; the extraction passed local residue validation. The probe stopped before any assessor or evaluation call after a harness serialization error, without retry or replacement. The repository currently lacks a committed fixed-fixture schedule/orchestrator and CLI path for the full 48-response/48-extraction/48-assessment/144-readout contract, so no P2.3 adequacy or completion claim is made. Evidence: `docs/receipts/MNEME_P2.3_Pilot_Partial_Probe_Receipt.md` and `.json`.

## 2026-09-20 P2.3 pilot artifact restart correction

- Offline audit of the partial pilot probe found that `PilotRuntime` publishes an `extraction/` artifact directory while `ArtifactStore.verify_run()` rejected that directory on restart. The verifier now admits and validates the existing extraction artifact category, with a regression proving a run containing extraction output reopens as `RUNNING`. Focused runtime tests and the complete 308-test suite pass; no provider call was made for this correction. The partial probe receipt remains historical and unchanged.

## 2026-09-20 P2.3 extraction repair binding correction

- Offline audit found that a repair reservation used a new laboratory call ID while `InterpretationService` correctly retained the original episode interpretation operation. `PilotRuntime.extract()` now separates those coordinates, reuses the original operation for the single permitted repair, and persists/validates the repair result under the new call reservation without creating a second interpretation. Focused runtime tests, Ruff, and the complete 308-test suite pass; no provider call was made for this correction.

## 2026-09-20 P2.3 assessment artifact restart correction

- The pilot runtime writes assessor results under `assessment/`; the artifact verifier had allowed the runtime API to publish that directory but rejected it during restart verification. The verifier now admits and validates the existing assessment category alongside extraction, with runtime tests and Ruff passing. No provider call was made for this correction.

## 2026-09-20 P2.3 pilot extraction stop

- The approved post-qualification pilot was dispatched at fixed coordinates and stopped under the finite-repair rule. Six provider calls returned: two Gemma development responses, two initial Gemma extractions, one Gemma extraction repair, and one Qwen assessment. Subject 0 episode 2 failed strict source-bound quotation validation on both initial and repair output; the model-output quotation did not occur verbatim in source `s1`. No evaluation calls were made, and no adequacy or completion claim is made. Usage was 3,411 input, 2,128 output, 5,539 total tokens; cost unavailable. Evidence: `docs/receipts/MNEME_P2.3_Pilot_Extraction_Stop_Receipt.md` and `.json`.

## 2026-09-20 P2.3 pilot extraction stop

- The approved post-qualification pilot was dispatched at fixed coordinates and stopped under the finite-repair rule. Six provider calls returned: two Gemma development responses, two initial Gemma extractions, one Gemma extraction repair, and one Qwen assessment. Subject 0 episode 2 failed strict source-bound quotation validation on both initial and repair output; the model-output quotation did not occur verbatim in source `s1`. No evaluation calls were made, and no adequacy or completion claim is made. Usage was 3,411 input, 2,128 output, 5,539 total tokens; cost unavailable. Evidence: `docs/receipts/MNEME_P2.3_Pilot_Extraction_Stop_Receipt.md` and `.json`.

## 2026-09-20 P2.3 extraction quotation formatting correction

- After the finite pilot stop showed Gemma stripping Markdown markers from model-output quotations, the extraction prompt was tightened to state that every formatting marker, punctuation mark, and whitespace character is part of the immutable source and must be copied exactly. A prompt regression covers this instruction. The strict quotation validator is unchanged; no historical output or receipt was rewritten and no provider call was made for this correction. Focused semantic/interpreter tests and the complete 308-test suite pass.

## 2026-09-20 P2.3 pilot request and usage audit correction

- The pilot runtime now persists the exact sanitized GenerationRequest payload for development, extraction, assessor, and evaluation artifacts. Extraction reservations normalize the durable `token_usage` field into the same usage accounting shape used by other provider roles. Focused runtime tests cover request retention and extraction usage; no provider call was made for this correction. P2.3 remains stopped pending the fixed schedule/orchestrator and the P2.2 audit repairs.
## 2026-09-20 P2.3 assessor polarity contract regression audit

- Re-audited the existing `p2-assessor-v5` / `p2-assessor-production-v7` polarity boundary and added paired insufficient-statement and double-negative regression fixtures. Full offline validation passed at 312 pytest tests, Ruff, strict mypy, wheel/fresh-install smoke, and zero provider calls. Historical qualification receipts remain unchanged; the latest polarity-v8 pass remains the current live evidence.

## 2026-09-20 Phase Two queue reconciliation after polarity audit

- Pointed P2.2 and P2.3 at candidate `f11b884`; P2.2 is `VALIDATING` pending dedicated recovery/identity receipts and final adversarial audit. P2.3 remains `WAITING` on P2.2 and the fixed pilot boundary; the polarity-v8 qualification pass remains the latest live evidence and no unchanged qualification was resampled.

## 2026-09-20 P2.2 recovery and evidence audit

- Added the five required P2.2 evidence receipts covering six deterministic dynamics scenarios, feedback/rebuild, reviewed identity, fork/revocation, and recovery. Added a simulated quarantine-rebuild interruption proving the authority event remains durable and explicit replay rebuild recovers a coherent materialized state. Offline validation passed at 313 pytest tests, Ruff, strict mypy, and no provider calls; P2.2 remains validating until the pushed CI result is recorded.

## 2026-09-20 P2.2 acceptance and P2.3 queue transition

- P2.2 is marked `DONE` after the five receipts, 313-test offline suite, Ruff, strict mypy, wheel/fresh-install smoke, and CI run `35546205491` passed. P2.3 no longer waits on the stale external qualification dependency: its polarity-v8 Q1/Q2/Q3 pass remains preserved, while the package validates the fixed pilot execution boundary before any new pilot calls.

## 2026-09-20 P2.3 production-path integration correction

- The fixed pilot now has a production-shaped assessor adapter that serializes complete source-bound requests, validates semantic observations, resolves provenance deterministically, and publishes learner observations through the existing atomic interpretation boundary. Pilot study reports and completed development/evaluation coordinates are persisted for restart-safe resume without repeating returned provider calls or completed probes. Development-response and extraction accounting roles now resolve to the single prepared `developing` host binding. FakeHost adapter, role-binding, and resume regressions pass; no provider call occurred.

## 2026-09-20 P2.3 offline integration receipt

- Published `MNEME_P2.3_Pilot_Production_Path_Receipt` and reconciled the queue to commit `2db5aed`. The pushed offline gate passed 315 pytest tests, Ruff, strict mypy, wheel build, fresh-install CLI smoke, and CI `35547126266`; no provider call occurred. P2.3 remains validating for the bounded live pilot, with historical qualification and extraction-stop evidence preserved unchanged.

## 2026-09-21 P2.3 fresh pilot extraction/assessment stop

- Reused the preserved polarity-v8 qualification evidence and dispatched exactly three new Gemma calls for a fresh fixed pilot coordinate: one development response, one initial extraction, and one permitted repair. All returned and were durably retained. The initial extraction failed strict source-bound evidence validation; the repair passed residue validation but supplied no relationship edge, so the production assessor/publication boundary stopped with `extraction has no assessable relationship`. No Qwen assessor or evaluation calls were made. Usage was 1,488 input, 830 output, 2,318 total tokens; cost unavailable. Evidence is preserved in `docs/receipts/MNEME_P2.3_Pilot_Live_Extraction_Stop_20260920.md` and `.json`; no historical receipt was rewritten and no automatic resampling occurred.

## 2026-09-21 P2.3 live evidence bundle

- Added the complete sanitized development/extraction request and result bundle for `p2-pilot-live-20260920` under `docs/receipts/MNEME_P2.3_Pilot_Live_Extraction_Stop_20260920_Bundle.json`. It contains no credential or authorization data and preserves the exact three returned provider results needed to audit the stop.

## 2026-09-21 P2.3 edge-less extraction boundary correction

- Corrected the in-scope pilot integration defect exposed by the fresh stop: a structurally valid residue with no relationship edge is now recorded as an explicit excluded terminal opportunity with zero learner credit, atomically accepted through the existing publication boundary, and allowed to continue the fixed schedule without an assessor call or invented proposition. Focused regressions, Ruff, and strict mypy passed; no provider call occurred. Historical live stop evidence remains unchanged.

## 2026-09-21 P2.3 second live extraction stop and budget boundary

- After the edge-less exclusion correction passed offline and CI, a fresh bounded run used the remaining 287-call/189,696-output-token envelope. Six calls returned: two Gemma development responses, three Gemma extraction attempts including one repair, and one Qwen assessment. The first episode reached accepted extraction, assessment, and publication; episode 1 failed strict source-bound validation after its one repair because Gemma omitted Markdown emphasis delimiters from a model-output quotation. No evaluation calls or resampling occurred. Usage was 3,697 input, 2,371 output, 6,068 total tokens; cost unavailable. Historical evidence is unchanged. With 18 calls now consumed, 281 calls remain, below the 288 scheduled pilot calls before repairs; continuation requires budget review.

## 2026-09-21 P2.3 assessor coverage/polarity v9 offline correction

- Prospectively versioned the production assessor contract to `p2-assessor-v6` / `p2-assessor-production-v8`. Coverage, relation support, and expression polarity remain separate; explicit negation is `present/contradicted/negated`, incomplete source coverage is `unknown`, and cross-field combinations fail closed. The previous v5 contract is readable only through the explicit archival reader, and historical provider evidence remains unchanged. Audited learner handling retains contradicted evidence without positive credit, absence conversion, or automatic contextual consequence; replay reproduces the same disposition. Validation passed at 318 pytest tests, Ruff, strict mypy, wheel/fresh-install smoke, and zero provider calls. Evidence: `docs/receipts/MNEME_P2.3_Assessor_Coverage_Polarity_V9_Offline_Receipt.md` and `.json`.

## 2026-09-21 P2.3 assessor coverage/polarity v9 qualification pass

- Executed exactly one fixed three-call DeepInfra Qwen qualification under `p2-assessor-v6` / `p2-assessor-production-v8`. Q1, Q2, and Q3 all passed; results were persisted before validation, with no retries, repairs, resampling, or model substitution. Usage was 3,784 input, 801 output, 4,585 total tokens; provider cost unavailable. The qualification audit verified artifact integrity, host binding, semantic coverage/polarity, deterministic provenance, and exact-once accounting. Total Phase Two campaign calls are now 21, leaving 278 under the unchanged 299-call ceiling; the approved 288-call no-repair pilot schedule therefore cannot fit, so no pilot call was dispatched. Evidence: `docs/receipts/MNEME_P2.3_Assessor_Qualification_Coverage_Polarity_V9_Pass_Receipt.md` and `.json`.

## 2026-09-21 P2.3 lifetime budget reconciliation correction

- Audited all persisted Phase Two qualification and pilot receipts against the governing assessor-role addendum. The prior queue note undercounted historical qualification attempts. Counting each persisted provider call once, while deduplicating the pilot partial probe already included in the later six-call stop, yields 42 campaign calls, 34,591 input tokens, 11,988 output tokens, and 46,579 total tokens; provider cost remains unknown. The unchanged 299-call ceiling leaves 257 calls, below the 288-call no-repair pilot minimum. Historical receipts remain unchanged; no provider call was made for this reconciliation. Evidence: `docs/receipts/MNEME_P2.3_Budget_Reconciliation_Receipt.md` and `.json`.

## 2026-09-21 P2.3 budget schedule terminology correction

- Clarified that 288 calls is the pilot-only no-repair schedule, while the governing assessor-role addendum calls the full no-repair schedule 291 calls including the three qualification calls. The 299-call ceiling, 42 consumed calls, 257 remaining calls, and zero post-v9 pilot calls are unchanged. No provider call was made; historical receipts remain unchanged. Evidence: `docs/receipts/MNEME_P2.3_Budget_Reconciliation_Correction_Receipt.md` and `.json`.

## 2026-09-21 P2.3 queue dependency registration correction

- Registered the two unresolved P2.3 review dependencies in `.codex/work-queue.json` using the canonical queue transition. A controller status audit now preserves `WAITING` with `READY=0`, `RUNNING=0`, `VALIDATING=0`, and `WAITING=1`; no provider call or pilot dispatch occurred. This changes queue bookkeeping only and does not resolve either review dependency.

## 2026-09-21 P2.3 hard-idle budget blocker census

- Recorded the canonical queue census at `d1f874d`: 10 DONE, 0 READY, 0 RUNNING, 0 VALIDATING, and one required P2.3 package WAITING on the two unresolved review dependencies. The reconciled 42-call ledger leaves 257 calls, below both the 288-call pilot-only and 291-call full no-repair schedules. No provider call was made and Phase Three did not begin. Evidence: `docs/receipts/MNEME_P2.3_Budget_Blocker_Census_Receipt.md` and `.json`.

## 2026-09-24 Phase Two operational budget contingency

- Recorded the standing in-scope contingency authority: the larger of +100 calls or +25% of the approved campaign ceiling, with cumulative accounting, no favorable resampling, and an unchanged 204,288 output-token ceiling. For P2.3 this makes a 399-call operational cap after the nominal 299-call ceiling; 42 historical calls leave 357 calls in the contingency envelope. The budget review is resolved, while the extraction-stop review remains substantive. Evidence: `docs/decisions/MNEME_P2_Operational_Budget_Contingency_Addendum.md` and `docs/receipts/MNEME_P2.3_Budget_Contingency_Authorization_Receipt.md`.

## 2026-09-24 P2.3 failed-coordinate recovery correction

- Added an explicit schema-8 recovery path for a failed extraction after the historical pilot exhausted its one repair. The failed operation remains immutable; a new versioned recovery operation records its superseded operation and uses a new fixed coordinate. Accepted developmental responses are never redispatched. Offline provider calls: zero. Evidence: `docs/receipts/MNEME_P2.3_Extraction_Recovery_Correction_Receipt.md` and `.json`.

## 2026-09-24 P2.3 recovery-coordinate correction

- The first recovery attempt consumed one Gemma extraction call and returned invalid residue; its repair was rejected before dispatch because the recovery operation identity was not retained. The repair path now reuses that operation ID while reserving a distinct deterministic laboratory coordinate, and subsequent recovery IDs derive from the superseded operation. The returned result and failed row remain preserved; 319 pytest, Ruff, strict mypy, and package smoke pass with zero calls for this correction. Evidence: `docs/receipts/MNEME_P2.3_Recovery_Coordinate_Correction_Receipt.md` and `.json`.

## 2026-09-24 P2.3 recovery migration correction

- The first continuation's one recovery extraction call reached publication but exposed a v7→v8 SQLite migration foreign-key rewrite to temporary `__v7_*` names. Legacy ALTER semantics are now enabled during the explicit table rebuild; focused migration checks and the complete 319-test, Ruff, strict mypy, and package-smoke suite pass with zero calls for this correction. The failed continuation evidence remains unchanged. Evidence: `docs/receipts/MNEME_P2.3_Recovery_Migration_Fix_Receipt.md` and `.json`.

## 2026-09-24 P2.3 assessor quotation prompt correction

- The fixed continuation reached 20 returned calls before Qwen's semantically correct relationship judgment was rejected because Markdown markers were omitted from its evidence quotation. The production assessor prompt is versioned from v8 to v9 with explicit formatting-preservation instructions; strict source validation is unchanged, 319 tests/Ruff/strict mypy/package smoke pass, and no corrective provider call was made. Historical v8 evidence remains unchanged. Evidence: `docs/receipts/MNEME_P2.3_Assessor_Quote_Prompt_Correction_Receipt.md` and `.json`.

## 2026-09-24 P2.3 assessor correspondence-scope correction

- The v9 continuation preserved exact quotation formatting but Qwen's valid current-input correspondence `s0` was rejected because the production monitor declared only model-output correspondence slots. Production monitors now declare all required source slots; deterministic roles and ancestry still resolve provenance. Offline 319-test/Ruff/strict-mypy/package-smoke validation passed with zero calls. Evidence: `docs/receipts/MNEME_P2.3_Assessor_Correspondence_Scope_Correction_Receipt.md` and `.json`.

## 2026-09-24 P2.3 extraction v2 and lifecycle correction

- The latest preserved pilot stop at `extraction-s0-e8` was a strict non-verbatim Markdown quotation failure in both the initial extraction and its one repair. New extraction calls now use the versioned `residue-v2` prompt with an exact formatting example, while strict validation and all historical v1 evidence remain unchanged. Pilot status is synchronized into the run manifest, accepted-development coordinates and repair counts are persisted before later stages, and contradicted learner updates use an explicit no-positive-credit reason. Offline 320-test, Ruff, strict mypy, and learner/publication/pilot regressions passed with zero provider calls. Evidence: `docs/receipts/MNEME_P2.3_Extraction_V2_Lifecycle_Correction_Receipt.md` and `.json`.

## 2026-09-24 P2.3 recovery-v2 live stop

- The private continuation `p2-pilot-recovery-20260924h` returned 48 bounded provider results, reached 25 valid extractions and 13 admitted relationships, then stopped at `extraction-s1-e1` after its one permitted repair because Gemma omitted Markdown bullet/bold markers from a source quotation. Strict source validation correctly rejected both attempts; no evaluation call was made. Evidence: `docs/receipts/MNEME_P2.3_Pilot_Recovery_V2_Failure_20260924.md`.

## 2026-09-24 P2.3 extraction-v3 correction

- Added a concrete Markdown-list/bold-marker example to the provider-facing `residue-v3` extractor prompt after the h stop; strict quotation validation and historical residue contracts remain unchanged. The 321-test, Ruff, strict-mypy, and wheel smoke gate passed with zero provider calls. Evidence: `docs/receipts/MNEME_P2.3_Extraction_V3_Markdown_List_Correction_Receipt.md`.

## 2026-09-24 P2.3 recovery-v3 stop

- The i continuation used one residue-v3 recovery extraction after reusing the accepted h response. Gemma again omitted immutable Markdown list/bold markers despite the concrete v3 instruction; strict validation rejected it and the exhausted eight-call repair pool prevented a repair. No assessment or evaluation call followed. Cumulative campaign usage is 120 returned calls. Evidence: `docs/receipts/MNEME_P2.3_Pilot_Recovery_V3_Failure_20260924.md`.

## 2026-09-24 P2.3 queue blocker update

- P2.3 is recorded as `WAITING` on `review:p2.3-extractor-host-suitability-after-v3`. The queue preserves the v2/v3 offline correction receipts and h/i live-stop evidence; the standing 399-call operational cap was not the blocker, and no unchanged resampling is authorized.

## 2026-09-24 P2.3 semantic evidence reconciliation correction

- Added bounded temporary experimental semantic evidence reconciliation after the preserved h/i extraction stops. Exact immutable-source quotation validation remains the first path. Only otherwise plausible missing or ambiguous quotations may be sent to a separately accounted non-developing reviewer, which may return one exact unique source quotation; deterministic software performs matching, Unicode offsets, and validation. False, unknown, malformed, nonexistent, and duplicate quotations fail closed. The original failed operation remains immutable and a versioned recovery operation passes through the existing validation/publication boundary. Offline validation passed with 333 pytest, Ruff, strict mypy, and zero provider calls; the fixed four-case reviewer qualification is pending. Historical 120 returned calls and receipts are unchanged.

## 2026-09-24 P2.3 semantic evidence reviewer qualification stop

- The fixed reviewer qualification reached DeepInfra successfully for three returned calls (531 input, 673 output, 1,204 total tokens; cost unavailable). Q1 Markdown-formatting omission and Q2 source-grounded paraphrase returned exact unique quotations and passed. Q3 correctly rejected an unsupported extraction semantically but included an empty `evidence` field with `grounded:false`; strict validation rejected the malformed shape and marked the qualification failed closed. No fourth case, pilot call, retry, or resampling occurred. Historical 120 campaign calls and all prior receipts remain unchanged. Evidence: `docs/receipts/MNEME_P2.3_Semantic_Evidence_Review_Qualification_Failure_20260924.md` and `.json`.
