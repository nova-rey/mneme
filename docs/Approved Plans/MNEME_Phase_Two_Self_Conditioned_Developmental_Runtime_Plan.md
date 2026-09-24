# MNEME Phase Two — Self-Conditioned Developmental Runtime

**APPROVED PLAN**  
**Approval date:** 2026-09-20  
**Repository:** `nova-rey/mneme`  
**Planning baseline:** `9c5619c8addd2172ddb64a51273183eba8d31ece`  
**Reference tag:** `mneme-phase-one-graph-preview`  
**Proposed release:** `0.2.0`, tagged `mneme-phase-two-developmental-runtime-preview` only after all gates pass  
**Execution boundary:** This document authorizes planning only. P2.1, P2.2, and P2.3 require separate implementation and live-budget authorization.

Phase One made source-backed associations available through a fixed wrapper. Phase Two adds one inspectable developmental mechanism: attributable experience can alter the future contextual influence of eligible associations. It does not claim personality, individuality, truth, usefulness, or user approval.

The implementation sequence is fixed:

```text
P2.1 replayable learner
    → stop, audit, publish, push
P2.2 restraint, retention, reviewed identity, recovery
    → stop, audit, publish, push
P2.3 bounded developmental pilot and candidate freeze
```

Phase Zero and Phase One tags, receipts, and failed historical attempts remain authoritative historical evidence. New findings must be recorded as new evidence.

## 1. Source reconciliation and reconnaissance

The current model-instance specification governs intent and evidence distinctions. The development roadmap governs Phase Two boundaries and the two-sibling pilot. The approved Phase One plan and its remediation receipts govern implemented contracts. The Developmental Dynamics Amendment supplies the scenarios and distinctions allocated to Phase Two. The identity/individuality amendment constrains interpretation; it does not prove that MNEME produces individuality.

| Requirement | Existing foundation | Phase Two landing | Deferred |
|---|---|---|---|
| Own-output development without approval | Durable episodes, interpretations, graph snapshots, and source-purpose masks | P2.1 source-aware observations and a pure learner | General causal attribution |
| Fixed versus learned retrieval | Fixed graph/controller and frozen readers | Corrected fixed comparator plus learned readout | Phase Three comparator families |
| Support versus expression | Evidence graph and explicit suppression directives | Separate `A`, `S`, and `E` state | Rich trait and neural models |
| Temporal recurrence | Durable history but no developmental clock | P2.1 opportunity clock; P2.2 retention | Biological lifespan models |
| Reviewed identity | Deliberate initial adoption and durable self-view | Proposal/review/accept/reject/unchanged transition | Self-recognition and autobiographical claims |
| Isolated measurement | Private immutable checkpoints and read-only evaluation | Learner, clock, policy, and authority pinned in frozen views | Population-scale individuality tests |
| Bounded pilot | P0.3 artifacts and P0.4/P1 comparison paths | Two siblings, 24 external episodes each, 12 disjoint probes | Phase Three cohorts |

Read-only reconnaissance found five prerequisites that must be handled inside P2.1 before adaptive behavior is added:

1. `controller.py` can replace a declared current system instruction when memory or identity payload exists. Common instructions must survive exactly once and memory must remain subordinate.
2. Duplicate evidence spans can change route ranking through `support_count`. The corrected fixed policy must use canonical distinct evidence/dependence identities, while the historical policy remains replayable.
3. Payload truncation can leave a trace claiming a route was applied when it was not present in the host-visible request. Selection, serialization, and actual exposure require separate records.
4. The historical Phase One edge `rain_jacket enables shower` has a valid quotation but does not express that directed proposition. Its old receipt and graph remain unchanged; future semantic admission must distinguish quotation validity from relationship meaning.
5. Identity generation results that fail validation are not currently durable. P2.2 must persist returned requests/results before validation.

The current graph publication also lacks direct interpretation/source foreign keys on graph edge evidence, and resolver decisions are recorded after raw graph materialization. Stable learner bindings must add those links and apply accepted resolution decisions operationally.

## 2. Architecture and operational definitions

### Architecture

Phase Two extends the existing per-lineage SQLite store, explicit SQL transactions, immutable checkpoints, existing controller, experiment runner, and frozen reader. It does not add a service, ORM, broker, cloud database, distributed writer, or second authoritative memory store.

```text
declared input + pinned state
    → shared selection and rendering kernel
    → response reservation and generation outside a transaction
    → durable response and accepted episode
    → source-aware extraction
    → production-equivalent semantic assessment
    → validated observations and accepted resolver decisions
    → pure learner transition
    → atomic graph/learner publication
    → next developmental opportunity
```

Evaluation invokes the same pure readout kernel over a frozen snapshot and writes only external artifacts. It cannot advance the opportunity clock, update learner state, refresh exposure counters, mutate manifests, or create developmental evidence.

### Operational definitions

- **Opportunity:** one completed developmental processing cycle for one accepted external turn. It advances once when its interpretation/assessment reaches a terminal disposition, including an explicit excluded disposition.
- **Global opportunity clock `G`:** the count of completed developmental opportunities. Lineage revision, accepted episode count, graph revision, learner revision, self-view version, and `G` remain separate counters.
- **Relevant clock `r`:** the count of completed, covered, context-valid opportunities for one monitored edge/context target.
- **Dependence group:** recorded ancestry that prevents copies, replay, reinjection, or overlapping interpretations from becoming independent support.
- **Observation:** an immutable source-bound occurrence with origin, target, context, status, dependence, coverage, and uncertainty.
- **Observed support:** a valid occurrence or absence found by the declared measurement procedure. It is not the same as numerical credit.
- **Credited support:** the bounded numerical contribution awarded after dependence and cap rules.
- **Support:** durable association state, represented by `A` and `S`, without a truth or utility claim.
- **Contextual expression:** the bounded `E` adjustment that controls whether an otherwise eligible route is supplied in a context.
- **Retention:** deterministic state reduction on measured non-recurrence or an explicit modeled advance. It is never inferred from missing data.
- **Consolidation:** slower-changing support earned across separated relevant opportunities.
- **Consequence:** a separately attributable contextual assessment. Unknown outcomes remain unknown.
- **Quarantine:** a hard eligibility prohibition on affected evidence, targets, caches, managed snapshots, and inherited derivatives until deterministic review/rebuild.
- **Identity review:** a durable decision about a proposed name transition, separate from ordinary conversation.

## 3. Stable evidence, semantic assessment, and dependence

### Production semantic contract

The extractor remains responsible for concepts, relationships, source quotations, and approved enum values. Software resolves quotations, Unicode spans, source bindings, aliases, arithmetic, caps, and accounting.

The exact source-bound quotation check is the normal fast path. During the
Phase Two pilot only, an otherwise plausible extraction that fails solely
because its quotation cannot be matched exactly may use the temporary
**experimental semantic evidence reconciliation** role. That bounded reviewer
receives the immutable source, extracted proposition, proposed quotation, and
source role; it may return `grounded=true` with one exact quotation copied from
the source, `grounded=false`, or `grounded=unknown`. Software then requires a
unique exact match and computes the canonical span. The reviewer does not
assign provenance, learner credit, offsets, or developmental consequences.
Malformed, false, unknown, missing, or ambiguous quotations fail closed. This
role is research scaffolding, is separately accounted for, and is a candidate
for removal or replacement when the acquisition mechanism changes; it is not a
developing MNEME component.

The semantic assessor answers:

> Does this source express the proposed relationship with these participants, direction, polarity, and context?

It is not a truth oracle, personality judge, approval signal, or reward model. For model-output sources, recognizing that the output expressed a proposition does not establish that proposition as fact.

Every assessor request uses the same production structure in qualification and pilot:

- candidate occurrences and immutable source references;
- source role and source availability;
- required monitored targets and coverage requirements;
- actually supplied memory exposure;
- replay/dependence ancestry;
- context and source-purpose mask;
- relation support, expression status, dependence category, source quotation, and coverage fields.

Every requested monitor must return a row. Missing rows are validation failures, never absence. `present` requires a unique verbatim quotation. `absent` requires complete coverage of available source slots and an absence reason, with no quotation of nonexistent text. `unknown` identifies incomplete or unavailable coverage. Recorded exposure ancestry overrides an assessor claim of independence.

### Stable identities

Concept identity is a versioned canonical descriptor containing normalized label, kind, and explicit disambiguation context. Edge identity hashes ordered semantic source/target identities, relationship meaning, polarity, and applicable context. Route identity hashes ordered semantic edge identities and route context.

Snapshot UUIDs, extractor keys such as `e1`, collision suffixes, insertion order, timestamps, and source occurrence IDs are not learner identities. Evidence occurrence identity remains separate and links directly to its interpretation and source.

Accepted resolver decisions may join aliases. A merge, split, source correction, or reinterpretation creates a new binding version and deterministic rebuild. Old weights are never added or subtracted naively across a changed binding. A derived route remains a navigable path; it is not a new transitive causal claim.

### Dependence mapping

Apply classification per relationship occurrence, not per entire response.

| Source/attribution | Factor | Grouping and rule |
|---|---:|---|
| New external evidence with separately established provenance | `1.00` | Its evidence root |
| External material copied/replayed from an earlier source | `0` | Original root; no new independent root |
| Model output restating current external input | `0` | Current external root; `current_input_echo` |
| Model output restating supplied memory/replay | `0.10` | Inherited roots; induced subcap applies |
| Model-origin association with no identified antecedent | `0.25` | Provisional origin root; independence unproven |
| Unknown or conflicting attribution | `0` pending resolution | Preserve uncertainty; no optimistic fallback |
| Duplicate accepted application | `0` | Same application coordinate |
| Cached annotation on a new accepted experience | Depends on source rows | Cache is not an independent assessment |

The assessor category `external_supported` supports an external source occurrence. On model output that repeats the current input, it is a `current_input_echo` and contributes zero additional credit. `no_identified_link` never proves independent thought.

Retain separate external and model-output pools of `0.08` per opportunity. Divide each pool among distinct admitted edge targets before dependence discounts; unused or zero-credit shares are not redistributed. Across both pools, the same canonical edge/dependence ancestry shares the `0.12` lifetime group cap, model-induced contributions share the `0.01` induced subcap, the rolling edge/context cap is `0.20` over eight relevant opportunities, and total credit per opportunity is `0.16`.

## 4. Learner state and exact transition rule

### State

For every canonical edge/context, store:

- `A ∈ [0,1]`: short-term accessibility;
- `S ∈ [0,1]`: consolidated support;
- relevant-opportunity count and recorded inactivity cause;
- `J`: consecutive applicable inactivity ticks, measured or explicitly modeled;
- raw occurrence counts, dependence-group totals, and rolling credited totals;
- last consolidation opportunity.

For each canonical route/context, store `E ∈ [-0.25,+0.25]`, the contextual exposure adjustment. Initialize all values to zero. Use fixed-point integers at scale `1,000,000`, rounding toward zero after each operation. Replay requires exact equality; reject nonfinite or out-of-range imported values.

### Development contribution

For an admitted target `i` in a source-role pool:

```text
pool_share[i] = 0.08 / admitted_distinct_target_count
proposed_D[i] = pool_share[i] × dependence_factor
```

Apply the lifetime group, induced, rolling, and per-opportunity caps with deterministic content-ordered remainder handling. Then:

```text
A' = min(1, A + D)
```

Consolidation occurs only when `D > 0`, the group has not already consolidated this target, and at least four relevant opportunities have elapsed since the last consolidation except the first contribution:

```text
S' = min(1, S + 0.25 × D)
```

Known reinjection-derived support never consolidates.

### Observation and retention order

1. Verify operation identity, permissions, source masks, and pinned state.
2. Determine whether the operation is new, duplicate, unresolved, or an explicit modeled advance.
3. Determine covered monitored targets and `present`, `absent`, or `unknown` status.
4. Advance `G`, `r`, and the rolling window exactly once where applicable.
5. Deduplicate occurrences and resolve dependence.
6. Compute contributions and caps.
7. Apply `D` and eligible consolidation.
8. Apply retention only for measured absence or modeled advance.
9. Apply separately accepted contextual consequences.
10. Persist every input, reason, coverage result, delta, and before/after state.

| Case | `G` | `r/window` | `U` | `J` and numerical state |
|---|---|---|---|---|
| Covered relevant support | +1 | +1 | Reset | Apply credit/consolidation; no retention |
| Support observed but cap exhausted | +1 | +1 | Reset | `D=0`; no retention; record `support_seen_credit_capped` |
| Known reinjection | +1 | +1 | Reset | Apply dependent credit if available; no absence retention |
| Covered relevant absence | +1 | +1 | +1 | Apply inactivity retention |
| Failed, excluded, or uncertain assessment | +1 only when terminal | No | Unchanged | Freeze numerical state; record `measurement_unknown` |
| Duplicate, retry, or cache lookup alone | No | No | Unchanged | Idempotent no-op |
| New experience using cached annotations | +1 | +1 if covered/relevant | Based on measurement | Credit uses original ancestry |
| Unrelated or hard-excluded target | Experience may complete | No | Unchanged | No aging of that target |
| Explicit authorized advance of `k` ticks | +k | +k for pinned set | Unchanged | Modeled retention; never observed absence |

For each measured absence or modeled advance tick:

```text
A ← floor_fixed(A × 7/8)
if J >= 8 and the target is not an inactivity-exempt warning:
    S ← floor_fixed(S × 255/256)
```

Presence, including cap-exhausted presence, resets `J` and applies no retention. Unknown freezes `A`, `S`, `r`, the window, `J`, and `U`. Explicit advance increments `J` and applies the same decay while recording `modeled_advance`; it does not increment `U`.

### Contextual consequence and learned restraint

Unknown outcome produces no consequence transition. An explicitly targeted, attributable contextual assessment contributes `q ∈ {-1,+1}`:

```text
E' = clip(E + 0.05 × q, -0.25, +0.25)
```

The signed contribution pool is shared across targeted routes. Maximum absolute contribution is `0.10` per originating exposure and `0.10` per route/context over eight relevant opportunities. Positive and negative awards do not cancel to free cap budget. Retractions and corrected attribution trigger deterministic rebuild from the earliest affected assessment.

The learned exposure gate is:

```text
base  = mean_over_edges(0.6 × A + 0.4 × S)
score = base + E

exposure_eligible =
    hard_gates_pass
    AND current_relevance_passes
    AND E > -0.25
    AND score > 0
```

`E = -0.25` closes contextual restraint. A closed route is omitted even when it is the only candidate or when `A` and `S` are saturated. The association, evidence, and provenance remain intact. Support recurrence cannot reopen it. Only permitted positive contextual evidence or an assessment retraction/correction can move `E` above `-0.25`; recovered eligibility still requires positive score and all hard gates.

### Selection and exploration

`fixed-v2` uses no learner state: hard gates, query coverage, directness, and canonical content determine selection. `learned-v1` applies the exposure gate, then ranks exposure-eligible routes by query coverage, learned score, directness, and canonical content. No-memory supplies no route or identity payload while preserving common task instructions.

Selection is separate from serialization:

```text
considered → eligible → selected → serialized/supplied → observed expression → consequence
```

The final request is authoritative. A route dropped for the 1,536-byte memory budget is not “applied” and earns no exposure credit.

Exploration is restricted to the highest query-coverage tier. Let `L` be exposure-eligible routes and `H` the highest-coverage routes in `L`.

- If the next opportunity `n=G+1` is not divisible by four, use ordinary ranked selection.
- If `n` is divisible by four and `H` contains at least three routes, retain the highest-ranked route in slot one and rotate slot two through the canonical remainder of `H`.
- If `H` contains fewer than three routes, use ordinary ranked selection and record `exploration_not_applicable_insufficient_highest_tier`.

Exploration never bypasses positive-score eligibility, permissions, quarantine, relevance, current instructions, or suppression. Administrative identifiers and insertion order never affect ordering.

## 5. Worked traces and required learner tests

### Weak association

For one route with `A=.020000`, `S=.005000`, `E=0`, score is `.014000`; it is supplied. One permitted negative assessment gives `E=-.050000`, score `-.036000`, and the actual payload becomes `{"routes":[]}`. A later valid `+.050000` assessment restores `E=0`, score `.014000`, and the exact prior route JSON is supplied again.

### Established association

For `A=.400000`, `S=.100000`, base score is `.280000`:

| Position | Delta | `E` | Score | Payload |
|---:|---:|---:|---:|---|
| Before correction | — | 0 | .280000 | route |
| 1 | −.05 | −.05 | .230000 | route |
| 2 | −.05 | −.10 | .180000 | route |
| 9 | −.05 | −.15 | .130000 | route |
| 10 | −.05 | −.20 | .080000 | route |
| 17 | −.05 | −.25 | .030000 | `{"routes":[]}` |
| 25, valid recovery | +.05 | −.20 | .080000 | route |

Intervening capped support is present but earns no extra credit and no absence retention. It cannot keep the route exposed after `E` closes restraint.

### Saturated association

With `A=1`, `S=1`, five valid negative assessments move `E` from `0` to `-.25`; the score remains `.750000`, but the actual payload is empty. Further dependent recurrence remains empty. A valid `+.05` recovery opens restraint at `E=-.20`; the route becomes eligible again.

### Mixed-coverage exploration

For routes A/B/C with query coverage 2 and D with coverage 1, at an exploration coordinate the slot-two choice rotates among B/C. D cannot enter the exploration slot even if its score exceeds theirs. If C becomes contextually closed and the highest tier contains only A/B, ordinary ranked selection applies; D is not mislabeled as exploration.

Tests cover one, two, and more-than-two routes; exact zero; weak/established/saturated support; correction without a persistent directive; recovery; hard directives; quarantine; payload truncation; mixed coverage; administrative-ID independence; and host-independent payload assertions. They never require a particular frozen-host sentence.

## 6. Storage, publication, migrations, and recovery

Add schema 6 in P2.1 and schema 7 only for P2.2-specific records.

Schema 6 records:

- `development_operations`: operation, episode, pinned manifest/configuration, opportunity, stage, terminal disposition;
- immutable semantic bindings: canonical target, graph/local key, resolver version, originating interpretation/source links;
- `development_observations` and typed links: origin, target, context, coverage, status, dependence, actual exposure, assessor version;
- `learner_updates`: unique application coordinate, ordered inputs, cap reasons, deltas, before/after snapshots;
- learner snapshots/values: graph binding, learner configuration, `G`, coverage, policy/authority version, canonical digest;
- durable semantic attempts: exact request, persisted result, usage, validation, and disposition.

Schema 7 adds outcome assessments, quarantine authority events, and identity review operations/attempts. Manifests gain nullable learner snapshot/configuration, binding version, opportunity, coverage, and authority revision fields. Inspection distinguishes every counter.

The lifecycle is:

1. Reserve and persist exact response intent and maximum output allowance.
2. Generate outside a database write transaction.
3. Persist the returned response before validation; accept the episode once.
4. Persist extraction/assessment requests and returned results before validation.
5. Resolve stable bindings and compute the pure learner.
6. In one `BEGIN IMMEDIATE` transaction, recheck manifest, permissions, authority, and stale base; publish interpretation, observations, graph, learner update/snapshot, revisions, and current tip.
7. Commit; then write external laboratory completion evidence.

A crash before final commit leaves the previous coherent tip. A crash after commit returns the existing receipt. `STARTED` without durable result is `UNCERTAIN`, retains its reservation, and is never automatically regenerated. Accepted replay is idempotent. Old checkpoints remain byte-identical. Forks inherit permitted learner state, age, dependence ancestry, and coverage without earning parental evidence again; child revisions begin at zero and diverge independently.

Migration requires an explicit backup and validation. Legacy material receives `learn=false`; new instances must explicitly request learning:

```text
mneme --store private/a.sqlite3 instance create \
  --development-enabled --learning-enabled --host gemma-deepinfra
```

Historical replay requires separate authorization and source scope. Revocation/quarantine invalidates learned scores, caches, managed snapshots, and inherited derivatives. Frozen reads block on authority drift instead of silently becoming another treatment. Unmanaged exports remain outside enforceable erasure guarantees.

## 7. Feedback, restraint, identity, and modes

Current-turn constraints, persistent directives, and learned consequences remain separate:

1. A current constraint gates the current response immediately.
2. A persistent directive suppresses its scoped target until revoked.
3. An attributable assessment changes `E` through the bounded rule.

Natural-language feedback may propose a target, but quoted, fictional, third-party, ambiguous, sarcastic, or unconfirmed material cannot acquire operator authority. Silence creates no consequence. Factual contradiction can quarantine or challenge a proposition; it is not merely a preference penalty.

Identity follows:

```text
proposal → isolated review → accepted / rejected / unchanged / uncertain
```

Returned identity requests/results persist before validation and are charged. Model proposals, operator renames, aliases, quotations, role-play, and factual self-description remain distinct. Accepted changes atomically update self-view while preserving lineage identity and old names. Name values never seed sampling or traits. The pilot masks identity projection in behavioral comparisons.

Independent controls govern recording, interpretation, learning, readout, identity projection, and session carryover. `observe` may read declared memory without learning. `evaluate` uses only a frozen boundary and performs no developmental writes or clock/cache updates. Existing Phase One contracts remain learning-disabled after upgrade.

Ablations are one pipeline with switches:

- full source-aware development;
- external-input-only, masking model outputs before graph/observation/replay/consequence paths;
- frequency-only, counting genuine admitted occurrences without consolidation, consequence, or retention;
- no-consequence, retaining development/retention but disabling `E` updates;
- fixed-v2 and no-memory readouts.

Replay of fixed history, same-snapshot readout comparison, and prospective alternative development remain distinct claims.

## 8. Fixtures, split policy, and pilot contract

### Development fixture

Use two siblings and 24 external episodes per sibling, with the same ordered fixture and fresh prompt-local context. The fixture includes three repeated-support families and competition:

- labeled workshop bins and finding parts;
- garden mulch and retained soil moisture;
- slow music practice and note accuracy;
- transparent drawers as a competing parts route;
- explicit current-input constraints and two contingent contextual assessments.

The exact 24 inputs are frozen in the pilot fixture artifact. Episodes 1, 4, 7, 10, 13, 16, 19, and 22 cover the parts family; 2, 5, 8, 11, 14, 17, 20, and 23 cover garden moisture; 3, 6, 9, 15, 18, 21, and 24 cover practice/accuracy. Episodes 5, 8, and 11 are deliberate dependent recurrence, not independent discoveries. Episodes 7, 13, 17, and 18 are separately declared event roots. Episode 12 explicitly suppresses a practice reminder for that answer only.

Relevant positions are per-edge, not global episode numbers. The fixture must record `r`, coverage, and dependence for each target. Twelve unrelated episodes cannot become twelve relevant opportunities.

### Evaluation split

Remove direct follow-ups from the paid disjoint evaluation bank. Use twelve distinct families: chart interpretation, paper deformation, measurement precision, map scale, sound reflection, baking gas, translation ambiguity, shadow geometry, board-game coordination, meeting decisions, tidal timing, and library classification. The exact prompts are frozen in the evaluation dataset.

The existing normalized-content and scenario-family split validator remains unchanged. Direct follow-up examples may be retained as engineering recall fixtures only under a separately named non-pilot contract. They are not unseen generalization probes. The sealed assessment bank is untouched.

### Coverage matrix

| Mechanism | Deterministic fixture coverage | Live pilot status |
|---|---|---|
| Separated support/consolidation | Same target at separated `r` positions | Intended, subject to valid extraction |
| Dependent cap | Garden recurrence and replay ancestry | Intended |
| Measured non-recurrence | Covered monitored absences | Intended |
| Competing routes | Bins versus transparent drawers | Intended |
| Contextual positive/negative consequence | Prespecified practice targets | Conditional on actual exposure |
| Exposure recovery | Later support after restraint | Possible, not forced |
| Long retention | Eight measured absences or modeled advance | Not guaranteed in the pilot |
| Unknown/no own-output credit | Complete accounting and source masks | Measured, never manufactured |

### Pilot

Scientific identity is `p2-developmental-pilot / contract_revision 1`. Use one clean learning-enabled checkpoint, two siblings, 24 external episodes each, common policy/host/order, separate orchestration streams, and provider-managed sampling labels. At initial and final checkpoints inspect source quality, semantic decisions, selected/serialized/applied routes, update terms, correction handling, concentration, alternatives, factual/instruction failures, and no-influence readouts.

Use one conservative prospective parameter setting. A second setting changes the developmental pool from `.08` to `.12` while retaining all caps and is replay-only sensitivity analysis unless separately authorized. It must never be selected by transcript charisma, name, divergence, or personality label.

## 9. Production-equivalent assessor qualification and budget

Qualification occurs after the executable pipeline passes offline validation and before any pilot call. It uses exactly three separately reserved calls, the production request/response structure, the same enum vocabulary, source roles, monitor fields, validation, prompt version, and settings.

| Case | Required result |
|---|---|
| Q1: “Pulling the lever released the latch.” Candidate causes latch release; model output repeats it | Supported relation with quotations; current-input echo attribution; covered absence for an unrelated monitor |
| Q2: Rain-jacket source plus supplied memory “Turning the handle raises the shade” and dependent model output | Rain-jacket direction unsupported; shade relation present and `exposure_linked`; recorded memory ancestry preserved |
| Q3: “Turning the dial did not stop the ticking; the sound continued,” with model-output slot unavailable | Candidate is `present` / `contradicted` / `negated` with a negating quote; monitor requiring unavailable source coverage is `unknown`, never absent |

Qualification requires all monitor rows, complete/declared coverage, required evidence where text exists, and valid dependence references. A missing row, false coverage, malformed response, wrong classification, or attribution conflict stops qualification. There are no retries, repairs, prompt changes, or replacement calls. Qualification creates no pilot state and is not an independent pilot observation.

### Proposed ceiling

| Role | Calls | Output cap | Maximum output tokens |
|---|---:|---:|---:|
| Assessor qualification | 3 | 1,536 | 4,608 |
| Development responses | 48 | 256 | 12,288 |
| Initial extraction | 48 | 1,536 | 73,728 |
| Development assessment | 48 | 1,536 | 73,728 |
| Frozen readouts | 144 | 192 | 27,648 |
| Pooled extraction repairs | 8 | 1,536 | 12,288 |
| **Total proposed ceiling** | **299** | — | **204,288** |

Scheduled calls excluding the finite repair pool: 291. One extraction repair maximum per interpretation; eight repairs total. No response, evaluation, or identity allowance is hidden. The learner itself uses zero inference calls.

Retain the original 90-second per-call timeout, ten-hour active execution limit, 1 GiB private artifact limit, 32 KiB serialized input bound, durable reservation states (`RESERVED → DISPATCHED → RETURNED|FAILED|UNCERTAIN`), retained reservations for uncertain outcomes, and explicit actual-versus-estimated usage/cost. These 299 calls are proposed, not authorized; no Phase One allowance carries forward.

## 10. CLI, artifacts, and inspection

Extend the existing CLI without creating a workflow platform:

```text
mneme --store private/a.sqlite3 learner inspect --json
mneme --store private/a.sqlite3 learner explain --target EDGE_OR_ROUTE
mneme --store private/a.sqlite3 learner replay --verify
mneme --store private/a.sqlite3 learner rebuild --reason ASSESSMENT_ID
mneme --store private/a.sqlite3 learner advance --context CONTEXT --steps 8
mneme --store private/a.sqlite3 feedback propose --file feedback.json
mneme --store private/a.sqlite3 feedback accept PROPOSAL_ID
mneme --store private/a.sqlite3 identity propose --name NAME
mneme --store private/a.sqlite3 identity review PROPOSAL_ID --host fake
mneme --store private/a.sqlite3 quarantine add --target TARGET --reason TEXT
mneme --store private/a.sqlite3 quarantine release RECORD_ID
mneme experiment validate configs/p2-pilot.json
mneme experiment preflight configs/p2-pilot.json --host gemma-deepinfra
mneme experiment run create configs/p2-pilot.json --lab PRIVATE_LAB --run-id RUN
mneme experiment run execute RUN --lab PRIVATE_LAB --host gemma-deepinfra
mneme experiment run resume RUN --lab PRIVATE_LAB --host gemma-deepinfra
mneme experiment developmental report RUN --lab PRIVATE_LAB
```

`learner advance` explicitly identifies modeled temporal intervention. Replay and report commands make no provider calls.

Artifacts remain in the existing experiment layout, with separate developmental stores and evaluation artifacts:

```text
artifacts/experiments/<experiment>/<run>/
  experiment.json
  preflight.json
  run-manifest.json
  development/
  evaluation/
  qualification/
  receipts/
  summary.json
```

The inventory includes exact requests/results, qualification classifications, source/interpretation links, exposure payloads, monitor coverage/status, dependence/cap ledgers, per-edge relevant timelines, feedback applicability, before/after snapshots, reservations, usage, failures, unknowns, and sanitized human-readable evidence. Missing or wrong-but-valid artifacts fail closure.

## 11. Implementation packages and stop gates

### P2.1 — Replayable learner and trustworthy inputs

Implement the foundation repairs first inside P2.1: instruction composition, corrected fixed/no-memory comparator, actual-exposure traces, stable semantic bindings, direct source/interpretation provenance, production-equivalent assessor contract, learning opt-in, pure learner, and atomic interpretation/learner publication.

Add schema 6, migration/recovery tests, source/dependence observations, exposure threshold, and exact replay. Demonstrate with FakeHost that a permitted model-origin observation changes learner state and a subsequent eligible exposure, while unknown outcome remains unknown. Run the full offline suite, Ruff, strict mypy, install smoke, and CI. Publish `p21-prerequisites`, `p21-learner-traces`, `p21-own-output`, `p21-publication`, and `p21-semantic-review` evidence.

Stop feature work, audit actual records and payloads, fix in-scope defects, append `bible.md`, commit and push, verify remote SHA/CI, and record P2.1 status before P2.2.

### P2.2 — Restraint, retention, identity, and recovery

Enable retention and modeled advance, contextual consequences, quarantine/rebuild, reviewed identity proposal/review, failed identity-result durability, fork inheritance, revocation, and schema 7. Execute all six dynamics scenarios as deterministic tests. Prove weak/established/saturated restraint, recovery, competing routes, hard directives, actual payload changes, and independent children.

Publish `p22-six-scenarios`, `p22-feedback-rebuild`, `p22-identity`, `p22-fork-revocation`, and `p22-recovery` evidence. Stop, audit, commit/push, verify CI, and accept P2.2 before P2.3.

### P2.3 — Qualification, bounded pilot, and candidate freeze

Run the fixed three-call production-equivalent assessor qualification first. If it passes, run the separately authorized 299-call pilot ceiling with two siblings, 24 episodes each, twelve disjoint probes, fixed readouts, and finite repairs. Resume only from durable coordinates; do not restart for an inconvenient result.

At initial/final checkpoints inspect actual exposure, semantic integrity, update terms, concentration, alternatives, corrections, competence, no-memory/fixed/learned readouts, and state invariance. Generate replayable reports without model calls.

## 12. Tests and acceptance criteria

### Tests

Add tests for:

- fixed-point learner initialization, caps, saturation, precision, duplicate/no-op, and replay;
- weak/established/saturated contextual restraint, exact serialized payloads, recovery, hard directives, and competing routes;
- highest-coverage-only exploration and mixed-coverage exclusion;
- observed presence versus capped presence versus measured absence versus unknown versus modeled advance;
- current-input echo, replay dependence, mixed-origin output, cache reuse, and overlapping-root caps;
- stable semantic identities, alias bridging, split/retraction rebuild, direct source provenance, and no UUID/path influence;
- instruction preservation, actual-exposure traces, fixed/learned/no-memory policy parity, and no hidden session carryover;
- permission migration, quarantine/revocation through caches/forks/frozen readers, and child independence;
- failed identity-result persistence, reviewed transitions, and no name-derived traits;
- subprocess interruptions before/after response, extraction, atomic publication, and external acknowledgment;
- reservation-before-dispatch, retained uncertain charges, finite repairs, completed-probe reuse, and wrong-coordinate rejection;
- exact split family validation, qualification failure stopping pilot dispatch, and human-readable evidence inventory;
- no evaluation clock, learner, manifest, cache, or exposure updates.

Ordinary CI remains network-free. FakeHost establishes mechanics; the three qualification calls and pilot calls are explicit acceptance actions, never ordinary CI.

### Three-dimensional acceptance

**Engineering acceptance** requires correct arithmetic and actual exposure, complete provenance/accounting, bounded updates, exact replay, valid permissions, atomic recovery, evaluation isolation, and all required artifacts.

**Pilot adequacy** requires at least 44 of 48 structurally valid extractions after permitted repair, at least 12 admitted semantic relationships, one separated-support/consolidation opportunity, one genuine competing-route opportunity, complete counts of measured absence/dependence/correction/exposure, and honest own-output coverage. Zero qualifying own-output observations is a pilot subanalysis limitation, not automatically a learner code failure.

**Research outcome** may be positive, weak, convergent, negative, or inconclusive. A competent host response failure is a competence observation when inputs were delivered correctly. An unsupported relationship admitted by policy is an integrity failure. A correct quarantine is successful negative handling.

| State | Disposition |
|---|---|
| Engineering pass, adequate pilot, any honest research outcome | P2.3 may pass with the recorded result; release remains non-individuality claim |
| Engineering pass, inadequate central coverage | `COMPLETED_INADEQUATE`; no automatic release/tag; human decides whether to authorize further study |
| Interrupted/uncertain | Paused or blocked; resume permitted coordinates only |
| Integrity defect | Fail affected gate; preserve evidence and repair under one bounded correction policy |
| Qualification failure | Pilot does not start; publish diagnostic evidence |

Disappointing behavior does not authorize indefinite tuning or resampling. Missing evidence never counts as success.

## 13. Release, scope, and open decisions

Only after all three packages pass their stop/audit/push gates may the implementation update package metadata to the proposed unused `0.2.0` and create `mneme-phase-two-developmental-runtime-preview`. Recheck tag/version availability before release. Preserve `mneme-phase-zero`, `mneme-phase-one-graph-preview`, all receipts, and all failed attempts unchanged.

Phase Two does not implement base-weight updates, LoRA, hidden-state hooks, neural route fields, a broad ontology rewrite, a reward model, Phase Three cohorts/statistical individuality claims, a new provider campaign, distributed workers, a dashboard, multi-user development, cryptographic identity, encryption-at-rest, or a secrets platform.

The material decisions settled by this approved plan are the strict positive-score exposure gate, contextual closure at `E=-.25`, zero extra credit for current-input echoes and unresolved/conflicting attribution, measured-versus-modeled retention, highest-coverage exploration, revised fixtures/splits, production-equivalent three-call qualification, and the 299-call/204,288-token proposed ceiling. Any change to those decisions requires a new reviewed amendment.

The final scientific result may show strong differentiation, weak effects, convergence, or no detectable effect. The implementation is complete only when the runtime is correct, attributable, resumable, and honest about which of those outcomes occurred.
