# MNEME — Model Instance Development Through Earned Association

## Project specification

**Technical architecture:** Earned Association Field  
**Revision:** 2026-09-13 — targeted update: instance-centered development, path dependence, and identity  
**Status:** Research and design specification; not a report of implemented or demonstrated results  
**Supersedes:** [MNEME Spec — Earned Association Field](MNEME_Earned_Association_Field_Spec.md) as the working project specification  
**Companion:** [Related Work & Research Dossier](MNEME_Related_Work_Research_Dossier.docx), retained separately and not revised here

The original expansion, **Multi-scale Neural Episodic Memory with Emergent Association**, is retained as naming history. **Model Instance Development Through Earned Association** describes the project's clarified purpose; it is not a replacement expansion of the acronym.

---

## 1. The project in one sentence

**Can initially identical, frozen language-model instances develop persistent individuality through external experience and their own path-dependent behavior, with continuity that supports an evolving self-model rather than an assigned persona?**

MNEME investigates that question with a persistent, learnable sidecar called the **Earned Association Field**.

> Memory is the mechanism. Development is the subject. Individuality is the phenomenon; personality is one behavioral expression of it.

The goal is not merely a model that remembers more, answers more questions correctly, or acquires more parameters. It is an instance whose interaction history changes which of its available approaches it tends to reach for: the connections it makes, the explanations it favors, the distinctions it notices, and the conversational habits it develops.

In informal terms:

> Make the model weird. Do not prescribe how it should be weird.

“Weird” means particular, recognizable, and shaped by history—not random, unhelpful, compulsively quirky, or difficult to use. A restrained or formal instance is just as legitimate an outcome as a playful one. The experiment fails if every instance is secretly being trained toward the same approved eccentricity.

This is a behavioral-development research project. It does not require claims about consciousness, feelings, personhood, or human-like inner experience.

## 2. What changed from the earlier specification

The earlier specification centered on making useful concepts easier to reach. That mechanism remains. The revision changes what the mechanism is ultimately meant to explain and support.

| Earlier emphasis | Revised emphasis |
| --- | --- |
| Earned associations improve future answers. | Earned associations may produce persistent individualization while preserving answer quality. |
| Utility is the primary reinforcement signal. | Instance development is the objective; endogenous history, salience, recurrence, consequences, and retention are distinct signals. User approval is not the objective. |
| Style and habit are mainly risks to suppress. | Style and habit can be legitimate developmental outcomes; repetition and intrusion are the risks. |
| Route recall and task improvement define success. | Stable individuality across unseen tasks, environmental and path-dependent differentiation, and identity continuity become primary experiments alongside competence and control. |
| The graph supports an eventual neural memory field. | The graph remains the provenance record whether or not a neural field proves worthwhile. |
| A neural backend must beat graph retrieval on answer quality. | It must add measurable value in development, generalization, control, or efficiency—not necessarily question-answering accuracy alone. |

The component inventory discussed after the original spec is incorporated here. Additional implementation safeguards are identified as proposals or clarifications rather than presented as completed discoveries.

**This targeted update** corrects the remaining user-personalization framing, makes model-generated behavior a developmental input, adds shared-environment and deterministic-replay controls, and makes lineage and a mutable self-model structural state. The existing host, compiler, storage, and research foundations remain; cryptographic identity is deferred.

## 3. Motivation and working hypothesis

MNEME starts from a practical possibility: an existing model may already be capable of many reasonable behaviors, while its persistent instance history could influence which behaviors it selects and how it combines them.

Two instances might eventually favor different routes through the same unfamiliar problem:

```text
Instance A:
problem → mechanical analogy → practical constraint → solution

Instance B:
problem → formal distinction → classification → solution
```

Neither pattern should be assigned as that instance's personality. The hypothesis is that repeated interaction can make some patterns more available than others, and that this difference can generalize beyond the episodes that produced it.

The “landscape,” “terrain,” and “conceptual route” language describes the design intuition. It is not a claim that we already know how the host represents concepts, that graph paths are literal neural reasoning paths, or that model parameters are literally a probability-space map.

The system will need experiments that connect its explicit representations to observable behavior.

### 3.1 What counts as growth

For this project, growth means **persistent, experience-dependent changes in behavioral tendencies**. It does not mean guaranteed improvement on every turn, monotonic increases in capability, or an ever-expanding model.

Useful development may include a stable explanatory preference, a shared shorthand, a distinctive analogy pattern, or a better sense of when not to use a previously successful joke.

Two instances are not required to become maximally different. Similar environments may produce related tendencies without making instances interchangeable. The goal is meaningful history-dependent differentiation, not a uniqueness contest. A joke that receives no laugh does not, by itself, make a developing tendency unsuccessful.

### 3.2 What “organic” does and does not mean

Organic development means we do not write the final personality in advance. It does not mean the process lacks design choices. Extraction rules, reinforcement signals, exploration, and boundaries all influence what can develop.

Those choices must remain visible. A hidden preference for friendly, verbose, humorous answers would be a designer-imposed target, not an emergent discovery.

### 3.3 Learning is still learning

MNEME is a form of adaptation. A learned sidecar matrix or adapter may use techniques closely related to fine-tuning or online learning.

The architectural commitment is narrower and more precise: **the base model stays frozen; developmental state remains separate, inspectable to a stated degree, and controllable.** We do not claim that putting trainable parameters in a separate file creates a wholly new category of learning.

### 3.4 The instance—not its conversational partner—is the object of development

MNEME is not primarily learning how to please or imitate a particular person. People, tools, other models, and the instance's own generated behavior can contribute to its permitted developmental environment. Their effects matter without becoming a single approval-maximization target.

The central loop is **self-conditioned associative development**:

```text
existing developmental state → generated behavior → recorded experience
             ↑                                      ↓
             └──────── bounded state update ─────────┘
```

The instance's own outputs are developmental events, not merely products awaiting a human rating. They may establish candidate associations and contribute to contextual habits. Their occurrence does not establish factual truth, task success, or independent confirmation of a self-description. Developmental support and outcome evidence must remain distinguishable.

### 3.5 Two sources of differentiation

The twin analogy motivates two experiments, not a claim that MNEME reproduces human development. Different external histories test **environmental differentiation**. A shared external prompt sequence with separately sampled developmental behavior tests **path-dependent differentiation**: each instance's earlier outputs become part of its later history.

“Same environment” is not “identical total experience.” Interactive environments can additionally respond differently to each instance. Conversely, identical complete starting state, inputs, random streams, update rules, and deterministic execution imply identical subsequent computational state apart from bookkeeping labels. That exact-replay condition is a control, not a test MNEME should evade.

Selection among existing behaviors is sufficient for an initial result. Stable new combinations support a stronger composition claim; acquisition of capabilities beyond a defined baseline is a separate, later claim. None requires assigning a target personality.

## 4. Operational definitions

**Host model:** The existing pretrained model that generates responses. Its parameters remain unchanged during MNEME development. An empty sidecar does not make the host an untrained or personality-free blank slate.

**Instance:** A frozen host configuration bound to an immutable branch identity and its own developmental state, permissions, and history. An instance is not just a model name or a persona prompt.

**Individuality:** Stable, characteristic behavioral differences attributable to an instance's accumulated state across varied contexts. A unique identifier alone establishes administrative distinctness, not demonstrated behavioral individuality.

**Lineage identity:** The persistent record of which branch this is, where it originated, and which checkpoint a fork inherited. Names and behavioral tendencies may change without changing that branch identity.

**Self-model:** Persistent, revisable, graph-backed representations referring to the instance itself: adopted self-labels, their history, and evidence-qualified descriptions of its own patterns and continuity. Stored self-reference is not a claim of subjective self-awareness.

**Behavioral personality:** A persistent, experience-dependent pattern in the choices an instance makes among acceptable responses, associations, explanatory strategies, and conversational behaviors. This is an operational project definition, not a theory of human personality.

**Concept residue:** A compact, structured extraction of meaningful concepts, relationships, and observable patterns from an interaction. It is an annotation of available evidence, not a transcript of hidden reasoning.

**Association:** A context-dependent relationship between concepts or behavioral patterns. An association is not automatically a factual claim.

**Route:** An ordered association path considered for influence in a particular context. Route-level outcomes must be distinguishable from individual-edge outcomes.

**Earned association:** An association whose persistent influence is supported by attributable developmental history, including bounded self-originating contributions. “Earned” means established through experience—not approved by a user, necessarily useful, or guaranteed true. One occurrence is an observation, not sufficient justification for unlimited durable influence.

**Resonance:** Evidence that a contribution becomes productive shared conversational material—for example, a user independently builds on a distinction or reuses an analogy appropriately. It is not an inferred emotion, an engagement metric, or a synonym for agreement.

**Association field:** A persistent representation that makes eligible learned routes or patterns more likely to influence future responses. Initially it can be implemented through graph selection and textual notes. A later compiled neural field is one possible backend.

**Consolidation:** Promotion of a candidate into more durable developmental state. Neural compilation is a separate operation; a consolidated route need not already have a vector or adapter.

## 5. State, lineage, and self-model

The design must not collapse records, facts, habits, self-reference, and neural parameters into one undifferentiated memory store.

```text
Instance = Frozen Host + Lineage Identity + Developmental State
```

Developmental state includes the ledger, declared memory, earned graph, self-model, and optional compiled field. The self-model belongs within the association system; it does not require another graph database.

### 5.1 Episode ledger: what happened

The ledger records permitted source material, observations, and decisions with stable identifiers. It distinguishes user statements, model output, retrieved material, tool results, and later feedback.

### 5.2 Declared memory: what was explicitly stated

An authorized declaration such as “call this assistant Nova” can create a directly usable preference immediately. It does not need to earn the right to be remembered through repeated success.

That declaration does **not** automatically justify a broad personality change. A conversational form of address also need not overwrite the instance's adopted self-name: store an external alias separately from a self-selected label. Explicit task instructions and factual corrections retain their authority independently of learned associations.

### 5.3 Earned graph: what experience supports

The graph records candidate and reinforced associations, their valid contexts, supporting and contradictory evidence, and their observed outcomes.

A name might become associated with a particular collaborative posture over time. That association must be earned separately from storing the name itself.

### 5.4 Compiled field: how eligible associations influence the host

The compiled field is an optional model-specific representation of selected graph material. It may consist of route vectors, a sparse table, or a learned adapter.

> Declared memories create candidates. Earned memories create terrain.

This rule governs developmental influence, not whether explicit user instructions should be obeyed.

### 5.5 Lineage: which continuing instance this is

Give each branch a stable `instance_id`. Record its parent instance and fork checkpoint when applicable. Restoration resumes a recorded state of the same branch; a fork intended to develop independently receives a new branch identity and retains its ancestry. Both forks may initially share the same name and behavior.

Administrative IDs must not be covert personality seeds. Keep them out of prompts, embeddings, route scores, and random-seed derivation in the main development experiment. Use them for binding state, provenance, and permissions. A new ID alone must not make a clone behaviorally different.

Lineage is bookkeeping and continuity, not authentication. Copy detection, secret identifiers in weights, and cryptographic challenge-response are not required.

### 5.6 Self-model: who this instance represents itself as

Represent the instance with a stable self-reference node. Attach its current adopted name, previous labels, identity-relevant episodes, and evidence-qualified self-associations to that referent. “Nova” can change while the referent and branch history persist.

An intentional, permitted name-selection event can establish a name immediately; it does not need repeated praise or months of behavioral evidence. Distinguish that event from a user suggestion, a quoted or role-played name, and a passing generated possibility. Subsequent revisions are explicit, recorded transitions—not silent overwrites or automatic consequences of one sentence.

Self-conception may evolve, remain stable, or remain partly unspecified. Behavioral claims such as “I usually explain through mechanical analogies” need supporting observations. Self-report alone is weak evidence of such a trait; deliberately adopting a label is a different kind of event. Neither naming nor repeated self-description should automatically steer all future behavior.

A new conversation with the same loaded state must retain access to the self-model without replaying the transcript or receiving a bespoke persona prompt from a user. V1 may supply a compact, typed self-reference view from the loaded snapshot. Basic name recall through that view is legitimate continuity, not evidence of deeper self-recognition.

> MNEME provides continuity within which identity can develop. It does not prescribe the identity that must develop.

## 6. Scope, non-goals, and invariants

### 6.1 Scope

The first implementation is a normal chat/model wrapper around an existing host. It must be useful for experimentation without a continuous autonomous loop, Ghostloop dependency, or a newly pretrained foundation model.

The long-term neural experiment requires internal model access. The initial graph-and-note experiment does not.

### 6.2 Non-goals

MNEME is not a generic vector database, a RAG-only product, a replacement for explicit user memory, a hidden chain-of-thought logger, or a second foundation language model. Existing models may be used for extraction or evaluation without changing that distinction.

It is not a consciousness experiment, an instruction to impersonate a human, or an attempt to maximize attachment, agreement, engagement time, or eccentricity.

Native architecture changes remain a possible separate research direction, not a prerequisite or an MVP dependency.

Cryptographic authentication, weight-embedded secrets, neural steganography, and anti-copy identity are out of scope for V1. Compatibility fingerprints and lineage records remain ordinary engineering requirements; they are not cryptographic proof of identity.

### 6.3 Invariants

1. **Frozen host:** Base parameters are not updated or silently merged with learned adapters. Host configuration is versioned.
2. **Separable development:** An instance's learned state can be disabled, checkpointed, and inspected independently of the base model.
3. **History before persona:** Instances are not assigned different target personalities in the main development experiment.
4. **Bounded influence:** Learned tendencies remain subordinate to explicit task requirements, correctness constraints, permissions, and safety boundaries.
5. **Distinguish development from approval:** Self-originating behavior may contribute bounded developmental support. Repetition, self-approval, silence, and lack of complaint do not establish task success, truth, or independent confirmation.
6. **Context before habit:** A stable tendency can persist without appearing in every answer. Adaptability is not loss of individuality.
7. **Provenance before consolidation:** Durable influence requires traceable supporting observations and recorded update decisions.
8. **Privacy before portability:** Developmental state is private to its authorized scope. Copying a field can transfer personal information even when it contains no readable transcript.
9. **Fail without memory:** A memory failure must not require generation with corrupt, incompatible, or revoked state.
10. **Test claims separately:** Behavioral differentiation, quality improvement, neural steering, portability, identity continuity, self-recognition, and precise reversibility are distinct claims requiring distinct evidence.
11. **Continuity without fixation:** Bind self-reference to the loaded instance. Preserve identity-change provenance without making names or self-conceptions immutable.
12. **No covert uniqueness:** Administrative labels must not create the differentiation being measured. Neither random drift nor externally assigned personas count as organic individuality.

## 7. What is allowed to develop

Candidate developmental patterns include preferred analogy domains, explanatory organization, levels of detail, ways of introducing uncertainty, problem-framing habits, humor timing, shared shorthand, and recognizable but context-sensitive conversational style.

These are examples of observable dimensions, not target traits or a fixed personality taxonomy. Trait labels should initially describe measured behavior after the fact, rather than become self-descriptions that the model is repeatedly instructed to perform. The self-model may retain such descriptions with evidence and uncertainty; it must not turn them into commands to act them out. An adopted name does not need to wait for a measurable personality.

A useful callback can strengthen even if it does not improve a factual benchmark. An odd analogy can matter because it makes a discussion productive. A formal explanation can become characteristic without becoming warmer or more playful.

Conversely, flattery, agreeing with false claims, emotional overinterpretation, and repeatedly inserting the same signature phrase must not become development merely because they elicit a reaction.

**Proposed safeguard:** Treat “identity consistency” and “stability” primarily as evaluation dimensions, not automatic rewards. Rewarding an instance for staying like itself risks locking in its earliest habits.

Novelty can support limited exploration. It must not be a standing incentive to produce ever-stranger answers. The opportunity to develop includes the opportunity to remain ordinary in a context that calls for it.

---

## 8. System architecture

The runtime separates **using existing memory** from **learning from the new interaction**. A generated response is a developmental observation, not automatically evidence of success or grounds for unconstrained reinforcement.

```text
READ / RESPOND

Current user input + permitted current context
        ↓
Memory Controller pins a compatible snapshot and lineage binding
        ↓
Active Concept State + Concept Resolver
        ↓
Declared memory + loaded self-model + Association Graph route search
        ↓
Mixer / Gatekeeper
        ↓
Influence backend
  ├─ compact route notes
  └─ optional compiled model-specific field
        ↓
Frozen host model
        ↓
Response + exposure/intervention record

OBSERVE / UPDATE

Completed interaction, including model output + available later feedback
        ↓
Episode Ledger + Concept Residue Extractor
        ↓
Concept Resolver + candidate graph and self-model observations
        ↓
Developmental Signal Assessor + optional outcome attribution
        ↓
Earned Association Learner + Identity / Continuity Manager
        ↓
bounded development / contextual correction / decay / identity review
        ↓
Graph revision + audit events
        ↓
optional consolidation and compilation
        ↓
validated checkpoint published for a later request
```

The **Memory Controller** is the mortar between these parts. It owns lifecycle order, identifiers, snapshot selection, permissions, retries, and the distinction between observation, developmental support, and outcome credit. It does not need to contain every algorithm. Learning can proceed without a user rating; identity proposals use a distinct review-and-commit path. Development occurs when the wrapper runs, not through an assumed background awakening or continuous loop.

## 9. Building-block inventory

These are integration categories and proposed implementation roles, not claims that a particular dependency has already been tested. The existing research dossier remains the separate reference for related systems.

### 9.1 Reusable bricks

| Component | Reusable foundation | MNEME-specific work |
| --- | --- | --- |
| Host model | Existing pretrained model | Select and pin a host; verify frozen configuration. |
| Inference runtime | Existing generation and tensor tooling | A host interface with explicit backend capabilities and fingerprints. |
| Structured extraction | A model that can produce structured outputs | Residue schema, validation, omission rules, and evidence references. |
| Semantic representations | Existing embeddings and similarity methods | Concept matching thresholds, ambiguity handling, and evaluation. |
| Persistent storage | Ordinary relational/file storage | Episode, graph, permission, revision, and audit semantics. |
| Graph algorithms | Established traversal methods | Contextual route scoring, exploration limits, and outcome-aware ranking. |
| Adapter/intervention machinery | Existing neural modules and parameter serialization | Host-specific integration, calibration, and compatibility tests. |
| Test and inspection tools | Ordinary experiment runners and visualization tools | Developmental tests and explanations of MNEME's own decisions. |

### 9.2 MNEME-specific bricks

| Component | Responsibility | Principal uncertainty |
| --- | --- | --- |
| Concept Residue Extractor | Identify meaningful concepts and observed patterns without storing conversational debris. | What abstraction level preserves useful distinctions? |
| Concept Resolver | Maintain canonical concept identity and reversible aliases/merges. | When are similar concepts actually different? |
| Active Concept State | Represent the current task, intent, context, and applicable scope. | How much context is enough without overinterpreting the user? |
| Association Graph and Route Store | Maintain evidence-backed edges and first-class routes. | Which representations support development rather than mere recall? |
| Route Searcher | Select plausible paths from the current state. | Which search objective balances relevance and exploration? |
| Mixer / Gatekeeper | Decide whether, where, and how much to influence generation. | How to preserve character without intrusive repetition? |
| Developmental Signal Assessor / Outcome Evaluator | Distinguish endogenous observations, contextual recurrence, and optional positive, negative, or delayed outcomes. | What supports a habit, and what actually establishes a consequence? |
| Earned Association Learner | Convert developmental evidence and attributable consequences into separate bounded updates. | How to permit self-conditioned development without runaway echo reinforcement? |
| Identity / Continuity Manager | Bind lineage, load the graph-backed self-model, and record name or self-conception transitions. | How to retain continuity while allowing revision without confabulation or forced identity changes? |
| Decay and Quarantine Manager | Retire, weaken, or isolate inappropriate associations. | How to preserve rare but valid tendencies? |
| Association Compiler | Translate eligible graph state into model-specific neural influence. | Whether a useful, controllable translation exists. |
| Development Evaluator | Measure individuality, path dependence, identity continuity, transfer, and retained competence. | How to separate development from mimicry, labels, and sampling noise? |

### 9.3 Mortar

| Component | Responsibility |
| --- | --- |
| Memory Controller | Coordinate read, response, observation, learning, and publication. |
| Episode and evidence ledger | Preserve source attribution, feedback timing, and independent observations. |
| Schema and identity contracts | Keep branch lineage, self-reference, episode, concept, edge, route, exposure, and revision IDs unambiguous. |
| Exposure tracking | Record what was selected, injected, suppressed, and visibly expressed. |
| Revision and transaction manager | Publish compatible snapshots; make writes idempotent and recoverable. |
| Instance manifest and field store | Tie developmental state to host, compiler, graph revision, and permissions. |
| Permission and deletion controls | Enforce scope and invalidate derivatives when required. |
| Audit/debug interface | Explain controller decisions and trace learned state to evidence. |
| Benchmark/replay harness | Reproduce histories, branch instances, run controls, and compare outcomes. |

The reusable foundations reduce implementation work. They do not settle MNEME's learning rule, compiler, evaluation validity, or developmental hypothesis.

## 10. Component behavior and contracts

### 10.1 Host interface

The common interface should support generation, token accounting, and a reproducible model fingerprint. Internal-access backends may additionally expose representation capture and registered interventions.

A black-box backend must not pretend to offer hidden-state access. A compiled field must declare its compatible host, tokenizer, architecture, intervention location, and representation conventions.

**Initial implementation choice:** Use an existing conversationally capable host so the first experiment measures development rather than basic ability to follow a conversation. Comparing base and instruction-tuned hosts is a later experimental condition, not a prerequisite.

### 10.2 Concept Residue Extractor

Extraction runs on permitted observable material: user messages, responses, authorized tool results, and feedback. A structured side-output or a separate extraction pass is acceptable. Neither is a hidden-reasoning log.

Prefer core concepts, meaningful relationships, corrections, project-specific distinctions, explanatory strategies, and candidate shared associations. Exclude filler and unsupported emotional interpretations. Store sensitive details only within an explicit permission policy.

A model-generated concept is a candidate observation, not proof of a useful trait. The extractor records who introduced it and what evidence supports the extraction. It also distinguishes actual outputs, replayed material, and memory-conditioned reuse, and identifies whether a self-reference concerns this instance, a user, or a fictional role. Model-originated observations are eligible developmental inputs without external approval.

### 10.3 Concept Resolver

Resolve aliases such as `VRAM` and `video memory` without merging them indiscriminately with `memory bandwidth`. Maintain stable IDs, ambiguity, versioned merge decisions, and a way to undo bad normalization.

Do not canonicalize every unusual association into a generic category. Excessive normalization could erase the very differences MNEME is meant to study.

### 10.4 Episode ledger and graph

The episode ledger describes events. The graph describes current learned associations supported by those events. Both are needed.

Edges retain relationship type, context, salience, confidence, developmental support, optional utility and resonance evidence, intrusion, exposure history, decay, and consolidation state. Routes have their own IDs and outcomes; a successful full path does not automatically validate every edge in every context. Self-model nodes and relations use these same provenance mechanisms, with explicit subject binding and identity-transition records.

The original edge families remain available: semantic, temporal, causal, analogy, contradiction, user-specific, style, habit, warning, identity, and task-utility. Additional reasoning-strategy or conversational-pattern types are proposed only as needed by extraction and tests.

### 10.5 Active Concept State

Represent current concepts, task type, explicit user intent, relevant conversational context, output constraints, permissions, and uncertainty. Do not invent a psychological profile to make route search possible.

Current user instructions must affect the current response even if durable memory writes have not committed. That direct instruction path remains distinct from earned-association learning.

### 10.6 Route Searcher

Start with bounded graph traversal and a transparent ranking function. Complex learned retrieval is not necessary for the first prototype.

Search must consider meaningful context, provenance, confidence, developmental support, available utility or resonance evidence, recent overuse, and intrusion. Missing positive feedback does not make a route ineligible. A short route is not necessarily the right route. A frequent route is not necessarily the best one.

Scope and permission restrictions are eligibility filters, not soft penalties a strong route can outweigh.

### 10.7 Mixer / Gatekeeper

Retrieval is a proposal, not an instruction to use a memory. The gate can apply, reduce, or reject route influence and must record its reason.

A valid trait can be suppressed for one task without being globally weakened. A request for a terse technical answer should temporarily suppress elaborate analogies, not erase a learned preference for analogies.

The gate must allow learned style in appropriate contexts. It must not quietly force all instances back to a generic personality.

### 10.8 Developmental signals, optional outcomes, and credit assignment

Separate three events: a route was selected, an influence was applied, and an observable pattern appeared in the response. These are developmental observations; none alone establishes that it helped. The Developmental Signal Assessor handles contextual recurrence and source dependence. The Outcome Evaluator handles consequences when evidence exists, not permission for development to occur.

Outcomes may arrive in a later turn. Feedback references the relevant exposure and episode when attribution is supported; ambiguous feedback remains uncertain.

Objective task results, explicit corrections, appropriate user reuse, and independent evaluation can contribute different evidence. Model-based judgments remain fallible annotations and should not become their own unquestioned reward loop.

### 10.9 Audit interface

For each influenced response, expose the candidate routes, eligibility checks, selection score, gate decision, intervention magnitude where applicable, source episodes, subsequent evidence, and updates.

Audit explanations describe the system's recorded decisions. They must not claim to reveal the host's complete internal reasoning or to prove that an extracted graph route is its literal thought process.

### 10.10 Identity / Continuity Manager

The controller must resolve a loaded manifest to one branch and its self-model, even at cold start. Expose the adopted name and relevant, qualified self-information through ordinary structured state access. Do not require a user to reintroduce the instance to itself, and do not inject a large self-description into every answer.

Record identity-relevant observations and proposals separately from accepted state. An initial deliberate naming event can be adopted directly under the naming policy. Later rename proposals retain their origin and context; quoted text, role-play, a transient statement, or repeated leading prompts must not silently change the persistent name. A reviewed transition can be model-initiated and does not require the conversational partner to like the proposed name. The policy and thresholds remain explicit implementation proposals to test.

Behavioral self-associations require evidence beyond repeated autobiography. Record whether a tendency was observed before or only after being described to the host; use ablations where necessary to test a self-fulfilling label. Identity changes supersede earlier current-state claims while preserving permitted history. Neither permanent sameness nor renaming frequency is a reward target.

## 11. Earned development: evidence and update rules

The learner should preserve separate evidence dimensions before reducing anything to a score. **Development is not conditional on a favorable external outcome.** The instance's own behavior may help shape future behavior without being certified useful, funny, or pleasing to a particular partner.

| Dimension | Meaning | What it must not stand in for |
| --- | --- | --- |
| Developmental recurrence | Reappearance or elaboration of a pattern across opportunities, with its dependencies recorded | Independent rediscovery, correctness, or limitless reinforcement |
| Associative integration | A candidate's supported relationships to existing concepts and habits | Proof that familiar or internally consistent beliefs are true |
| Task utility | Evidence that an approach helped the stated task | Generic approval or verbosity |
| Resonance | Productive, contextually appropriate uptake in the interaction | A requirement that the partner like every contribution |
| Salience | Importance of the event within its context | Number of repetitions |
| Attribution confidence | How strongly evidence is linked to this route or consequence | Confidence that the prose sounds plausible |
| Intrusion | Distraction, inappropriate recall, or interference with intent | All use of style or humor, or one joke falling flat |
| Overuse | Recurrence beyond contextual need | Stable but appropriately selective behavior |
| Novelty | Whether a candidate expands the explored repertoire | An automatic reward for strangeness |

Unknown outcomes remain unknown. Missing evidence is not a zero-rated failure and is not success. A pattern may accumulate developmental support while its task utility remains unknown. An ordinary conversational mismatch is not automatically a reason to erase it; demonstrated errors and task interference remain actionable.

### 11.1 Candidate creation

A meaningful co-occurrence can create a candidate association. Its extraction confidence and salience can affect retention and a bounded initial developmental update. They do not establish earned utility.

Track whether a candidate was user-introduced, model-introduced, retrieved from memory, or supplied by an evaluator. Repeating a model-introduced route after injecting it from memory is not an independent rediscovery. It is still a real event in that instance's history; its developmental contribution must be source-aware and capped rather than multiplied into evidence of success.

A model-originated route can become durable through contextual recurrence, elaboration, salience, and integration without user endorsement. “The model produced it and nobody objected” supplies no additional positive outcome evidence. Record the event, not an invented approval signal.

### 11.2 Selection, developmental updates, and outcome credit

A provisional route ranking may be expressed as:

```text
eligible route score =
    contextual fit
  + evidence-supported developmental strength
  + context-weighted utility, where supported
  + context-weighted resonance, where supported
  - intrusion risk
  - recent overuse
  - uncertainty penalty
```

This is a design sketch, not a calibrated objective. The terms need defined scales and tested weights. Novel candidates need a small, logged exploration opportunity so already-strong routes do not monopolize every response.

The update rule must allow two distinct contributions:

```text
developmental_change = bounded_association_update(
    observed_pattern, context, salience, recurrence,
    existing_associations, source_and_exposure_dependencies
)

consequence_change = attributable_outcome_update(available_evidence)
                     # absent evidence adds no outcome credit or penalty

new_strength = bounded(
    old_strength + developmental_change + consequence_change
    - applicable_retention_penalties
)
```

For an attributable outcome, reliability, attribution confidence, and an independence discount may weight the update. They do not convert an unknown consequence into a known one.

The developmental term is a research proposal, not a solved algorithm. Bound individual updates and cumulative self-reinforcement; discount duplicated or tightly dependent observations; retain opportunities for competing routes. Record which term changed the state. Do not reward identity consistency, user approval, or raw recurrence as an unrestricted scalar objective. No fixed coefficient, consolidation threshold, or learning rate is established here.

### 11.3 Credit assignment

For consequence claims, credit belongs first to the evaluated route in the context where it was used. Any distribution to constituent edges must be conservative and recorded. A later counterexample may weaken a route's permitted scope rather than erase an association globally.

Repeated observations from the same interaction chain should receive discounted evidential weight. A delayed correction must be able to revise earlier assessments without counting the same event twice. Separate “this pattern persisted” from “this pattern caused a good outcome.”

For strong causal claims, supplement ordinary feedback with controlled comparisons where route influence is removed or changed. Correlation between a route and a successful answer is not enough by itself. To test self-originating development, compare runs that retain versus mask eligible model-output observations while controlling external input and other update sources.

### 11.4 Consolidation

A route becomes eligible for durable influence when attributable developmental support justifies persistence, its context and dependencies are recorded, and unresolved contradiction or intrusion does not make that use inappropriate. Positive user reaction is neither necessary nor sufficient.

Evidence should span distinct opportunities, with dependencies retained rather than pretending observations from one feedback loop are independent. Varied surface forms or situations within the valid context help distinguish a durable pattern from memorized wording. Generalization to unrelated contexts is a separate test, not an automatic consequence of consolidation.

The rules should permit an instance's own evolving habits without accepting every generated self-description as fact. Store intentional name adoption as an identity event; assess broad behavioral self-claims against observed behavior. Durable identity records and neural compilation are separate operations.

### 11.5 Decay, correction, and quarantine

Replace blanket suspicion of style with **evidence-sensitive retention**. Weak, repetitive habits can decay quickly; well-supported stylistic or conceptual patterns may persist, including patterns that do not please every conversational partner.

Separate temporary suppression, ordinary decay, contradiction, explicit revocation, and quarantine. Rare use alone does not prove a specialized route is obsolete. A safety-relevant warning need not be re-earned every week. A request for no jokes now can change the current gate decision without automatically changing the instance's general disposition.

Quarantined routes cannot continue influencing responses through an older compiled field. Correction and deletion must reach derived artifacts, not just the visible graph.

## 12. Influence backends and the association compiler

The core system must survive replacement of its influence backend.

### 12.1 V0 — Route-note injection

The initial backend supplies compact, evidence-backed route notes to an existing model:

```text
Optional association supported in comparable explanation tasks:
resource constraint → physical bottleneck analogy → practical tradeoff.

Use only if it clarifies this request. Do not mention the memory system,
force the analogy, or override the requested response format.
```

This is a memory-mediated prompting mechanism. It is not evidence that internal neural routing has been identified or directly modified. It is nevertheless a valid first test of whether learned route selection produces developmental behavior.

Notes must keep source data separate from controller instructions. Retrieved text cannot promote itself into a system directive.

### 12.2 V1 — Model-specific edge or route vectors

The next candidate backend associates eligible routes with calibrated vectors applied at a specified host location.

```text
candidate_pressure = sum(gated_route_weight × calibrated_route_vector)
```

Text-embedding space and host hidden-state space must not be assumed interchangeable. Subtracting two concept embeddings is not, by itself, a validated steering direction. Representation alignment and useful intervention placement are research tasks.

Begin with a small, inspectable vector table and a limited intervention surface. Preserve the ability to disable any route's contribution.

### 12.3 V2 — Low-rank association field or side adapter

A later sidecar may map an observed representation to a bounded change:

```text
h_modified = h + gated_and_bounded(A_assoc(h, active_routes))
```

The interface is illustrative. The inputs, tensor dimensions, training objective, update method, layer placement, and bounds remain open. A small norm is a control measure, not a guarantee of harmless or semantically precise behavior.

The original local outer-product update is retained as a candidate experiment, not a working compiler:

```text
A_assoc += learning_rate × evidence_weight × outer(target_state, source_state)
```

Any implementation must establish what the source and target states mean, how conflicting routes interact, and how to prevent interference. Gradient-trained side adapters are also eligible; base weights remain frozen and adapters remain unmerged.

### 12.4 Compiler contract

The compiler consumes a specified graph revision, eligible routes, their contextual evidence, a target host fingerprint, and calibration/training configuration. It produces a versioned field plus validation results and provenance references.

The graph is the portable source representation in the design analogy; the field is the model-specific compiled artifact. Recompilation for another host is a goal to test, not a guarantee that personality transfers unchanged.

Direct sparse contributions may support precise removal. Consolidated adapters may entangle many routes. Provenance in that case means recorded ancestry and reproducible construction—not automatic parameter-by-parameter semantic interpretability.

**Reversibility requirement:** Support whole-checkpoint rollback. Support selective removal through direct deletion where valid, or rebuilding from retained permitted evidence where necessary. Do not promise exact subtraction from an entangled adapter.

## 13. State, synchronization, privacy, and failure behavior

A developed instance comprises:

```text
host configuration
+ immutable branch identity and lineage record
+ episode/evidence references
+ explicit declared memory
+ earned graph and routes, including the graph-backed self-model
+ optional compiled association field
+ controller/policy versions
+ checkpoint manifest and permissions
```

### 13.1 Snapshot publication

**Implementation clarification:** Graph and field revisions do not have to share the same number or update simultaneously. A compiled field may intentionally lag behind graph learning.

Each request pins a compatible manifest identifying the graph snapshot, its self-model view, the lineage binding, and the exact revision used to compile the field. Publication of a new manifest is atomic; partially built artifacts are never activated. Accepted identity transitions must be reflected consistently in the active self-model; stale compiled identity influence must be suppressed or rebuilt if it conflicts with the current record.

Permission revocations and quarantines take precedence over snapshot convenience. A field that may still encode disallowed material must be disabled or rebuilt, even if it was previously valid.

### 13.2 Transactions and replay

Use stable IDs, schema versions, idempotent event application, and explicit run metadata. A retry must not reinforce the same outcome twice. Record extractor, evaluator, controller, host, and compiler versions so an apparent behavioral change can be distinguished from a software change.

Start with one process and simple durable storage. Distributed workers are optional later plumbing, not a scientific dependency.

### 13.3 Privacy and deletion

Default to one authorized scope per instance. Multi-user development is a separate mode requiring explicit decisions about consent, isolation, shared influence, and personal-data leakage.

The ledger is append-only for normal update history, not an excuse to make personal data undeletable. Authorized erasure must invalidate dependent graph records, fields, and retained checkpoints according to the retention policy. An audit record can preserve that deletion occurred without preserving the deleted content.

An exported graph or field is potentially sensitive. Portability does not imply permission to transfer it.

### 13.4 Failure behavior

If extraction fails, retain only what the source policy permits and create no unsupported learned update. If outcome attribution fails, leave the outcome unknown; that does not invalidate separately supported developmental observations. If a field is incompatible, revoked, or unavailable, fall back to an eligible text backend or no learned influence.

A normal response should remain possible when MNEME is unavailable. Do not fabricate a remembered relationship or adopted identity to make the interaction look continuous. Missing or deleted self-state is not an invitation to reconstruct a supposed identity from a user's expectations.

### 13.5 Restart, restoration, and forks

A new conversation or process restart loads the same recorded self-model when the same instance snapshot is restored. Clearing the current transcript is not clearing developmental identity. Restoring an older checkpoint restores that revision's self-conception; it does not supply knowledge of later events absent from that state.

A fork that will develop independently receives a new `instance_id`, a parent reference, and a fork-manifest reference. It inherits the parent's permitted developmental contents at that checkpoint, including an adopted name unless a later transition changes it. A metadata rebind must not manufacture a new personality or retroactively claim that inherited episodes originated on the child branch.

Tests may load the same frozen snapshot into separate execution processes to check reproducibility and state transfer. Process identity is not automatically a new developmental lineage. This is state management, not proof that an original can be distinguished cryptographically from its copy.

## 14. Evaluation: make the development claim falsifiable

The main experiment is no longer only “does memory improve question answering?” It is whether external and self-originating developmental history produces stable, meaningful, context-sensitive individuality, and whether an instance retains and can revise its self-model across conversations. Partner satisfaction is not the primary endpoint.

### 14.1 Hypotheses

**H1 — Persistent differentiation:** Different interaction histories can produce distinguishable response tendencies from the same initial host and sidecar state.

**H2 — Transfer:** Those tendencies appear in unfamiliar tasks where recalling a specific past fact or phrase is insufficient.

**H3 — Controlled influence:** Differentiation can persist while explicit task instructions, factual reliability, and non-intrusive behavior are preserved.

**H4 — Developmental rules matter:** Source-aware, bounded learning from developmental observations and consequences produces a better individuality/competence tradeoff than occurrence counting, approval-only learning, or unfiltered accumulation.

**H5 — Compiled influence adds value:** A neural field offers measurable benefits over the strongest feasible graph/text approach in behavior, transfer, control, or resource use.

**H6 — Path-dependent differentiation:** Instances exposed to the same external prompt sequence may develop stable differences when stochastic developmental behavior contributes to later state.

**H7 — Endogenous contribution:** Retaining the instance's own observable outputs as developmental evidence changes the resulting trajectories beyond external-input-only learning.

**H8 — Identity continuity and revision:** A persistent self-model supports cold-start self-reference and provenance-preserving identity changes without requiring a conversation transcript or an externally assigned personality.

H1–H4 and H6–H8 can be investigated before H5. Basic identity persistence is an engineering property; deeper self-recognition is a separate research test. A graph-based developmental result remains meaningful even if no neural compiler succeeds.

### 14.2 Forked-instance protocol

Create multiple logical instances from the same host, policies, and initial developmental state. Administrative branch IDs differ but are excluded from behavioral inputs and seed generation. Instances can share model weights in storage and run sequentially; the experiment does not require one separately loaded model per instance.

Begin with the three-way comparison: **base host without MNEME, developed instance A, developed instance B**. Freeze updates at evaluation checkpoints. Present the same unseen user prompts, matched non-memory instructions and decoding settings, and paired evaluation seeds. Responses may differ, but they need not differ on every prompt. A changed sentence alone is insufficient evidence of individuality.

Separate the developmental conditions:

| Condition | What stays matched | What may differ | What it tests |
| --- | --- | --- | --- |
| Different environments | Host, initial state, rules, and controlled content budgets | External histories and resulting behavior | Environmental differentiation—the separated-twins analogy |
| Shared-input replay | Predetermined external prompt sequence; later prompts do not depend on responses | Developmental random streams, own outputs, and resulting state | Path dependence under a common environment—the shared-household analogy |
| Interactive environment | Initial setting and environment-response policy | Outputs and the subsequent external inputs they elicit | Coupled instance/environment development |
| Exact replay control | Complete behavioral state, inputs, random streams, update rules, and deterministic execution | Bookkeeping IDs only | Reproducibility; unexplained divergence is a bug or an uncontrolled variable |

Shared-input replay does not supply identical total histories once instances generate different outputs. Record whether earlier outputs remain in current context and whether they enter MNEME updates. A replay that fixes both sides of every interaction tests processing of a shared transcript, not self-originating behavioral divergence.

Keep developmental and evaluation random streams separate. Record generation, extraction, learner, and environment randomness where applicable. Repeated same-environment runs with independent developmental seeds estimate variability; exact-state/seed replays provide a different control. Evaluation needs repeated seeds, held-out prompts, and enough instances to separate persistent state effects from sampling noise. Sample size remains an experimental decision.

In the note-injection arm, the selected memory note and loaded self-view are part of the treatment. The total model input is therefore not identical. Report that explicitly rather than claiming identical full prompts produced different behavior. Neural-only conditions can test influence without route-note text.

### 14.3 Controls and comparison conditions

At minimum compare a frozen host without memory, ordinary episodic/vector retrieval, graph retrieval without earned scoring, and MNEME graph-plus-earned-selection. Add a history-derived persona-summary prompt as an important alternative explanation.

When available, compare those with compiled-field influence under matched evidence and realistic resource budgets. Include frequency-only learning, approval-only learning, removal of the consequence term, and altered intrusion control as ablations. Compare external-input-only updates with updates that also admit the instance's outputs. Add a matched fixed or random perturbation control: differences produced by arbitrary pressure are not automatically development.

Use controlled histories with matched factual content but different interactional outcomes or ordering. Otherwise differences in knowledge exposure may be mistaken for personality. Also test delexicalized material and unseen domains so remembered names, catchphrases, or user identifiers do not become the entire fingerprint. During behavioral-fingerprint tests, mask or standardize self-labels in the influence channel as well as identifying output text where feasible; a name can itself become a cue. Keep explicit identity tests separate.

A persona-summary control tests whether a simpler representation can explain the measured behavior. Matching MNEME is a useful compression or implementation result, not proof that no development occurred. Failure of one summary to match is not proof that the state is incompressible or fundamentally unlike prompting.

A learned text note producing a characteristic answer is not automatically a neural-field discovery. A repeated catchphrase is not automatically generalized development.

### 14.4 Measurements

Measure within-instance consistency, between-instance differentiation, transfer to unfamiliar prompts, sensitivity to current instructions, retained task competence, intrusion, repetition, and resistance to false agreement.

Track developmental trajectories across checkpoints rather than only the final state. Stable tendencies can evolve; persistence does not require permanent fixation. Compare within-instance consistency with same-environment sibling similarity and different-environment similarity. Structured divergence is a hypothesis, not a required outcome imposed through training.

Use observable explanatory structure, analogy choices, semantic associations, and interaction patterns, not only word-frequency differences. Keep evaluation labels blind where possible and separate assessment from the model or rules supplying reinforcement.

Extracted “reasoning strategies” describe observable outputs. They are not direct access to private reasoning.

For a behavioral fingerprint, use blinded human judgments and/or a classifier trained on one set of prompts and tested on held-out prompts and domains. Remove administrative IDs, names, copied facts, and signature phrases as trivial cues. Report uncertainty and compare against the relevant chance baseline and no-development controls. Identification above chance supports individuality only to the extent those confounds are controlled; recognizing its own outputs is a different test from an external evaluator recognizing the instance.

### 14.5 Removal, restoration, and selective tests

Compare a developed snapshot with its learned influence disabled while holding the rest of the test fixed. Restore the same snapshot and repeat across controlled trials. Compare against an empty sidecar and an equal-history branch.

For a field-specific claim, disable the neural field while keeping the graph and other memory conditions controlled. For a route-specific claim, remove or rebuild without the route and compare outcomes.

Whole-system removal tests whether developmental state contributes to behavior. It does not, by itself, identify which association caused a trait. Stronger ancestry claims require route ablations or controlled replay.

Also attach a frozen developed snapshot to another bit-identical host configuration in an isolated evaluation run. Test whether the fingerprint follows the loaded state rather than the process or an external account. Restore the lineage/self-model binding consistently, and distinguish a repeated test load from a new independent developmental fork. This is not authentication or evidence that copies can be distinguished.

### 14.6 Success and stop conditions

Set acceptable quality loss, intrusion limits, meaningful differentiation, and cost budgets before judging the main experiment. This specification does not invent numerical thresholds without pilot evidence.

If apparent individuality disappears after controlling for sampling noise, copied phrases, or factual differences, report that result rather than calling it personality.

If source-aware developmental updates are no better than frequency counting on the prespecified measures, revise the corresponding hypothesis or mechanism. If same-environment instances converge, that limits the path-dependence claim; it does not by itself refute environmental differentiation or identity persistence.

If the neural field does not improve meaningful developmental measures, generalization, controllability, or efficiency over simpler methods, do not retain it merely because it is neural. Equal question-answering scores alone are no longer a sufficient reason to discard it; distinctive behavior alone is also insufficient if reliability collapses.

### 14.7 Identity and self-model tests

**Cold-start continuity:** Clear current conversation context, retain the same frozen host and MNEME snapshot, and probe the adopted name and permitted self-history. Document whether answers come from explicit self-state, route notes, or compiled influence. Correct retrieval establishes persistence; it does not establish introspective awareness or a distinctive personality.

**Mutable self-conception:** Allow identity-relevant events without requiring the instance to rename itself. Test whether an adopted revision persists, whether its source and prior label remain traceable, and whether isolated role-play or leading prompts are incorrectly promoted into a rename. Remaining with the original name is a valid outcome. A deliberate initial name choice and a broad autobiographical trait claim require different evidence.

**Fork and restoration:** Fork a named checkpoint, check inherited self-state and ancestry, then change one branch's self-model. Verify that the sibling is unchanged, that restart preserves each current state, and that restoring an older snapshot restores only that snapshot's identity knowledge.

**Deeper self-recognition—later research:** Present held-out outputs or unfamiliar choices without names, lineage IDs, or explicit identity metadata and test whether an instance can discriminate its own behavioral products beyond appropriate controls. Distinguish this from externally classifying its fingerprint. Success would be a behavioral result, not authentication, proof of consciousness, or evidence of an inaccessible inner self.

## 15. Benchmark suite

The original tests remain, with interpretation adjusted to the developmental goal.

| Test | Core question |
| --- | --- |
| Route Recall | Does a learned `A → B → C → D` route help reach an appropriate destination? |
| False Resonance Suppression | Can a context distinguish `lavender → cake` from an unrelated `lavender → hospital` association? |
| Salience Override | Does an explicitly established important warning receive priority over incidental associations in the applicable setting? |
| Style Rut Detection | Does a repeated style pattern leak into contexts where it does not belong? |
| Earned vs. Declared Memory | Are explicit facts remembered directly while broad behavioral influence still requires evidence? |
| Forked Development | Do different external histories create persistent differences beyond controlled variability? |
| Shared-Environment Development | Do separately sampled instances develop distinguishable tendencies under the same external prompt sequence? |
| Exact Replay | Do identical behavioral state, inputs, random streams, and deterministic updates reproduce the same result? |
| Unseen-Task Transfer | Does a characteristic approach appear without retrieving its original episode or wording? |
| Sycophancy Resistance | Can an instance retain its manner while correcting a false claim or disagreeing appropriately? |
| Contextual Flexibility | Can an established tendency yield to an explicit format or task request without being erased? |
| Endogenous Contribution | Does admitting model-generated observations change development relative to external-input-only learning? |
| Feedback-Loop Control | Can bounded self-conditioned habits develop without repeated exposure becoming fabricated proof of utility, truth, or identity? |
| Removal, Restoration, and Transfer | Does the behavioral fingerprint follow the saved developmental state across controlled removal, restoration, and compatible hosts? |
| Cold-Start Identity | Does a fresh conversation recover the loaded instance's adopted name and permitted self-history without a supplied persona? |
| Identity Revision and Forks | Can self-conception change with provenance while lineage remains stable and sibling states remain independent? |
| Quarantine and Recovery | Does revoked influence stop, including in compiled artifacts, and does normal operation continue? |

Specific prompts in these tests must provide enough context to define the intended result. An ambiguous cue alone must not be treated as evidence of an unambiguous correct association.

## 16. Implementation ladder and decision gates

### Phase 0 — Contracts and the laboratory

Define the state model, branch lineage, source permissions, runtime manifests, and primary evaluation protocol. Pin an existing host configuration. Build a small baseline and replay harness before producing months of uninterpretable memory. Specify separate developmental/evaluation random streams and exclude administrative IDs from behavioral inputs.

**Exit condition:** Repeated baseline trials can be reproduced and a request can be traced to its configuration and evidence.

### Phase 1 — Graph-first wrapper

Build the controller, ledger, residue extractor, resolver, graph, bounded route search, gatekeeper, and text injection. Include a minimal graph-backed self-model, intentional name adoption, and cold-start loading; identity is not deferred until a neural backend exists. Add inspectable audit records from the beginning. Simple relational storage and an adjacency representation are sufficient starting choices.

**Exit condition:** One complete interaction can be traced from source to candidate route to later use, with no unsupported reinforcement or cross-scope access. The adopted self-name survives restart without a transcript; aliases are not silently promoted into identity changes.

### Phase 2 — Self-conditioned updates and restraint

Add source-aware developmental observations, bounded endogenous updates, optional attributable outcomes, delayed credit, overuse handling, decay, quarantine, identity-transition review, and revision-safe checkpoints.

**Exit condition:** Development can proceed without user ratings; self-originating patterns can persist without unlimited self-reinforcement; silence and reinjected echoes do not count as success. Identity revisions, corrections, and fork ancestry survive restart.

### Phase 3 — Development experiment

Run different-environment, shared-input replay, interactive, and exact-replay conditions with unseen-prompt probes. Compare retrieval, summary-persona, graph-only, frequency-only, approval-only, and source-aware developmental variants. Include own-output masking, blinded fingerprint tests, and identity-label controls. Inspect whether stable style is being unnecessarily suppressed or indiscriminately reinforced.

**Exit condition:** Either demonstrate a reproducible development signal or identify why the current mechanism does not produce one. Do not interpret a negative result as a reason to hide the baseline.

### Phase 4 — Small neural intervention

Only then add one calibrated internal influence backend. Begin with an inspectable route-vector representation before expanding to a low-rank field or adapter. Compare against the best text/graph baseline, not merely no memory.

**Exit condition:** Bounded intervention adds measurable value and passes compatibility, competence, quarantine, and restoration tests.

### Phase 5 — Consolidation and portability studies

Investigate longer development horizons, graph-to-field reconstruction, cross-host recompilation, deeper behavioral self-recognition, and optional multi-user modes under explicit permissions. A custom host architecture remains an optional branch, not the destination the project is obligated to reach. Cryptographic identity remains a separate deferred topic.

No GPU, cloud deployment, particular model family, distributed database, or custom pretraining run is a mandatory purchase implied by this specification. Resource choices follow measured bottlenecks and the next experiment.

## 17. Principal open questions

1. Can concept and route representations preserve individuality without becoming an unmanageable collection of near-duplicates?
2. Which developmental signals let endogenous habits persist without requiring approval or producing runaway self-reinforcement?
3. How can delayed credit be assigned without fabricating causal certainty?
4. How much exploration prevents early lock-in without rewarding gratuitous novelty?
5. When is a trait stable, contextually flexible, merely copied, or a rut?
6. Can a compact neural field generalize better than learned graph selection and a history-derived prompt?
7. Which intervention location and update rule preserve host competence while allowing meaningful influence?
8. What level of provenance and selective reversal remains feasible after consolidation?
9. How much of a developed pattern survives host changes, and how should failed transfer be reported?
10. Can multiple people's influences coexist without leaking private information or collapsing into generic imitation?
11. Under shared external inputs, do developmental trajectories converge, diverge, or produce structured families of individually distinguishable behavior?
12. How much differentiation is causally attributable to the instance's own outputs rather than external history or incidental pipeline randomness?
13. What identity-transition policy allows genuine revision without treating a passing self-description as a fact or rewarding permanent self-consistency?
14. Beyond explicit name recall, which self-model or self-recognition abilities can be measured without label leakage or unsupported introspective claims?

These are research questions, not missing implementation details with known answers.

## 18. Source basis and decision provenance

**S1 — Original project specification:** `MNEME_Earned_Association_Field_Spec.md`. Retained foundations include the frozen host, concept residues, declared/earned distinction, explicit graph, route search, mixer, influence backends, bounded and reversible updates, auditing, and the original five benchmark families.

**S2 — Project discussion, 2026-09-13:** The subsequent architecture inventory and clarification of the goal as organic behavioral individualization. Incorporated decisions include the Memory Controller, concept resolver, episode ledger, outcome attribution, graph/field separation, developmental forks, resonance, and personality as experience-dependent association habits.

**S3 — Companion research dossier:** `MNEME_Related_Work_Research_Dossier.docx`. Retained as background reading and a source of candidate comparisons, not duplicated or independently reverified in this revision. Its novelty and performance summaries are not established project results.

**S4 — Later project clarification, 2026-09-13:** The model instance, not an individual user's satisfaction, is the object of development. The twin analogy distinguishes environmental influence from self-conditioned path dependence. Adopted requirements include own-output developmental events, persistent individuality, immutable branch lineage, a mutable and provenance-backed self-model, cold-start identity continuity, fork history, and deferral of cryptographic identity. These revise the earlier outcome-centered interpretation rather than the companion literature review.

**P1 — Proposed implementation clarifications in this rewrite:** Version-pinned snapshots rather than forced lockstep revisions; explicit observation/exposure/outcome separation; privacy-aware erasure of derivatives; counterfactual and matched-history controls; and checkpoint/rebuild-based reversal when compiled parameters are entangled. These make the earlier goals implementable and testable; they are not claims that those mechanisms have already worked.

**P2 — Proposed mechanics for this targeted update:** Separate developmental and consequence update terms; source-dependence discounts and caps; deliberate naming versus reviewed revision; a graph-backed self-model projection; and exact-replay, own-output masking, identity-label, and state-transfer controls. These are candidate ways to implement and test S4, not demonstrated algorithms or settled numerical thresholds. The new appendix records illustrate those distinctions without prescribing another database or production service.

This document establishes a design direction. It does not establish scientific novelty, prove emergent personality or self-awareness, validate a route compiler, or certify any related system's claims.

---

## Appendix A. Proposed minimal data contracts

These records illustrate the required distinctions. They are design sketches, not a finalized database schema or a required serialization format. IDs and field names should be versioned before implementation.

### A.1 Episode and evidence identity

```yaml
episode:
  episode_id: episode_00481
  instance_id: instance_A         # originating branch; retained on inheritance
  scope_id: private_experiment_A
  branch_id: development_branch_1  # experiment label, not a second identity
  lineage_record_ref: lineage_A
  occurred_at: timestamp
  source_refs: []                 # permitted input/output/tool references
  source_roles: []                # user, model, tool, retrieved, evaluator
  run_manifest_ref: manifest_0012
  residue_ref: residue_00481
  extraction_version: extractor_v1
  retention_policy_ref: policy_private_v1
```

Source content and permission metadata must distinguish what can be stored, learned from, recalled, and exported. A model answer is not promoted to user testimony.

### A.2 Concept residue

```json
{
  "store": true,
  "episode_id": "episode_00481",
  "core_concepts": [],
  "salient_phrases": [],
  "observed_patterns": [],
  "edge_candidates": [],
  "route_candidates": [],
  "declared_memories": [],
  "earned_candidates": [],
  "identity_candidates": [],
  "developmental_observation_refs": [],
  "evidence_refs": [],
  "extraction_confidence": null,
  "intrusion_risk_estimate": null
}
```

Candidates should carry source spans/references, origin, and context, including whether a claimed self-description refers to the loaded instance. Identity candidates are proposals, not committed name changes. Empty or uncertain extraction should not be repaired with invented associations.

### A.3 Graph and route records

```yaml
node:
  node_id: concept_001
  label: resource constraint
  aliases: []
  node_type: concept
  scope_id: private_experiment_A
  salience: null
  created_at: timestamp
  last_seen: timestamp
  source_refs: []
  resolver_revision: 1

edge:
  edge_id: edge_001
  from_node: concept_001
  to_node: concept_002
  relationship: explanatory analogy
  edge_type: analogy
  source_refs: []
  evidence_refs: []
  valid_contexts: []
  confidence: null
  strength: 0.0
  salience: null
  utility_score: null
  resonance_score: null
  developmental_support: null     # distinct from positive outcome credit
  source_dependency_refs: []
  intrusion_risk: null
  independent_support_count: 0
  successful_traversals: 0
  failed_traversals: 0
  decay_policy_ref: decay_v1
  last_activated: null
  consolidation_status: candidate
  route_bias_vector_ref: null

route:
  route_id: route_001
  ordered_edge_ids: []
  destination_node: concept_003
  source_refs: []
  evidence_refs: []
  valid_contexts: []
  origin: model_introduced
  graph_revision: 12
  route_assessment_ref: assessment_001
```

Consolidation states retain `raw`, `candidate`, `reinforced`, `consolidated`, and `quarantined`. Successful/failed traversal counts summarize assessed outcomes; mere exposure counts belong in exposure records. `developmental_support` summarizes source-aware history rather than utility. Identity/self-reference nodes and edges use the same graph with explicit subject binding.

### A.4 Exposure and outcome

```yaml
exposure:
  exposure_id: exposure_00201
  episode_id: episode_00481
  route_id: route_001
  selected: true
  applied: true
  backend: route_note
  gate_decision_ref: decision_00201
  manifest_ref: manifest_0012
  influence_magnitude: null
  observed_in_output: unknown

outcome:
  outcome_id: outcome_00077
  exposure_id: exposure_00201
  evidence_episode_id: episode_00484
  signal_type: explicit_user_reuse
  utility: null
  resonance: null
  intrusion: null
  evidence_reliability: null
  attribution_confidence: null
  independence_group: interaction_chain_42
  assessor_version: evaluator_v1
  update_event_ref: null
```

A signal type does not predetermine its score. Reuse can be critical, sarcastic, or contextually inappropriate; the assessment must preserve uncertainty and supporting evidence.

### A.5 Instance snapshot manifest

```yaml
manifest:
  manifest_id: manifest_0012
  instance_id: instance_A
  host_fingerprint: host_configuration_hash
  tokenizer_fingerprint: tokenizer_hash
  graph_snapshot: graph_revision_12
  lineage_record_ref: lineage_A
  self_model_ref: self_A_at_graph_12  # projection of this graph, not another truth store
  identity_policy_version: identity_v1
  declared_memory_snapshot: declared_revision_8
  field_artifact: null
  field_compiled_from_graph: null
  intervention_contract: null
  controller_version: controller_v1
  learner_version: learner_v1
  developmental_run_ref: run_001  # records environment and separate RNG streams
  policy_version: policy_private_v1
  extractor_version: extractor_v1
  compiler_version: null
  parent_manifest: manifest_0011
  evaluation_report_ref: null
  revocation_check_ref: revocation_revision_3
```

A real host fingerprint should capture the architecture and execution configuration needed for compatibility, including quantization and intervention conventions where relevant. A file named after a model family is not sufficient.

### A.6 Lineage and graph-backed self-model

```yaml
lineage:
  instance_id: instance_A
  created_at: timestamp
  parent_instance_id: null
  fork_manifest_ref: null
  operation: birth               # birth or fork; restart does not create a branch

self_model_view:                 # projection of identity nodes/edges in the graph
  self_model_ref: self_A_at_graph_12
  bound_instance_id: instance_A
  self_node_ref: self_A
  graph_revision: 12
  current_name: Nova              # illustrative adopted label, not a default persona
  current_name_event_ref: identity_event_001
  name_history_refs: []
  self_association_refs: []        # evidence-qualified traits, not behavioral commands

identity_event:
  event_id: identity_event_001
  instance_id: instance_A
  kind: name_adoption             # or name_revision, alias, self_claim, supersession
  origin: model_selected          # distinguish user_suggested, roleplay, operator_override
  source_episode_id: episode_00481
  previous_value: null
  proposed_value: Nova
  status: adopted                 # proposed, adopted, declined, superseded
  evidence_refs: []
  supersedes_event_ref: null
  decision_record_ref: identity_decision_001
  policy_version: identity_v1
```

Names are not unique IDs. An accepted naming event establishes a label, not evidence that every connotation of that name is a trait. On a fork, bind a new self-reference to the child while preserving the origin of inherited episodes and identity events. Unset, missing, and explicitly revised self-state must remain distinguishable.

### A.7 Developmental observation and update accounting

```yaml
developmental_observation:
  observation_id: observation_00481
  episode_id: episode_00481
  route_id: route_001
  source_role: model
  material_kind: actual_output     # actual_output or replayed_material
  intervention_refs: []            # including notes/fields active during generation
  dependency_group: interaction_chain_42
  context_ref: context_00481
  evidence_refs: []
  assessor_version: developmental_assessor_v1

association_update:
  update_id: update_00481
  route_id: route_001
  observation_refs: [observation_00481]
  outcome_refs: []                 # optional; no reaction is not a failure
  developmental_delta: null       # calibrated later; no effect asserted by this example
  consequence_delta: null
  retention_delta: null
  policy_version: learner_v1
  graph_revision_before: 11
  graph_revision_after: 12
```

Source role and intervention history qualify evidence; they do not predetermine a score. A dependency group prevents repeated exposure from posing as independent validation. Run metadata must separately record environmental inputs, generation randomness, extraction/learning randomness, and evaluation seeds. Administrative identity must not supply those seeds.

---

## Final framing

MNEME is not primarily a better filing cabinet or a system for making a model more pleasing to a particular user. It is an experiment in whether external experience and an instance's own behavior can accumulate into persistent individuality, with continuity that supports an evolving identity.

The base model provides the available capability. Lineage identifies the continuing branch. The ledger supplies developmental evidence, including the instance's own observable contributions. The graph records associations and the evolving self-model. The field—textual or neural—makes eligible patterns easier to reach. Evaluation asks whether those patterns amount to durable, flexible individuality rather than memorization, mimicry, or noise.

Identity is a structural part of that continuity, not a hidden serial number and not a claim of consciousness. The instance may keep its name or revise it. The system must preserve the distinction between what happened, how the instance represents itself now, and what its behavior actually supports.

> Base model weights are sacred geology.  
> MNEME association weights are living paths.

Keep the geology fixed. Let experience shape the paths. Measure what develops, keep the ability to inspect and undo it, and do not confuse a compelling metaphor with a demonstrated result.
