# MNEME P0.3 — Experiment contracts and experimental isolation

Status: approved plan; implementation complete and accepted under the documented FakeHost receipt.

This plan is based on the accepted P0.2 baseline and the current Model Instance
Development Specification, Development Roadmap §P0.3, and individuality/identity
research amendment. P0.3 establishes laboratory controls; it does not implement
learning, associations, personality, self-model development, or behavioral
individuality measurement.

## 1. Proposed architecture

P0.3 compiles a versioned scientific contract into an immutable, inspectable study
plan. Experiment records live outside per-lineage P0.2 SQLite databases. Use standard
library Python, JSON specifications, JSONL fixtures, and filesystem artifacts. Do not
add a laboratory database, workflow engine, scheduler, or general experiment runner.

```text
experiment specification + fixture manifests
                 |
                 v
validate and preflight
  splits, subjects, conditions, checkpoints, seeds,
  host capabilities, fingerprints, budgets
                 |
                 v
immutable prepared run directory
  contract, bindings, plan, receipts, private checkpoint copies
                 |
                 v
bounded FakeHost isolation check
  read-only checkpoint view -> separate evaluation artifacts
                 X
          no developmental writeback
```

The full developmental schedule and real-host study execution remain P0.4. P0.3 may
execute only a small FakeHost isolation primitive needed to prove the boundary.

P0.2's checkpoint reader requires two narrow guards before it can serve as this
boundary: bind a reader to the requested checkpoint's own descriptor, lineage,
revision, and manifest; and reject published checkpoints through public writable-store
and developmental-service entry points. Read-only opening must perform no initialization,
migration, recovery, or directory-creation writes. These are focused boundary fixes,
not a P0.2 redesign.

## 2. Operational definitions

| Term | Definition |
|---|---|
| **Experiment** | A scientific contract in a named series. Its human/scientific identity is the declared `name + contract_revision`. |
| **Contract content digest** | SHA-256 of the canonical serialized contents of one contract revision. It identifies exact immutable contents and provides integrity; it does not replace the scientific series identity. |
| **Experiment run** | One preparation/execution attempt of one exact contract revision, with recorded software, host, dataset, checkpoint, and subject bindings. |
| **P0.2 RunManifest** | Existing provenance for one developmental generation. P0.3 references it without changing its meaning. |
| **Subject** | A scientific position bound to a lineage and exact starting checkpoint. Its numeric slot is separate from administrative identifiers. |
| **Sibling family** | Subjects sharing an exact starting checkpoint. This is an experimental relation, not another identity. |
| **Cohort** | Subjects sharing declared external developmental sequence and matched execution policies. |
| **Condition** | The explicitly permitted treatment differences, initially external input sequence and declared sampling arrangement. |
| **Material partition** | Engineering fixtures, learner-pilot material, or sealed assessment material. |
| **Dataset role** | Development or evaluation, distinct from material partition. |
| **Scenario family** | A curator-declared group containing one scenario and its known variants/near-duplicates. |
| **Evaluation view** | A private copy of a published checkpoint opened through a read-only interface. |
| **Study plan** | Resolved schedules, assignments, seeds, checkpoint bindings, and resource accounting produced before calls. |
| **Isolation check** | A bounded FakeHost probe against an evaluation view that writes only separate laboratory artifacts. |

The scientific identity example is `shared-input-control / revision 3`. Its SHA-256
content digest identifies the exact serialized revision approved and executed. Changing
scientific content requires a new contract revision and therefore a new digest. Run
UUIDs, filesystem paths, and content digests must never substitute for the declared
scientific identity or enter model-visible prompts and random seeds.

## 3. Experiment specification

Use JSON with explicit versioned dataclasses and reject unknown fields, duplicate keys,
non-finite numbers, unsupported schema versions, and inconsistent references.

Required sections are:

* identity: `schema_version`, human name, `contract_revision`, purpose;
* scientific contract: permitted differences, fixed controls, history contents, and
  evidence sought;
* fixture-pack version and digest;
* exact checkpoint ID, lineage, revision, manifest, file digest, and locator;
* subject slots, cohorts, conditions, and starting checkpoints;
* development and evaluation datasets, ordering, and context policy;
* host selection, required capabilities, safe fingerprint pin, and revision policy;
* common instructions and generation settings;
* master seed and seed-derivation version;
* call, token, time, and optional cost budgets;
* artifact location and software/contract versions;
* explicit storage permission for experimental content.

The canonical serialization includes the declared name and contract revision. The
content digest is calculated after canonicalization and is stored alongside, never in
place of, those identity fields. A rerun of an unchanged contract retains the same
scientific identity and content digest while receiving a distinct administrative run
record.

Example shape:

```json
{
  "schema_version": 1,
  "name": "shared-input-control",
  "contract_revision": 3,
  "purpose": "Verify controls and isolation without learning.",
  "stage": "engineering",
  "contract": {
    "may_differ": ["development_sampling"],
    "fixed": ["starting_checkpoint", "host", "external_sequence", "context_policy", "evaluation_settings"],
    "history": "external_input_and_actual_output_only",
    "evidence": "infrastructure invariants; no individuality claim"
  },
  "fixture_pack": {"path": "fixtures/pack.json", "sha256": "<digest>"},
  "subjects": [
    {"slot": 0, "start": "checkpoint-a", "cohort": "shared", "condition": "common", "development_sampling_slot": 0},
    {"slot": 1, "start": "checkpoint-a", "cohort": "shared", "condition": "common", "development_sampling_slot": 1}
  ],
  "conditions": {"common": {"development_dataset": "engineering-development", "ordering": "listed", "update_policy": "record_only"}},
  "evaluation": {"dataset": "engineering-evaluation", "repetitions": 2, "pair_seeds_across_subjects": true},
  "host": {"backend": "fake", "fingerprint_sha256": "<digest>", "requires": ["text_generation", "seed_control"], "revision_requirement": "known"},
  "randomization": {"master_seed": 20260918, "derivation_version": "mneme-seeds-v1"},
  "budgets": {"max_model_calls": 14, "max_input_tokens": 4096, "max_output_tokens": 448, "max_seconds": 60},
  "storage_allowed": true
}
```

## 4. Dataset and split model

Fixture packs contain a manifest and JSONL records. Each record has a stable record ID,
explicit ordinal, scenario-family ID, ordered model-visible messages, material
partition, and dataset role. Manifests pin format, hashes, record count, ordered
content digest, and family membership.

The roadmap's three partitions are retained: engineering fixtures, learner-pilot
material, and sealed assessment material. Each is additionally marked development or
evaluation. A file, normalized prompt, or scenario family may not cross a forbidden
boundary. Reject aliases/symlinks, duplicate content under different IDs, trivial
whitespace variants, missing family annotations, and changed files after hashing.

Normalize Unicode and line endings for duplicate checks while preserving original
generation content. Known near-duplicates remain together by declared scenario family.
Automated semantic similarity detection is deferred; P0.3 must not claim to detect
unknown paraphrases.

Listed order is the default. Shuffling is explicit and persisted in the resolved plan.
Shared-input cohorts receive the same order; condition-specific datasets are explicit.

## 5. Random streams

Derive stateless, domain-separated seeds with versioned HMAC-SHA-256 over canonical,
length-unambiguous inputs, returning nonnegative 63-bit values where a host requires an
integer seed:

```text
derive(master_seed, domain, explicit_scientific_coordinates)
  development_generation
  evaluation_generation
  condition_assignment
  dataset_ordering
```

Development coordinates are sampling slot, episode ordinal, and repetition. Evaluation
coordinates are probe ordinal, checkpoint boundary, and repetition; subject slot is
excluded for paired comparisons. Assignment and ordering use explicit numeric blocks.
Lineage IDs, experiment/run UUIDs, names, timestamps, paths, and checkpoint identifiers
never enter seed material. Extraction, route exploration, environment simulation, and
evaluator streams remain documented future domains without placeholder contracts.

Assignments use explicit lists or balanced permutations in a declared block. Persist
the resolved result. A retry cannot shift later streams. Independent replication needs
explicitly different seed material or sampling slots; changing a run UUID is not enough.

Controlled orchestration is reproducible even when model sampling is not. A host may
be called controlled only when it advertises seed control. FakeHost may prove matched
fixture output. A real seed-capable host still requires measured repeatability. A
provider-managed host such as DeepInfra may pass text-generation preflight but must
fail a seed-control requirement and must be labeled uncontrolled sampling.

## 6. Capability and fingerprint preflight

Preflight performs no model calls. It validates the contract, fixture boundaries,
checkpoint identity and copy permission, subject/condition relationships, host
capabilities, complete safe fingerprint, assignments, ordering, and budgets before
producing a machine-readable report and study plan.

Record canonical upstream model identity, actual execution fingerprint, capability set,
hosted revision knowledge, requested settings, software commit, and contract versions
separately. A changed safe fingerprint invalidates the binding; no silent downgrade is
allowed. Unknown hosted revision may be explicitly permitted, but never satisfies a
known-revision requirement. Model-name equality does not prove hosted/local weight
identity.

## 7. Budgets

Expand the finite schedule before calls:

```text
development calls + evaluation calls + declared isolation checks
```

Enforce total calls, input/output token ceilings, per-call output limits, elapsed time,
and isolation allowance. Report exact counts, conservative bounds, estimates, and
unknowns separately. If a defensible tokenizer or host context bound is unavailable,
preflight cannot pass a hard token ceiling. Character heuristics are estimates only.

Optional cost metadata records currency, rates, source, and observation date. Unknown
pricing cannot satisfy a hard cost limit. No automatic pricing lookup or billing system
is introduced. Provider timeouts bound local waiting but cannot promise cancellation of
an already-running remote request. The roadmap's 4,000-call review cap remains a
planning ceiling, not paid-execution authorization.

## 8. Evaluation isolation

Use a private, staged copy of each published checkpoint. Verify checkpoint ID, lineage,
revision, manifest, file digest, and copy permission before publication. Evaluation
receives a `FrozenEvaluationView`, not a writable lineage store or `ContinuityService`.
Its interface exposes immutable metadata and records only; it exposes no SQLite
connection, migration, repair, prepare, or acceptance method.

Each probe gets a fresh request and reset immediate context. Probe answers are not fed
to later probes. Results are written only to a separate artifact writer. Evaluation
does not create episodes, revisions, manifests, checkpoints, pending operations,
recency/access updates, self evidence, or random-stream changes.

Capture checkpoint bytes, logical database content, active lineage/revision/manifest,
and directory inventory before and after measurement. Compare the developing working
lineage as well. The accepted-history digest is not sufficient by itself and does not
claim behavioral equivalence. This is structural protection against supported API
writeback, not a security sandbox against arbitrary code with filesystem privileges.

## 9. Lifecycle and resumability

An editable specification is a draft. Validation does not register it. Run creation
freezes its canonical content, human/scientific identity, and content digest. Any
scientific edit creates a new contract revision and digest; an administrative run UUID
does not create a new experiment revision.

A prepared run is published only after successful preflight. P0.3 does not implement a
full `RUNNING`/`COMPLETE` study lifecycle; inspection reports `PREPARED`, binding
validity, and isolation-check results. Changed dependencies fail verification rather
than rewriting history.

Isolation checks use append-only records:

```text
STARTED -> RESULT or FAILED
        -> UNCERTAIN after recovery without a terminal record
```

Existing successful checks return their receipt. Conflicting IDs fail. Uncertain calls
are not regenerated automatically; replacements use new IDs and explicit references.
Resume reconciles local records and bindings only. Full schedule execution is P0.4.

## 10. Storage, artifacts, and privacy

Use immutable manifests and staged publication under one local laboratory writer lock:

```text
<lab-root>/experiments/<series-name>/revisions/<contract-revision>/runs/<run-id>/
  experiment.json
  run-manifest.json
  preflight.json
  study-plan.json
  bindings.json
  inputs/
  snapshots/
  evaluation/<check-id>/started.json
  evaluation/<check-id>/result.json
  receipts/
```

The run manifest also stores `experiment_name`, `contract_revision`, and
`contract_sha256`. The path is only a locator and is never scientific identity. A run
UUID distinguishes attempts of the same contract revision.

Inputs and checkpoint copies may contain sensitive content. Sanitized receipts contain
hashes, counts, statuses, and safe provenance, never prompts, answers, tokens, headers,
environment dumps, or arbitrary provider metadata. Runtime artifacts remain out of Git.
Atomic same-filesystem publication makes staging invisible; identical retries return
the existing run and conflicting intent fails. The complete run directory is the
portable backup unit.

## 11. CLI and modules

```text
mneme experiment validate SPEC --json
mneme experiment preflight SPEC --json
mneme experiment run create SPEC --lab PATH --run-id UUID --json
mneme experiment run inspect UUID --lab PATH --verify --json
mneme experiment run resume UUID --lab PATH --json
mneme experiment check-isolation UUID --lab PATH --subject-slot 0 --probe-ordinal 0 --repetition 0 --check-id UUID --json
mneme experiment artifacts UUID --lab PATH --json
```

There is no full `experiment run execute` command in P0.3. Existing host and state
commands remain unchanged.

Likely modules are `src/mneme/experiments/contracts.py`, `datasets.py`, `planning.py`,
`artifacts.py`, and `evaluation.py`, plus focused CLI handlers and tests. Narrow
checkpoint guards belong in existing state reader/storage/service/snapshot modules.
No P0.2 database redesign or future-mechanism placeholder module is needed.

## 12. Tests

Use FakeHost for all ordinary CI and integration tests. Test contract parsing/versioning,
canonical identity and immutability; split overlap, duplicate IDs/content, aliases,
families, and sealed-material access; listed/shuffled ordering; golden seed vectors,
domain separation, paired evaluation, and administrative-ID independence; compatible
and incompatible capabilities/fingerprints; call/token/cost overflow and unknowns;
checkpoint binding and writable-checkpoint rejection; evaluation writeback attempts;
before/after state invariance; immutable run publication; restart, uncertain checks,
and idempotent retries; artifact sanitization and staging visibility.

Integration must prepare a FakeHost control run, run isolated probes, restart, inspect,
and continue development independently. Deliberately attempt same prompts in both
splits, duplicate files/content, unsupported seed control, budget overflow, changed
specification, writable lineage evaluation, and administrative-ID seed influence.
Real Gemma is optional and not part of ordinary CI; full real-host execution is P0.4.

## 13. Acceptance demonstration

1. Create root A, accept one bounded FakeHost interaction, checkpoint C, and fork B/D.
2. Create disjoint engineering development/evaluation fixtures with scenario families.
3. Define `shared-input-control / revision 3`, bind B and D, and validate it.
4. Print resolved assignments, independent streams, capabilities, fingerprint, and budgets.
5. Publish a prepared run and private checkpoint copies.
6. Run one paired FakeHost isolation check per subject.
7. Verify identical model-visible requests and expected outputs despite different admin metadata.
8. Verify no lineage episode, revision, manifest, checkpoint, pending operation, or seed state changed.
9. Accept one later developmental interaction into B and verify D/evaluation remain unchanged.
10. Demonstrate rejection of split overlap, duplicate content, family overlap, missing seed capability, and budget overflow.
11. Change the contract or checkpoint and show prepared-run reuse is rejected.
12. Restart, inspect, retry a completed check without another generation, and simulate an uncertain interrupted check.
13. Produce machine-readable manifests and sanitized receipts stating infrastructure evidence only.

No real Gemma call is required by P0.3. This demonstrates experimental control, not a
developmental or individuality result.

## 14. Implementation chunks

| Chunk | Goal | Likely files | Acceptance | Dependencies |
|---|---|---|---|---|
| **1. Contract and fixtures** | Versioned specs and split boundaries | `experiments/contracts.py`, `datasets.py`, fixtures | Canonical identity/digest, three partitions, role validation, duplicate/family rejection | explicit implementation authorization |
| **2. Plan and preflight** | Resolve subjects, conditions, seeds, capabilities, budgets | `planning.py` and tests | Stable assignments, truthful host checks, finite plan before calls | 1 |
| **3. Frozen evaluation** | Enforce no-write evaluation and narrow checkpoint guards | `evaluation.py`, existing state boundary modules | Exact checkpoint binding, published checkpoint write rejection, state invariance | 1–2 |
| **4. Artifacts, CLI, recovery** | Durable prepared runs and acceptance evidence | `artifacts.py`, CLI, tests, docs | Restart-safe publication, idempotent checks, interruption receipts, complete demonstration | 1–3 |

Each chunk returns a reviewable candidate and validation receipts. The work queue is
updated only when implementation is authorized; P0.3 is not marked complete by this
plan.

## 15. Risks, decisions, and scope

Blocking implementation decisions are settled: experiments remain outside lineage
databases; name/revision is scientific identity; digest is exact-content identity;
run UUIDs and paths are administrative; checkpoints remain copied and read-only;
FakeHost is the only P0.3 execution primitive.

Codex may choose private helper layout, error-code spelling, fixture wording, and
subprocess mechanics without changing these semantics.

Risks include incomplete semantic duplicate detection, unknown provider revisions,
seed control not proving determinism, sensitive copied conversation data, and
filesystem durability limits. Existing malformed or ambiguous checkpoints fail closed;
P0.3 does not silently repair them.

Deferred questions include semantic duplicate detection, real-host baseline repetitions,
statistical conclusions, advanced randomization, full execution accounting, learning,
extraction, associations, routes, memory influence, self-model, naming, personality,
behavioral scoring, hidden-state intervention, distributed scheduling, and cloud
orchestration.

P0.3 builds the laboratory protocol only. The integrated runner and reproducibility
study remain P0.4; developmental mechanisms remain Phase 1 and later.
