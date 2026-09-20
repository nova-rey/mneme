# MNEME Phase Two — Active Goal Amendment: Separate Assessor Host

**Amendment ID:** P2-ASSESSOR-SEPARATION-01  
**Date:** 2026-09-20  
**Type:** Targeted implementation and execution addendum to the existing Phase Two goal  
**Scope:** Correct the blocked P2.3 assessor boundary; preserve the approved learner, developing host, pilot, and release gates  
**Last reported checkpoint:** `9312013344d268618d02f3936f5edb943fd09031`

> **Keep the existing goal. Keep the approved plan. Keep Gemma as the developing instance. Give semantic assessment a separately configured, qualified host.**

This instruction supplements the currently active or blocked Goal Mode campaign. It does not replace the goal or require a new Phase Two plan. Resume the existing campaign at its recorded state. Implement the bounded correction below, audit and push it, qualify the selected assessor once, and continue the already authorized pilot only if the qualification gate passes.

## 1. Authority and what does not change

Read current clean `main`, the approved Phase Two plan and amendments, work queue, `bible.md`, assessor implementation, qualification fixtures, and preserved failure receipts before changing code. Record the actual starting SHA. Do not reset the repository to the last reported checkpoint or discard later legitimate documentation changes.

This addendum authorizes these specific changes:

1. Separate assessor-host selection from the developing-host selection.
2. Add the selected hosted assessor through the existing host boundary.
3. Bind permissions, provenance, caches, budgets, qualification, and production dispatch to the correct role.
4. Version the resulting experimental configuration without rewriting historical configurations.
5. Perform one bounded new qualification attempt after the offline gate.
6. If it passes, continue the unused, previously authorized P2.3 pilot under the amended role configuration and existing stop rules.

Everything else remains governed by the approved plan. In particular, do not change learner coefficients, restraint/recovery semantics, source-dependence rules, relevance clocks, fixture content, split membership, semantic answer criteria, adequacy thresholds, or release conditions merely to make this correction pass.

P2.1 and P2.2 remain completed historical packages. Rerun their regression checks where the integration touches them; do not erase their acceptance history or reimplement them. Keep P2.3 incomplete until its actual requirements are met.

Do not implement Phase Three or the future Developmental Self-Context proposal. That proposal remains developer-only, non-blocking future context.

## 2. Diagnosis to preserve accurately

The v4 receipt records three successful DeepInfra responses followed by semantic qualification failures. The provider and credential worked; pilot calls remained zero. The selected Gemma assessor configuration repeatedly failed the required relation, negation, coverage, and attribution cases. [R1]

This justifies trying a different assessor. It does **not** prove that all small models are unsuitable, that parameter count alone determines competence, or that no interface problem could remain.

Before dispatching the replacement, inspect the exact serialized qualification requests. Verify that each contains the complete proposition being assessed, its participants, relation direction, polarity, requested source coverage, availability, and role-scoped ancestry. Compare those fields with the frozen expected results. Do not rely on an abbreviated case name or a conversational retelling of Q2.

If an omitted proposition, contradictory fixture, or material validator defect is found, report it before live execution. Do not secretly alter the question or its answer key as part of changing the model.

Preserve every historical failure. New results belong to a new configuration and qualification attempt, not to a repaired version of an old result.

## 3. Select one concrete assessor—not a model-shopping campaign

Use this **single designated candidate**, subject to non-generative catalog/configuration verification:

```text
Provider: DeepInfra, standard serverless tier
Assessor model: Qwen/Qwen3-235B-A22B-Instruct-2507
API base: https://api.deepinfra.com/v1/openai
Endpoint: /chat/completions
Credential: existing DEEPINFRA_TOKEN
```

DeepInfra currently lists this model; its upstream card describes an instruction-tuned, non-thinking model. These properties make it a practical candidate for the existing bounded text/JSON task, not a guarantee that it will pass. The upstream model is open-weight, but this assignment does not require downloading or hosting it. [R4–R6]

The model designation contains a large parameter count. This is **API inference only**: no GPU rental, local deployment, weight download, private endpoint, subscription purchase, or hardware procurement.

Recheck the official model page/API metadata before execution. Record the provider model ID, endpoint, service tier, documented runtime/quantization information, settings, and price observation date. Unknown served revision stays unknown; an upstream repository name or commit does not establish the provider's exact weights.

Reference prices observed on 2026-09-20 were **USD 0.09 per million input tokens and USD 0.55 per million output tokens**, standard tier. Refresh the rate evidence; do not reuse earlier third-party prices or treat this note as a provider invoice. [R4]

No automatic substitution, second candidate, fallback to Gemma, ensemble vote, or further E4B qualification is authorized. If this exact candidate is unavailable, requires unapproved account changes, or cannot use the declared interface/resource limits, stop with the narrow reason.

## 4. Role separation: only the assessor changes

Implement explicit execution bindings conceptually equivalent to:

| Role | Host after this amendment |
| --- | --- |
| Developing conversational instance | Existing pinned `google/gemma-4-E4B-it` through DeepInfra |
| Developmental response generation | Same Gemma binding and existing settings |
| Residue extraction and permitted extraction repair | Existing approved extractor binding; do not upgrade it incidentally |
| Semantic assessment, including qualification | Designated Qwen assessor |
| Frozen learned/fixed/no-memory response readouts | Same Gemma developing-host binding |
| Identity adoption/review | Existing approved role and policy; no new naming calls in this pilot |
| Arithmetic, caps, clocks, canonicalization, persistence | Deterministic MNEME software |

Use the same common `Host` interface, existing controller, durable operation services, and experiment runner. Introduce only the configuration/injection necessary to select the assessor separately. Do not create another framework, multi-agent conversation, or execution engine.

A minimal provider-neutral DeepInfra transport with model-specific configuration is appropriate if needed. Preserve the existing Gemma entry point and behavior for existing callers.

**Do not simply instantiate `DeepInfraGemmaHost(model_id="Qwen/...")`.** At the inspected checkpoint, its fingerprint still contains Gemma-specific family, tokenizer/upstream, canonical-revision and context metadata. Merely changing the request's model ID would mislabel Qwen execution. Separate those fields correctly and regression-test both hosts. [R3]

The run's model map must say which role each host serves. One global `--host` setting must not silently switch all roles. New mixed-role pilot contracts must fail closed when the assessor binding is missing; historical single-host contracts can retain their explicit legacy interpretation.

## 5. Preserve the assessor task, not a preferred answer

Keep the current production assessor schema, prompt text/version, validators, frozen Q1/Q2/Q3 material, and semantic expectations for the first replacement qualification, after the static consistency check in section 2.

Preserve the exact task content and ordinary sampling settings used by the current production contract. The authorized change is the assessor execution host and its truthful transport/configuration metadata. If a parameter is unsupported, do not silently drop or reinterpret it; report the incompatibility before paid execution.

Use the model's non-thinking instruction endpoint. Keep prompted raw JSON plus local validation for this attempt. Do not add native schema-constrained decoding, examples containing the qualification answers, hidden hints, extra critique passes, or model-specific few-shot coaching while also claiming only the host changed. Those would be separate interventions.

Qualification and pilot must use the same actual request builder, role mapping, source-mask behavior, prompt/schema version, settings, and result-validation path. Passing a special simplified qualification implementation is not acceptance.

The assessor judges the existing source-expression questions. It must not write improved replies for Gemma, add replacement relations, prescribe habits, assign rewards, choose names, compute learner arithmetic, or judge which personality the researcher should prefer.

A supported source claim means that the source expresses the proposition—not that the proposition is objectively true. Absent, unsupported, unknown, current-input echo, memory exposure, and replay keep their approved meanings. Known provenance takes precedence over an assessor's claim of independence. Do not silently translate semantically wrong answers into expected ones.

## 6. Keep the subject unchanged; acknowledge the changed development condition

Changing the assessor does not change Gemma's base weights or make Qwen the conversational instance. However, assessor decisions determine which observations can influence later state. Therefore **the assessor is part of the developmental condition**, not a scientifically neutral technician. [S1–S2]

Record the change in the experiment configuration and reporting. Use the same assessor configuration for both siblings and for every condition that calls for assessment. Do not switch assessors midway through a developmental trajectory.

Keep assessor explanations and metadata out of Gemma's prompt, identity, raw-episode stream, and extractor source bundle. Validated classifications may affect the learner through the approved path; the assessor's commentary must not become a fresh experience or independent evidence supporting itself.

Do not expose subject names, branch IDs, expected qualification answers, or desired behavioral outcomes as unnecessary cues to the assessor. Preserve required request-local references and source roles. Keep administrative references in provenance rather than behavioral instructions.

A stronger assessor can still have biases and make mistakes. Retain human inspection of source/claim/assessment pairs and existing semantic-integrity stops. Three qualification cases establish narrow interface viability, not an estimated reliability rate or truth-oracle status.

## 7. Versioning, host binding, caches, and permissions

Add a linked execution addendum; do not overwrite the approved Phase Two plan. Create a new experiment contract revision and qualification/run identifiers for the mixed-role configuration. Preserve original contracts, hashes, receipts and tags.

Bind at least the following to every assessment operation and its result:

- Call role and stable operation/scientific coordinate.
- Expected assessor host fingerprint and returned provider/model evidence where supplied.
- Prompt, schema, serializer and validation versions.
- Exact source/candidate/monitor payload, masks and exposure ancestry.
- Requested and reported effective generation settings.
- Call reservation, finish reason, usage or explicit unknowns, and terminal disposition.

Do not fill missing returned metadata from a different host or pass a served-model mismatch as merely a label difference. Use documented equivalences only, recorded explicitly.

Include the assessor binding in qualification certificates, pipeline/manifests, idempotency intent and relevant cache keys. A Gemma assessor result cannot satisfy a Qwen assessment or qualify Qwen through replay. Changing model, prompt, generation settings, source mask, or validator requires compatible new qualification evidence; never mix results under the old run identity.

Recorded-output replay remains exact and model-call-free. It reproduces saved annotations, not a claim that live Qwen sampling is deterministic.

Retain current scope and provider-reuse checks. Explicitly authorize the selected assessor for the approved synthetic qualification/pilot sources through the existing policy mechanism. Do not overwrite Gemma's subject binding or blanket-grant unrelated historical/private content to every configured host. Role-scoped revocation must prevent new dispatch and invalidate affected reuse.

Schema changes, if actually necessary, must be additive/versioned with backup, migration and historical-read tests. Do not fabricate missing historical assessor metadata or initiate a general storage rewrite.

## 8. Offline integration gate—before any paid call

Add focused tests exercising the real orchestration boundary with distinct, recording fake hosts. Merely adding an `assessor_host` field to a configuration is insufficient.

At minimum prove:

1. Responses, extraction/repairs, and frozen readouts reach their unchanged intended hosts; only assessment reaches the replacement host.
2. Qualification and production invoke the same assessor request/validation path.
3. A Qwen-configured host fingerprint contains no accidental Gemma canonical revision, family or tokenizer metadata.
4. Missing assessor configuration, swapped roles, host/configuration drift and qualification mismatch reject before dispatch.
5. A prior Gemma result/cache entry cannot be reused as a Qwen sample or certificate. Ordinary retries of a completed identical operation make no extra call.
6. Every result—including invalid JSON and wrong semantic classifications—is persisted before rejection. Unknown dispatch outcome is not retried.
7. Common instructions survive provider rendering exactly once; memory data remains subordinate and actual supplied content matches the exposure trace.
8. External-only masks and source-role boundaries hold with two different model objects. Assessor output does not become subject testimony or identity.
9. Permission/revocation checks apply to the selected role; secrets and untrusted provider errors do not leak into public artifacts.
10. All frozen probes preserve learner/graph/identity/clock state; assessor integration cannot create evaluation writeback.
11. New qualification and pilot reservations use separate roles and the correct model's rates/usage. Failed calls cannot disappear from cumulative accounting.
12. A partial or failed qualification never releases the pilot; a missing or altered qualification artifact invalidates execution and completion claims.

Run focused regressions, full pytest, Ruff, strict mypy, fresh-install CLI smoke, and required existing replay/recovery/isolation checks. Ordinary CI stays network-free.

Audit the integrated diff, actual serialized requests, role-dispatch traces and artifact inventory. Use independent coding reviewers where helpful; do not describe them as independent empirical validation.

Commit the additive documentation/configuration/code corrections, append `bible.md`, push through the existing serialized workflow, and verify remote SHA and required CI before qualification. Do not make an unlogged test request to check whether the endpoint works.

## 9. Explicit new qualification authorization and unused pilot budget

Upon receipt of this instruction in the active goal, after section 8 passes:

**Authorize one new qualification attempt, with at most three DeepInfra generation calls, using the designated Qwen assessor.**

Run the existing frozen Q1, Q2, Q3 in order through the corrected production path. Validate and persist each case before dispatching the next. Stop immediately on a known failure: this is a maximum of three, not an obligation to spend all three after failure.

No retries, repairs, replacement samples, model switching, prompt tweaking, extra qualification calls, or fresh acceptance campaign are authorized. Nondeterministic regeneration after a failed case is not resumption.

After all three pass, stop for the existing qualification audit and evidence publication. Verify the actual files, case dispositions, unchanged fixtures, selected role fingerprint, and budget ledger; commit/push/verify as required. Only then continue the previously authorized, **unused** P2.3 pilot under the new contract revision.

The expected ceiling, given the reported zero pilot calls, is:

| Role | Host | Calls at most | Output cap/call | Maximum output tokens |
| --- | --- | ---: | ---: | ---: |
| New qualification | Qwen assessor | 3 | 1,536 | 4,608 |
| Development responses | Existing Gemma | 48 | 256 | 12,288 |
| Initial extraction | Existing extractor | 48 | 1,536 | 73,728 |
| Development assessment | Same qualified Qwen | 48 | 1,536 | 73,728 |
| Frozen response readouts | Existing Gemma | 144 | 192 | 27,648 |
| Pooled extraction repairs | Existing extractor | 8 | 1,536 | 12,288 |
| **Total prospective ceiling** | | **299** | | **204,288** |

This is **three newly authorized qualification calls plus up to 296 unspent pilot calls**, not a new 299-call allowance on top of another unused pilot allowance. The no-repair schedule is 291 calls. Qwen handles at most 51 calls; unchanged Gemma/extractor roles handle at most 248.

Reconcile these figures against the actual ledger before dispatch. All previous qualification attempts remain charged in the lifetime/campaign totals. They are not retroactively erased by the new prospective ceiling. If any pilot coordinates have already been dispatched contrary to the reported state, do not simply restart or assume the table is unused; report the discrepancy.

Retain the approved 90-second per-call timeout, 32 KiB serialized-input limit, ten-hour cumulative active-execution bound, 1 GiB artifact ceiling, per-interpretation repair limit, and all stricter current limits. Do not widen them to accommodate an assessor failure. Qualification and pilot use the same assessment output cap.

Recalculate estimated cost by role from dated official rates before live dispatch. Keep measured usage, reserved maxima, estimated cost, and provider-reported charge separate. Missing billed cost does not prevent a clearly labeled estimate; missing usage must not become zero. Byte counts must not masquerade as exact input-token counts. No account top-ups, dedicated infrastructure purchases, or undisclosed paid probes are authorized.

## 10. Preserve stop behavior without mislabeling the blocker

If qualification fails, stop with zero pilot calls. Publish the actual sanitized source, candidate, request, response, expected semantic classification, observed classification, validation failure, fingerprint and usage. Do not resume prompt engineering or try a second model automatically.

Use accurate blocker wording, distinguishing:

- Role configuration/implementation defect.
- Unavailable credential or endpoint.
- Response/transport failure or uncertain outcome.
- Structural assessor-output failure.
- Semantic qualification failure.
- Authorization or resource limit.

A working provider returning an incorrect classification is not an access problem. Conversely, do not claim the model lacks a capability if the serialized request failed to supply the necessary evidence.

If qualification passes, run the original pilot sequence and unchanged learner with the role separation recorded. Preserve all pilot integrity, human-review, adequacy and research-outcome rules. A failed production assessment still stops as specified; passing qualification does not immunize the assessor from future failure.

Do not restart lineages, tune coefficients, reclassify fixtures, collect additional samples, or discard inconvenient outputs to obtain a favorable result. Weak or inconclusive behavioral outcomes retain their approved disposition.

## 11. Repository integration and campaign continuity

File this addendum under the existing decision/execution-amendment convention, for example:

`docs/decisions/MNEME_P2_Assessor_Role_Separation_Addendum.md`

Link it beside the approved Phase Two plan in `docs/README.md`; leave the original approved file unchanged. Record the role-specific execution decision, source evidence, named candidate, authorization, new configuration revision, offline audit and qualification results in the normal append-only history.

Update the existing P2.3 work item with a bounded assessor-remediation dependency/substep using the repository's queue conventions. Do not create a competing goal or abandon the existing campaign. Do not mark P2.3 DONE because the new adapter exists or three qualification calls pass.

Preserve the mandatory **stop feature work → audit → repair → validate → inspect evidence → commit → push → verify remote/CI → record gate disposition** flow. Proceed automatically only across gates this addendum and the existing authorization actually permit.

Keep the Phase Zero and Phase One tags unchanged. Phase Two closure/tagging follows the approved release matrix, including the distinction among engineering acceptance, pilot adequacy and research outcome. No Phase Three work begins.

## 12. Completion or blocker report

Report:

- Amendment, remediation and final evidence commit SHAs.
- Active campaign/work-queue status and any remaining blocker.
- Developing, extractor, assessor, evaluation and identity role bindings.
- Confirmation that Gemma's developing model/configuration did not change.
- Exact assessor fingerprint, configuration and qualification binding.
- Offline tests, integration traces, full validation and remote CI results.
- Q1/Q2/Q3 actual dispositions, calls dispatched/skipped, usage and evidence paths.
- Pilot status and per-role call/usage totals, separated from historical failures.
- Dated estimated costs versus any actual provider-reported cost.
- Evidence that assessor commentary stayed outside developmental source material.
- Engineering acceptance, pilot adequacy and research outcome separately.
- Final tag only if the original release conditions are genuinely satisfied.

The intended outcome is a resumed Phase Two goal with an assessor qualified for its narrow job—not a different developing model and not a claim that an external evaluator is infallible.

## Source and inspection notes

This addendum is a project instruction and explicitly authorized design change, not a report that the replacement has been implemented or qualified.

- **[S1] Governing MNEME specification**, §§6.2, 8–11 and 13–14: permits existing models for extraction/evaluation while the developing host stays frozen; treats model judgments as fallible annotations and requires versioned provenance.
- **[S2] Research Amendment 01**, especially R11, R19 and §10.4: warns about evaluator preferences and evaluator-mediated developmental bias. This note uses the supplied project's research framing; it does not independently reproduce those studies.
- **[R1] Inspected v4 failure receipt:** https://github.com/nova-rey/mneme/blob/9312013344d268618d02f3936f5edb943fd09031/docs/receipts/MNEME_P2.3_Assessor_Qualification_V4_Failure_Receipt.md
- **[R2] Inspected assessor-contract excerpt:** https://github.com/nova-rey/mneme/blob/9312013344d268618d02f3936f5edb943fd09031/src/mneme/development/assessment.py
- **[R3] Inspected DeepInfra adapter:** https://github.com/nova-rey/mneme/blob/9312013344d268618d02f3936f5edb943fd09031/src/mneme/hosts/deepinfra.py
- **[R4] Official DeepInfra candidate listing and observed rates:** https://deepinfra.com/Qwen/Qwen3-235B-A22B-Instruct-2507 — inspected 2026-09-20; recheck before execution.
- **[R5] Official DeepInfra chat-completions documentation:** https://docs.deepinfra.com/chat/overview — standard compatible endpoint and bearer-token use; inspected 2026-09-20.
- **[R6] Upstream model card:** https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-2507 — documents non-thinking instruction configuration; inspected 2026-09-20. Upstream metadata does not prove exact hosted-weight equivalence.

Only the receipt and the identified code excerpts were inspected for this handoff. No full repository audit, local test-suite execution, provider inference, credential access, or repository modification was performed while drafting it.
