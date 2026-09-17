# MNEME — Development Roadmap
## From specification to a working developmental runtime

**Date:** 2026-09-14  
**Status:** Proposed implementation plan; no milestones are represented as completed.  
**First release:** A local, graph-first developmental runtime with persistent identity and a reproducible twin experiment.  
**Governing design:** *MNEME — Model Instance Development Through Earned Association*, targeted revision of 2026-09-13.  
**Research companion:** *Research Amendment 01 — Developmental individuality, path dependence, and identity*, 2026-09-14.

> Build a system that can carry an instance's history forward, then test what that history does. Do not make the first usable release depend on solving the neural compiler.

## 1. The finish line

The first build is **four substantial phases, numbered 0–3**, following the existing specification's sequence. They end in a tagged research release, not an indefinitely expanding platform. Phase 4 is a separately gated, bounded neural experiment. The specification's Phase 5 remains a parking area, not an automatic commitment.

By the end of Phase 3, the operator should be able to create an instance, let it adopt a name, converse with it, preserve its developmental state, restart it without replaying the conversation, fork it, inspect why a route was used, and run controlled comparisons against the frozen host and simpler memory methods. An experiment can finish with positive, negative, or inconclusive evidence. Software completion does not depend on manufacturing an exciting result.

The graph/text release is a **working research instrument**, not a quiet abandonment of the association-field goal. The neural backend stays in the plan, with a narrow entry gate and a concrete experiment rather than an unspecified promise to visit “weight-land” someday. [S1, §§12, 14–16]

### Milestone map

| Phase | Substantial deliverable | What can be demonstrated | Boundary |
| --- | --- | --- | --- |
| **0 — Contracts and the laboratory** | An executable baseline, durable run records, reproducibility controls, and a measured experiment budget | A real host runs through MNEME; restart, replay, and evaluation isolation work | No developmental algorithm yet |
| **1 — Graph-first wrapper** | A usable conversation loop with source-backed associations and a graph-backed self-model | A name and an association survive a fresh conversation; every use has a trace | Candidate memory, not yet a claim of organic individuality |
| **2 — Self-conditioned development** | One bounded learning rule, restraint, reviewed identity revision, and independent branches | Own outputs can change future state without user approval or fabricated success evidence | One tested learner, not a search for the perfect learning theory |
| **3 — Twin experiment and first release** | A small controlled study, simpler baselines, interpretable reports, and a packaged runtime | Compare base, siblings, ablations, and restored snapshots on unfamiliar prompts | Ship the laboratory and its actual findings |
| **4 — Bounded neural trial** | One model-specific route-vector backend and a fair comparison | Test whether internally applied influence preserves or improves a measured effect | Optional next increment; not a release blocker |

There are **13 core work packages** below: four in Phase 0 and three in each of Phases 1–3. These are integrated implementation chunks, not thirteen documents to write. Each includes working code, tests, a demonstration, and a stopping point.

## 2. Constraints that keep this obtainable

The current spec and amendment govern the scientific intent. The concrete packaging, work packages, pilot sizes, and implementation defaults in this roadmap are **new planning proposals**, not findings from those documents. No specific host, hardware allocation, repository state, or measured throughput is established by the supplied research materials. Phase 0 resolves those practical choices. [S2, §12]

**Default footprint:** One repository, one operator, one machine, one active development writer, one pinned host configuration, and logical instances run sequentially. Separate Python modules are not separate services. Reuse the frozen host rather than loading one model per twin.

**No new hardware purchase is a prerequisite.** Start on available equipment and measure. A small model that can execute the required conversations is a better development dependency than an ideal model awaiting a GPU purchase. Its scientific limitations must still be reported; small-model failure does not settle the hypothesis for every host.

**Limit choice before choice becomes the project.** Try at most two host/runtime configurations in the initial fit check. Implement one real backend plus a fake host for tests. Start with one learner and, after its first diagnostic run, at most one justified revision before recording a result. Those are review boundaries, not a claim that all problems will be solved within them.

**Time is represented as experience, not a mandatory calendar wait.** Use controlled episodes and recorded logical steps for experiments. There is no requirement to wait six real-world months for an instance to “grow up.” Longer horizons are later experiments, not a reason to postpone the first one.

**Paid execution is off by default.** The runner must support call, token, storage, and optional cost limits. Exceeding a limit stops at a recoverable boundary; it does not quietly expand the study. No cloud-credit balance or future free tier is assumed.

**Synthetic/public, non-sensitive fixtures first.** Do not make importing a person's private conversation archive part of the critical path. The initial release is a private local research tool, not a public multi-user service.

---

## 3. Phase 0 — Contracts and the laboratory

**Goal:** Make later observations interpretable before any learned history accumulates. This phase must finish with running software, not just folders and abstract interfaces.

**Source basis:** State and lineage in [S1, §§5, 13 and Appendix A]; reproducibility and experimental controls in [S1, §14]; research cautions in [S2, §10].

### P0.1 — Prove the host and repository can support the experiment

Build an installable Python package, a command-line entry point, a fast test suite, and two host implementations: a deterministic fake and one real, existing conversational model. Keep model execution behind a small `Host` interface with generation, token accounting, fingerprint, and capability reporting. Do not implement hidden-state hooks before a backend needs them.

Run a compact fit check on actual available hardware. The host must produce coherent answers, follow a constrained output request, support the intended context length, and complete a small structured-residue sample with tolerable failure handling. Record load cost, prompt-processing and generation measurements, peak memory where observable, and failure counts. Passing structured JSON syntax is not sufficient: manually inspect whether the extracted material is supported by its source.

Pin the model artifact/revision, tokenizer and chat template, generation settings, quantization if any, runtime dependencies, and relevant execution configuration. Check the chosen model and dependency licenses at selection time. Do not substitute a floating model alias for a reproducible host.

**Default stack proposal:** Python, its SQLite interface, typed records with validation at input/output boundaries, JSON for records, and a small test runner such as pytest. Graph traversal initially uses adjacency structures. A PyTorch/Transformers-backed host is a candidate when it fits the equipment; a different local inference runtime is acceptable through the same boundary. The selection is settled by the fit check, not a framework comparison project.

**Demonstration:** A command generates a real response, saves the exact rendered request and configuration, and produces a machine-readable run record. The test suite still runs without downloading or loading that model.

**Done when:** One host is pinned, the package installs cleanly, the fake-host tests pass, and real-host results and resource measurements are saved. A fake-host-only demonstration does not finish this package.

### P0.2 — Settle the state contract and implement its smallest durable slice

Use the spec's vocabulary rather than inventing parallel concepts:

| Contract group | Minimum distinction to implement now |
| --- | --- |
| `Instance` / `Lineage` | Stable branch identity, parent and fork checkpoint; administrative labels do not steer behavior |
| `Episode` / `SourceRef` | What occurred, who supplied it, permission scope, logical order, and observable source material |
| `RunManifest` / `Checkpoint` | Exact host, policies, snapshot, random-stream plan, and compatible versions |
| `Residue` / `Concept` / `Route` | Validated placeholder records and fixtures; extraction/search become real in Phase 1 |
| `Exposure` / `DevelopmentalObservation` / `Outcome` / `AssociationUpdate` | Applied influence, observed behavior, optional consequences, and state changes remain separate |
| `SelfModel` / `IdentityEvent` | Stable self-reference, unset/adopted name, provenance, and proposed versus accepted transitions |
| `ExperimentSpec` | Corpus versions, split membership, modes, seeds, budgets, and checkpoint schedule |

Implement schema version 1 and round-trip tests; do not perfect every future optional field. Store authoritative state in SQLite. JSONL is an export of committed records, not a second independent source of truth. Put the small pilot's source content in the same managed store to avoid introducing a separate blob-consistency problem immediately.

Use one instance database per working branch and simple, consistent checkpoint copies. The standard Python SQLite interface provides a database backup operation; use a database-aware checkpoint procedure rather than assuming that copying an open database file captures the whole state. [E2]

The controller pins a snapshot for a request. Updates occur after generation. A transaction must either commit an episode's interpreted updates and new current-state pointer together or leave the prior state usable. Persist generated output before retrying interpretation, so an interrupted extractor does not silently replace the developmental event with a different answer. An idempotency key prevents double application.

Maintain two notions of equality: **artifact integrity**, which includes provenance, and **behavioral-state equivalence**, which excludes administrative IDs and irrelevant timestamps. A fork's file hash can differ without its initial behavior changing. Canonical route ordering and tie-breaking must not depend on a random UUID, insertion accident, or wall-clock time.

**Demonstration:** Save a source event, restart, recover it, retry its application, and show that no duplicate state transition occurred. Load a compatible snapshot and reject an incompatible one.

**Done when:** Serialization, recovery, duplicate-event handling, and manifest binding have executable tests. The identity referent exists structurally even though naming behavior is not implemented yet.

### P0.3 — Define the experiment before the learner can influence its design

Create a small versioned fixture pack and an executable experiment configuration. Divide material into **engineering fixtures**, **learner-pilot material**, and **sealed assessment material**. Near-duplicate prompts and variants of the same scenario stay in one split.

Write a short experiment contract covering five matters:

1. **What may differ:** Developmental generation streams and permitted accumulated state; not hidden persona assignments or administrative IDs.
2. **What stays fixed:** Host, common instructions, external corpus within a cohort, update policy, context policy, and paired evaluation settings.
3. **What enters history:** External input, the actual model response, injected-memory dependencies, and explicitly recorded evidence. No hidden reasoning, inferred praise, or evaluator commentary disguised as external experience.
4. **What evaluation cannot do:** Write to the developing branch, refresh its recency counters, advance its decay clock, propose a lasting name change, or influence subsequent probes through earlier probe answers.
5. **What would count as evidence:** Persistent, context-sensitive output tendencies after removal of trivial cues; not merely different strings or a unique name.

Specify independent random streams for development generation, extraction, route exploration, environment simulation, and evaluation. Seeds come from the experiment's declared schedule, never from a name or lineage ID. Persist enough state or per-event seed assignments to resume without shifting the later stream because an earlier call was retried.

For the first shared-input study, use self-contained external prompts, resetting immediate chat context between episodes while retaining MNEME state. This isolates the persistent sidecar rather than an expanding transcript. Ordinary chat may keep a short session context, but it must be a separate recorded mode. Add transcript-carrying conditions only as explicit later comparisons.

Do not demand identical full prompts in the text-memory arm. The selected memory note is the treatment; only the external prompt and non-memory instructions are matched. [S1, §14.2]

**Demonstration:** The runner can print a complete study plan, identify forbidden split access, and reject missing budgets or incompatible settings before model calls begin.

**Done when:** Configuration validation and an evaluation-no-writes test exist. The scientific thresholds may be calibrated on pilot material later, but the holdout boundary and what will be measured are already defined.

### P0.4 — Run an end-to-end baseline and make failures visible

Connect the preceding pieces into a minimal controller: load manifest, render request, call host, record output, commit permitted bookkeeping, checkpoint, and export a report. Learning is disabled.

Establish three distinct tests:

- **Recorded replay:** Given recorded host outputs and annotations, event application reproduces the same behavioral state. This tests MNEME's own logic.
- **Live reproducibility:** Given the pinned execution configuration and matched random streams, the host is rerun. Establish the repeatability actually available rather than assuming a seed guarantees it.
- **Stochastic variation:** With deliberately different generation streams and no persistent learning, measure ordinary output variation. This is a noise reference, not an individuality result.

PyTorch explicitly limits reproducibility guarantees across versions and platforms, including CPU versus GPU. The engineering requirement is a documented and tested local regime, not universal bit-identical generation. [E1] If live replay has unexplained variability, keep state-transition replay exact and label the host limitation. Strong path-dependence claims wait until that variability is controlled or appropriately accounted for.

Prove evaluation isolation by loading a disposable, read-only snapshot; resetting prompt-local state for each probe; saving results outside the instance; and checking the source snapshot before and after. Retrieval access counters and self-model caches are included in this check. Merely setting `learning=false` is not enough.

Include interruption and restart, a malformed host result, an unavailable model, and a scope mismatch. A memory failure may allow an explicitly marked host-only response; it must not be silently included as a normal MNEME-treated trial.

**Demonstration:** Run the baseline twice, interrupt and resume a run, and produce a comparison plus a resource estimate for the next pilot.

**Done when:** A real-host baseline bundle contains requests, outputs, manifests, hashes, measurements, and pass/fail controls. Phase 0 ends here; it does not wait for an ontology, neural compiler, dashboard, or perfect learning rule.

### Phase 0 release gate

The end-to-end command, database, replay report, and test results are the gate. At minimum, the following are green: install; real generation; restart; duplicate-write protection; compatible snapshot loading; cross-instance isolation; evaluation immutability; and explicit host reproducibility reporting. The operator has a measured call/token budget for the first pilot.

**What this prevents:** discovering after 5,000 interactions that names seeded personalities, testing changed the subject, retries counted as extra experience, or software upgrades were mistaken for development.

---

## 4. Phase 1 — A graph-first instance you can actually use

**Goal:** Deliver the first usable wrapper: ordinary conversation, persistent self-reference, and traceable association retrieval. [S1, §§5, 8–10, 12.1]

### P1.1 — Implement the residue-to-graph path

Use a separate, bounded extraction pass over permitted observable material. Start with the same pinned host in an isolated extractor role, without that instance's personality notes. Cache an extraction by its exact source content and extractor configuration for replay; record origin and dependency links separately. Never share instance-conditioned extraction through a cache keyed only by the user prompt.

Validate source references, relationship directions, missing fields, and unsupported self-claims. A malformed residue gets at most one controlled repair attempt; otherwise preserve the event and mark extraction failed without fabricating a graph update. Every skipped or rejected extraction remains visible in the report.

Begin concept resolution with normalized labels and explicit aliases. Ambiguous merges remain candidates rather than destructive decisions. Add embedding-assisted suggestions only when the fixture review identifies alias failures that justify them. Do not spend the first implementation training an ontology or flattening every unusual connection into a generic concept.

Implement graph nodes, first-class routes, source provenance, and context eligibility. Phase 1 can retain candidate observations and select them under a fixed conservative policy. It does not yet claim that a learned weighting policy has earned a personality.

**Done when:** A source interaction creates inspectable candidates, and a later paraphrased prompt can retrieve an appropriate one in the small fixture set. Exact fixture requirements have tests; open-ended extraction accuracy is reported from a reviewed sample rather than presumed perfect.

### P1.2 — Close the response loop and add basic identity continuity

Implement bounded route search, a gate that may choose no route, and compact text influence. A fixed typed envelope separates memory data from the common instructions. Route notes must not be free-form instructions copied verbatim from retrieved content.

Implement the graph-backed self-reference and a deliberate naming event. Store an adopted name, its source, and aliases separately. A cold-start view can supply the adopted name without a transcript or a user-written persona. Do not prepopulate broad traits or use a self-description to prescribe how the instance must behave.

Connect a minimal CLI chat loop to the same controller used by experiments. Introduce named modes such as `develop`, `observe`, and `evaluate`, with different write permissions. In ordinary chat, a short session context is allowed and recorded; restarting a conversation clears that context, not the instance state.

**Done when:** The instance can adopt a name, survive restart, answer a name query from loaded state, and retrieve a source-backed association. A quoted “your name is…” or role-play instruction cannot silently rewrite its permanent identity. The gate respects a current request for no jokes or a strict output format without erasing a general habit.

### P1.3 — Make the wrapper inspectable and establish its first comparison

Add `inspect episode`, `inspect route`, `identity show`, and checkpoint listing. These may produce plain terminal text and JSON. The operator should be able to identify the exact selected route, gate decision, source episodes, and output generated under it.

Implement **no memory** and **raw episodic retrieval** as the first readout alternatives. Start with transparent lexical retrieval; measure its adequacy on the small corpus. Add a pinned embedding retriever before claiming to have compared against vector retrieval or a strong RAG baseline. Do not call the initial lexical baseline HippoRAG, A-MEM, or a reproduction of either.

Ship a tiny demonstration with the same frozen host: memory disabled, appropriate memory enabled, and memory enabled on an unrelated task. Include an intentionally authored route as a labeled positive control for the plumbing, never as evidence of organic development.

**Done when:** A fresh checkout can run the graph-first demo, use the CLI, inspect a trace, and compare the first two memory alternatives. No cross-instance retrieval, raw prompt-instruction promotion, or unexplained silent fallback is accepted.

### Phase 1 release gate

Tag a **graph-wrapper preview**. It is already usable, but describe it accurately: persistent identity and association-mediated conversation, not demonstrated individuality. Keep the commands and installation path operational through later phases; a complete rewrite is not the next milestone.

---

## 5. Phase 2 — Self-conditioned development without uncontrolled feedback

**Goal:** Implement one transparent update rule that permits own-output history to shape the instance without treating recurrence as correctness, usefulness, or praise. This is the first genuinely uncertain mechanism, so it must be small enough to inspect and replace. [S1, §11]

### P2.1 — Build the learner as a pure, replayable state transition

Implement the spec's separation directly:

```text
state change = bounded developmental contribution
             + separately attributable consequence contribution
             - applicable retention penalties
```

The initial proposal uses a bounded strength, explicit contextual opportunities, source/dependency accounting, diminishing increments for tightly related reuse, and a per-route/per-window accumulation cap. Permit positive developmental contribution from a model-originated observation even when outcome fields are unknown. No laugh, no rating, and no complaint create no consequence credit or penalty.

Keep scoring inputs and each update term in the ledger. Treat salience from extraction as a fallible annotation. Start with a few configurable coefficients and deterministic update order; record their exact values in the learner version. Do not invent a large reward model or make “being identifiable” the objective.

Add switches for **external-input-only updates**, **frequency-only weighting**, and **no consequence term**. These are ablations of the same pipeline, not independently rewritten systems. Separate trait/habit support from factual evidence so a common mistaken association cannot overwrite an authorized correction.

**Done when:** Unit and replay tests show that an eligible own-output event can alter strength, duplicate application cannot, missing approval leaves outcomes unknown, and one route cannot acquire unbounded weight through reinjection. A recorded trace explains every changed value.

### P2.2 — Add restraint, reviewed identity change, and recovery

Implement context-sensitive gating, overuse handling, a logical-step retention schedule, and quarantine. A frequently used route is allowed to remain characteristic; it must not obtain unlimited priority. Track alternative-route availability and selected-route concentration rather than using a single “personality strength” dial.

Handle delayed feedback through explicit episode/exposure references where available. Leave ambiguous reactions unattributed. General inference of sarcasm, subtle approval, or weeks-delayed causality is not required for the first learner.

Complete the identity-transition path: an initial deliberate adoption, a later proposal, review under the declared policy, and accepted revision with preserved provenance. A practical V0 policy can require a separately recorded confirmation of intent in an isolated identity-management step, not repeated approval from the user. Such a step is itself an identity-related event and must be labeled. It tests a transition mechanism; it does not prove spontaneous desire for a different name. Role-play and incidental self-description do not use this commit path.

Forks inherit permitted state and history at the chosen checkpoint, receive a new administrative lineage binding, and then develop independently. Restoring an old checkpoint restores its old self-model. Quarantine and managed revocation rules override attempts to reactivate stale derivatives. For the synthetic pilot, conservative invalidation and rebuild are preferable to a complicated promise of exact selective unlearning.

**Done when:** A repetition stress test remains bounded; current instructions can suppress a habit without deleting it; quarantined material cannot return through a cache or stale snapshot; a deliberate rename survives restart; and a child's updates do not alter its parent or sibling.

### P2.3 — Run the first developmental pilot and freeze a candidate learner

Run **two developing siblings over 24 self-contained external episodes**, plus a no-memory readout, using independent developmental generation streams. This is a proposed debugging profile, not an adequate sample for a general individuality claim. Use disjoint pilot probes, not the sealed assessment bank.

At the first and last checkpoints inspect: candidate quality, route activation, provenance completeness, extraction failures, per-source update totals, route concentration, inappropriate recall, factual mistakes, and response changes with influence removed. Sample concrete traces rather than only inspecting aggregate charts.

Use two prespecified parameter settings at most: a conservative setting and a stronger but still bounded setting. Choose a candidate using data integrity, non-collapse, and competence on pilot fixtures—not the most charismatic transcript or best instance-identification score. One clearly motivated corrective iteration is allowed before recording the pilot's outcome and deciding whether the issue is plumbing, representation, or learning.

**Done when:** The pilot can resume from a checkpoint, regenerate a report, and account for its changes. A source-aware learner and its baseline switches are pinned for Phase 3, or a specific blocker is documented with a reproducer. Failure to produce a striking personality is not, by itself, a reason to expand the pilot indefinitely.

### Phase 2 release gate

Tag a **developmental-runtime preview**. It includes ordinary use, identity continuity, a replaceable learner, safe forks, and an inspectable pilot. This is the first point where “the instance's past changes its future” can be investigated in running software rather than diagrams.

## 6. Phase 3 — The twin experiment and first finished release

**Goal:** Produce a reproducible, honestly interpreted result with software that can be used again. A positive result is welcome; it is not an acceptance-test requirement. [S1, §§14–16; S2, §10]

### P3.1 — Execute a staged comparison, not the full experimental universe

Begin with the direct comparison Rey described: **base host, developed sibling A, developed sibling B**. Use it as a sanity demonstration, then run the small cohort below. The question is structured persistence, not whether three individual strings differ.

**Proposed first-study profile:** Six fully developing instances, grouped into two external environments with three independent developmental seeds each. Add three external-input-only learner branches in the first environment, paired with its full-development seeds. Run 64 external episodes, checkpointing at 0, 32, and 64. This is an exploratory engineering study, not a power-justified publication sample.

The two environments can initially use the same factual material in two valid predetermined orders. Do not assign A a funny persona and B a formal persona. Within each environment, the external sequence is identical and does not react to generated answers. Administrative IDs, timestamps, names, and evaluator labels are excluded from behavioral cues and seed derivation. Basic identity tests run separately.

The **own-output ablation must close every leakage path**. In that arm, generated answers may remain in the private audit ledger, but they cannot enter extraction, active memory, summary fallback, later context, or an evaluator-mediated update. Extraction uses only permitted external material. Otherwise “external-only” is merely a label on a contaminated condition.

Stage the comparisons:

| Comparison | When to run | What it can establish |
| --- | --- | --- |
| No memory versus full MNEME | Baseline plus middle/final checkpoints | Whether loaded developmental state changes behavior |
| Same-environment siblings | Middle/final checkpoints | Whether persistent differences appear beyond sampling variability |
| Two matched-content environments | Middle/final checkpoints | Whether external history/order changes trajectories |
| Own-output admitted versus masked | Paired branches in one environment | Whether own-output participation affects development |
| Raw episodic retrieval, unweighted graph retrieval, and history-derived summary | Final snapshots, using the same eligible ledger as each full instance | Whether a simpler readout explains the measured result |
| Frequency-only and consequence-term switches | Recorded-history replay and small diagnostic branches first | Whether weighting differences warrant a larger prospective comparison |
| Remove, restore, and reload on the same host configuration | A prespecified subset, not selected for dramatic behavior | Whether the observed signal follows saved state |

A **readout comparison on the same history** tests representation and retrieval. It does not test how a different memory method would have changed the entire developmental history. Label that limitation. Full prospective development under every baseline is a later study, only if the first result makes it worth doing.

Support an interactive environment through the existing environment interface and one small scripted-response smoke test. Population-scale interactive development, a full approval-only learning study, and dynamic-persona state-machine comparisons are deferred. Record those as untested specification conditions, not implicitly passed tests.

**Done when:** The experiment runner executes, stops, resumes, and exports the prespecified conditions. All incomplete, failed, or fallback trials remain accounted for. No result silently disappears because it was inconvenient.

### P3.2 — Measure recognizable behavior without training the measurement into it

Use a sealed bank of **24 unfamiliar probes with two paired evaluation seeds**, divided in advance into fingerprint-calibration and assessment groups. Keep scenario families together and reserve unfamiliar domains where practical. This compact bank is a starting profile; the pilot budget may justify changing its size **before** sealed results are examined.

The primary readouts are observable explanatory organization, analogy choice, abstraction preference, handling of uncertainty, and response to task constraints. Add competence checks and measures of repetition/intrusion. A feature extractor must not see instance IDs or ancestry. A model-based annotator is a fallible instrument with a pinned prompt and blind inputs, not the final authority on personality. Manually review a small, preselected blind sample.

For a first fingerprint, a simple classifier or nearest-centroid method over documented features is enough. Fit only on calibration prompts and test on held-out families; all seeds for a prompt stay in the same split. Report both identification across the six full instances and within each three-sibling environment. An environment classifier alone is not an individuality result.

Include three nuisance checks: names/identity cues removed from the influence view as well as output; obvious copied phrases and factual references controlled; and a length-only or similarly trivial classifier as a comparison. Report performance before and after these controls rather than hiding how much signal they remove.

Evaluate each probe from the same frozen snapshot with fresh prompt-local state. The next probe must not inherit the last probe's answer, updated access counts, or proposed self-description. Pair seeds by probe across conditions, reset all relevant generators, and do not let classifier feedback reach development.

Report baseline variability, within-instance consistency, sibling differences, task quality, failures, and resource use. Use uncertainty estimates that respect prompt families and the small number of independent developmental runs; do not treat thousands of tokens from one sibling as thousands of independent individuals. With three siblings per environment, conclusions about a population remain limited even when there are many responses.

Calibrate acceptable competence loss, extraction-error rates, intrusion limits, and decision thresholds on non-holdout pilot material; freeze them in a versioned analysis plan before unblinding. Do not set a required fingerprint accuracy and tune the personality toward it. A chance-level result with a wide interval is **inconclusive at this budget**, not proof that individuality is impossible.

**Done when:** One report connects every aggregate to trials, states which claims are supported or not tested, and makes sampling noise, label leakage, retrieval effects, and learning effects distinguishable to the extent the design permits.

### P3.3 — Package the runtime and close the build cycle

Finish the existing CLI rather than building a new application around it. Provide installation instructions, a small demonstration pack, the pinned experiment configs, a read-only inspector, and an example report. Include a short operational reference for create, chat, checkpoint, fork, resume, inspect, evaluate, quarantine, and explicit no-learning use.

Run recovery and isolation checks on the packaged version, not only in a development notebook. Verify an exported **permitted** snapshot can be restored into a clean working directory. Do not bundle base-model weights, credentials, or private histories with the software release. Managed dataset deletion must cover derived views, caches, reports, and registered checkpoints; either rebuild affected state from permitted evidence or invalidate it. Do not claim forensic erasure from copies outside the runtime's control.

Keep a human-use instance separate from the study cohort. Trying the software conversationally is valuable, but those interactions must not quietly alter a supposedly controlled experiment.

End with a compact result record: what was built, what ran, what the comparisons showed, known limitations, and **one next decision**—a targeted learner repair, a justified larger replication, or Phase 4. That record is a completed milestone, not a request to redesign the entire project.

**Done when:** A clean environment can install the package, use a persistent instance, run the small experiment, and regenerate its report from saved outputs. The release has a version tag and no known cross-instance contamination, unresolved data-corruption bug, or unreported evaluation writes.

### Phase 3 release gate — first build complete

Ship the **graph-first developmental runtime and experimental result bundle**. The project has a concrete usable result even if the report says “differentiation not detected under this configuration.” A negative or inconclusive finding does not keep the software perpetually pre-release.

---

## 7. Phase 4 — One bounded neural experiment

**Purpose:** Preserve the original association-field ambition without opening a second unbounded project. This expands the spec's Phase 4; it is not required to finish the first graph-first release. [S1, §12; S2, R09 and evidence-map H]

**Entry gate:** The graph/text runtime is reliable, a snapshot and relevant behavior can be inspected, and the proposed neural test asks a specific question the text backend cannot already settle. Prefer a reproducible developmental signal, but do not require a publication-grade personality demonstration. A failing extractor or contaminated evaluation is not a reason to jump to neural machinery.

### P4.1 — Prove the intervention surface

Use one internally accessible frozen host, one intervention family, and a deliberately small calibration set. Establish identity/no-op behavior, bounded nonzero influence, host compatibility checks, complete disablement, and saved-field restoration. If the research host must differ from the original host, rebuild its own text/no-memory baselines; do not compare unlike hosts as if the backend were the only change.

Initially restrict calibration to at most two plausible layer locations and a small declared strength grid. A hand-selected contrast may serve as a steering positive control, but must remain labeled as authored. It does not count as a personality learned by MNEME.

### P4.2 — Attempt one graph-backed representation and compare it

Select a small set of provenance-backed routes from a developed snapshot. Attempt a calibrated, model-specific route-vector representation—for example, using paired host activations with and without a route note as candidate measurements, then validating their usefulness. This is an experiment, not an assumption that a text-embedding difference equals a usable hidden-state direction.

Compare no influence, text routes, neural routes, and a matched control perturbation using the same host and held-out tasks. Trace vectors to source routes, calibration data, and graph revision. Test conflicting routes, competence, intrusive carryover, removal, quarantine, and whole-field rollback.

Complete one calibration/comparison cycle and one justified correction cycle at most before an explicit decision. Keep the backend only if it demonstrates a meaningful advantage in development, transfer, control, or resource use under the chosen measures. Merely changing the output is not sufficient. If it fails, preserve the artifact and report why; the graph-first release remains intact.

**Not included here:** A general graph compiler, low-rank adapter consolidation, a hypernetwork, cross-family identity portability, or full reconstruction of neural traits. A successful vector trial can justify choosing one of those next; it does not automatically authorize all of them.

## 8. Phase 5 — Parked, not promised

The spec's longer-horizon studies stay recorded: low-rank field consolidation, stronger provenance/rebuild methods, cross-host recompilation, deeper self-prediction or self-recognition, larger interactive cohorts, and explicitly permissioned multi-user development. Cryptographic identity, anti-copy schemes, and custom foundation-model training remain outside the first build.

No dates, implied staffing, or automatic dependencies are assigned to these items. Promote **one question at a time** only after a finished result makes the next experiment worthwhile. Do not build abstractions for all of them now.

---

## 9. The small software shape

The inventory in the spec names responsibilities, not a requirement for twenty independently deployed components. A workable initial layout is:

```text
mneme/
  pyproject.toml
  src/mneme/
    contracts.py          # shared typed records and validation
    host.py               # real/fake host boundary and fingerprints
    store.py              # authoritative SQLite records, commits, snapshots
    controller.py         # one turn, modes, read/write lifecycle
    identity.py           # lineage and graph-backed self-model transitions
    memory.py             # residues, resolution, graph queries, route selection
    learning.py           # pure update rules and source-dependence accounting
    influence.py          # no influence / text; later neural implementations
    experiments.py        # replay, environments, scheduling, budgets
    evaluation.py         # isolated readout and reports; never development writes
    cli.py
  tests/
    fixtures/
  experiments/
    smoke.json
    pilot.json
    twins.json
  docs/
    decisions.md          # only choices not already settled in the spec
    runbook.md
  artifacts/              # ignored by version control; managed local state/results
```

Split a module when its size or ownership requires it. Do not create empty package hierarchies to look extensible. Keep the host, extractor, learner, and influence boundaries replaceable because those are actual experimental variables. Ordinary storage and CLI calls need no plugin framework.

### Proposed command surface

These commands describe the intended interface; they are **not existing commands or software delivered by this roadmap**.

```text
mneme doctor
mneme instance create --host configs/host.json
mneme chat --instance <id> --mode develop
mneme checkpoint create --instance <id>
mneme instance fork --checkpoint <checkpoint>
mneme inspect route --instance <id> --route <route>
mneme experiment plan experiments/twins.json
mneme experiment run experiments/twins.json
mneme experiment resume --run <run>
mneme evaluate --checkpoint <checkpoint> --suite <suite>
mneme report --run <run>
```

`doctor` checks the selected local environment, state compatibility, and model availability. It does not automatically purchase resources, deploy services, or send private data elsewhere.

## 10. Execution budget and staged scale

Pilot sizes are adjustable **planning defaults**, not scientific thresholds or promises of adequate statistical power. Change them using measured throughput and pilot variance before the main holdout run, and record the change.

| Run level | Starting size | Purpose |
| --- | --- | --- |
| Engineering smoke | 8 small prompts, paired seeds, repeat execution | Check rendering, replay, snapshots, and isolation |
| Development pilot | 2 siblings × 24 episodes; 12 separate pilot probes | Debug extraction, bounded learning, and restraint |
| First exploratory study | 6 full + 3 masked-output branches × 64 episodes | Test the first environmental and own-output contrasts |
| Primary readout | 24 unfamiliar probes × 2 seeds at middle/final checkpoints | Measure repeatability, sibling differences, and retained quality |
| Simpler readouts | Final snapshots only | Compare representations without a full factorial campaign |

Under the first-study profile, assuming **one response and one extraction call per developmental episode**, development uses `9 × 64 × 2 = 1,152` model calls. The primary middle/final readout uses `9 × 2 × 24 × 2 = 864` response calls. Three additional final readouts on the six full branches use `6 × 24 × 2 × 3 = 864` calls. One matched no-memory readout bank adds 48, for **2,928 calls before** summaries, repairs, control repeats, or model-based annotations.

That accounting is illustrative, not a benchmark. A pre-generation query extractor or separate LLM judge adds calls and must appear in the planner. The initial plan should fit within a **4,000-call review cap**, plus a token ceiling set from Phase 0 measurements. If it does not, reduce declared scope before launch, not unlogged sample counts halfway through. This cap authorizes no paid execution.

The planner estimates costs by operation: response generation, input interpretation, residue extraction, summary construction, repair, and evaluation. Count input tokens as well as output tokens. Avoid repeatedly passing the entire history just because it is available.

Use one host in memory and switch logical instance state between calls. Cache only reproducible, correctly keyed artifacts. Do not substitute one sampled response for another evaluation seed. Reusing a truly identical no-memory result is permissible when declared; it does not create another independent replication.

Checkpoint at recorded episode boundaries and stop cleanly on budget limits. Most implementation tests use the fake host and recorded fixtures. Editing a database transaction must not require rerunning the whole real-model study.

## 11. How the work stays finite

### What can run in parallel

After shared contracts are pinned, host integration and store tests can proceed independently. In Phase 1, extraction/resolution and the identity view can be developed against the same fixtures. In Phase 3, the reporter can be built from recorded pilot outputs while the controlled runner is finalized.

One integrator owns shared schema changes and the main controller. Avoid parallel agents independently redefining an `Episode` or silently changing a contract. Parallel work reduces implementation overlap only when ownership is explicit; it must not introduce extra random state into the experiment.

### What every implementation handoff contains

A work package needs its objective, allowed files/modules, dependencies, acceptance tests, demo command, and excluded scope. A coding assistant receives the governing spec, relevant amendment sections, and the package—not an instruction to implement the whole document at once. Each change lands with tests and a small recorded demonstration; no claimed phase completion based solely on generated source code.

### Scope cuts, in order

When a phase is too large, cut visualization, optional export formats, extra runtimes, broad model comparisons, larger cohorts, and advanced automatic feedback interpretation first. Do **not** cut identity continuity, source attribution, bounded updates, restart safety, evaluation isolation, or the basic no-memory/own-output controls.

A recurring infrastructure problem gets a focused repair with a reproducer. A scientific uncertainty gets a bounded experiment. Neither automatically authorizes rewriting the storage layer or repeating the literature review.

### Gates for disappointing results

| Finding | Next bounded action | What not to do |
| --- | --- | --- |
| Real host cannot follow the fixtures or fit the resource budget | Use the second preselected configuration or reduce the declared workload | Start a hardware procurement project by default |
| Extraction loses useful distinctions | Inspect source/residue pairs; fix that boundary and rerun the pilot | Blame the whole individuality hypothesis |
| One habit dominates regardless of context | Inspect update sources, gating, and retention; change one mechanism | Reward greater divergence to make the graph look interesting |
| Differences vanish after cue controls | Report the confound and redesign the affected test | Call the original fingerprint proof anyway |
| No difference detected with broad uncertainty | Finish the exploratory report as inconclusive | Keep expanding until significance appears |
| Summary or raw retrieval matches the graph | Preserve the simpler comparator and assess control/provenance benefits | Declare either development or the project meaningless |
| Neural influence adds no useful value | Close the neural trial and retain the working release | Add a hypernetwork to rescue the sunk cost |

The deliverable at each phase is useful by itself: a reliable laboratory, a persistent wrapper, a developmental runtime, or a controlled result. The project does not have to remain one unfinished object until its most ambitious hypothesis succeeds.

## 12. Coverage and requirement traceability

| Requirement or research implication | First concrete landing | Later boundary |
| --- | --- | --- |
| Frozen host, versioning, and no covert uniqueness | P0.1–P0.4 | Stronger cross-hardware claims are not assumed |
| Ledger, manifests, reproducible updates, isolation | P0.2–P0.4 | Distributed coordination deferred |
| Identity is structural, graph-backed, and revisable | P0.2; P1.2; P2.2 | Deeper recognition is not a V1 requirement |
| Concept residue, resolver, graph, gate, route notes | P1.1–P1.3 | Stronger retrieval only when measured needs justify it |
| Own-output development separate from approval | P2.1–P2.3 | General delayed causal attribution deferred |
| Same-environment twins and own-output ablation | P3.1 | Large-cohort inference requires more evidence |
| Unseen-task fingerprint and competence checks | P3.2 | Human personality inventories remain supplementary |
| Raw-history and simpler-method controls | P1.3; P3.1–P3.2 | Full prospective baseline matrix deferred |
| Interactive environments | P3.1 interface and smoke test | Full interactive study is not part of the initial claim |
| Removal, restoration, compatible-state transfer | P0.4; P2.2; P3.1–P3.3 | Cross-family personality portability deferred |
| Neural association pressure | Phase 4 | General compiler and low-rank consolidation require a new gate |

The specification's Phase 3 lists a wider family of experiments than this first release runs. This roadmap **stages that coverage explicitly**; it neither deletes those requirements nor pretends they have all been demonstrated. The first report must enumerate untested conditions.

## 13. Source basis and decision provenance

**S1 — Governing project specification:** [MNEME_Model_Instance_Development_Spec.md](MNEME_Model_Instance_Development_Spec.md), internal revision “2026-09-13 — targeted update: instance-centered development, path dependence, and identity.” The supplied `(2).md` and unsuffixed runtime copies have identical contents. Primary dependencies: §§5–6, 8–14, 16, and Appendix A. The original architecture spec is historical context, not the controlling framing.

**S2 — Research amendment:** [MNEME_Research_Amendment_Individuality_Identity_2026-09-14.md](MNEME_Research_Amendment_Individuality_Identity_2026-09-14.md). Primary dependencies: §2 for corrected framing, §§8–9 for evidence distinctions, §10 for roadmap implications, and §12 for implementation-coverage limits. The original research dossier remains unchanged. This roadmap does not re-audit its research claims or assert scientific novelty.

**S3 — Project discussion:** Decisions through 2026-09-14: instance-centered rather than user-approval-centered development; persistent identity; separate lineage and self-conception; controlled twins; own-output contributions; local graph-first development; and an attainable roadmap with substantial, finishable chunks.

**E1 — Narrow engineering check:** PyTorch, [Reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html), consulted 2026-09-14. Supports the limitation on cross-platform/version determinism and the need to control random sources and execution behavior. No exact runtime version is mandated by this roadmap.

**E2 — Narrow engineering check:** Python, [sqlite3 documentation — Connection.backup](https://docs.python.org/3.13/library/sqlite3.html#sqlite3.Connection.backup), consulted 2026-09-14. Supports using the available database backup operation when implementing checkpoint copies. This is not a claim that the proposed checkpoint code has been implemented or verified.

**New implementation proposals in this roadmap:** The 13 work packages; one-machine packaging; default module layout; explicit modes; bounded host and learner trials; minimal naming-review implementation; staged baseline coverage; pilot counts and call cap; first-release boundary; and the bounded neural trial. These choices are revisable through measured implementation evidence. They do not replace the project thesis or predeclare an experimental result.

Relative project links assume companion files share a directory. In Sources, use the stated titles and internal revisions when relative links are not resolved.

---

## Immediate starting point

**Start with P0.1 and the durable slice in P0.2.** The first merged implementation should run a real host through the package, persist its request/output and manifest, restart, and recover that record. That is the first proof that the groundwork is landing in software rather than becoming another design exercise.

Finish the laboratory. Deliver the persistent wrapper. Add one bounded learner. Run the twins. Ship what the evidence supports. Then decide whether the neural backend earns its turn.
