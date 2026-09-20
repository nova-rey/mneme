# MNEME — Developmental Self-Context and Functional Layering

## Future architecture proposal

**Document ID:** FUTURE-DSC-01  
**Revision:** 1  
**Date:** 2026-09-20  
**Status:** FUTURE DESIGN CONTEXT — NOT AN APPROVED IMPLEMENTATION PLAN  
**Proposed repository home:** `docs/architecture/future/MNEME_Developmental_Self_Context_Architecture.md`  
**Origin:** Project discussion about memory, individuality, naming, and an instance's internally maintained self-context.  
**Current-work impact:** Documentation and discoverability only. No change to an approved phase, running experiment, acceptance criterion, or inference budget.

> **Keep building the authorized runtime. Preserve this direction for later design. Do not turn it into another requirement for finishing Phase Two.**

## 1. Purpose and central question

MNEME studies whether a frozen model instance's history can produce persistent, revisable, characteristic behavior. Episodic memory, associative retrieval, and learned accessibility are mechanisms toward that question; they are not automatically a complete account of individuality.

This proposal makes a further distinction explicit:

- **Episodic history:** What happened, and what evidence exists?
- **Associative development:** Which connections have become available, established, or contextually restrained?
- **Developmental self-model:** What does the instance currently represent about itself, with what evidence and uncertainty?
- **Developmental self-context:** Which bounded projection of that self-model is available during a particular response?

The proposed research question is:

> **Does an evidence-qualified, revisable self-context add useful continuity, calibrated self-description, or history-dependent behavior beyond associative retrieval and a simpler history-derived summary?**

The intent is not to assign a personality, reward a preferred identity, or make the model continually discuss itself. It is to make permitted self-state available without requiring a person to reintroduce the instance to itself at every new conversation.

“Internal” describes the origin and management of this context within the instance's runtime. It does not imply a private conscious experience, privileged introspection, or an information channel already present inside the frozen host. [S1, §§1, 4–7]

## 2. This extends an existing commitment; it does not invent a second self-model

The governing specification already defines a persistent, revisable, graph-backed self-model. It provides for a stable self-reference, adopted names, evidence-qualified self-associations, cold-start access, and recorded identity changes. It explicitly says that the self-model belongs within the association system, not another graph database. [S1, §§5.6, 10.10; Appendix A.6]

The contribution of this note is narrower: it clarifies how a richer self-model might become a bounded runtime context, how that context differs from instructions and retrieved episodes, and how its own effects would be tested.

| Existing project commitment | Future elaboration proposed here |
| --- | --- |
| Graph-backed self-reference and identity events | A richer, evidence-qualified self-view, not another authority store |
| Basic name continuity without a replayed transcript | Contextual availability of permitted identity and self-observations beyond a name |
| Source/exposure/update provenance | Explicit tracking of exposure to self-descriptions and their downstream effects |
| Mutable self-conception with reviewed transitions | Separate handling of adopted labels, observed tendencies, hypotheses, and disputed claims |
| Optional text or neural influence backends | A representation-neutral self-context boundary, with text as the first possible prototype |
| Comparison with simpler methods | Direct tests against identity-only views, graph-only influence, and history-derived summaries |

These are functional responsibilities, not newly numbered phases, model layers, services, or extra model calls. The existing self-reference and identity mechanisms remain the starting point.

## 3. Placement, authority, and the non-contamination rule

### 3.1 Document authority

This document records a future architectural direction requested by the project owner. Its mechanisms, examples, and experiments are proposals, not approved implementation requirements.

Current implementation remains governed by the project's specification, approved phase plans, and explicit execution authorizations. This note does not supersede their scope allocations or resolve an active qualification failure by introducing a different system.

Where a future proposal would require changing an approved contract, record that dependency for future review. Do not use this note to justify the change during current work.

### 3.2 Immediate repository treatment

File this note under `docs/architecture/future/`, outside `docs/Approved Plans/`. Link it from the main documentation index, including beside the active Phase Two plan entry. Label the link as **future architectural context; no current implementation dependency**.

A reference in the index makes the direction discoverable without editing a pinned plan or experiment. Preserve historical approval records and append a documentation-only entry to `bible.md` when the file is integrated.

Do not add a required queue item, change a gate to WAITING, open a new phase, modify release criteria, or spend an API call to satisfy this note.

### 3.3 What “build with this in mind” means now

It means preserving the separations already required by approved work: evidence versus interpretation, instance identity versus host identity, data versus instructions, and snapshot state versus current conversation. Do not erase those distinctions merely to simplify an unrelated change.

It does **not** mean adding unused schema fields, placeholder classes, a self-context service, a reflection scheduler, a new persona prompt, or speculative extension hooks. Existing records can be extended through an explicit later migration when a real experiment needs them.

A missing future capability is not a defect in current work. A defect in an already-approved invariant still deserves its normal reproducer and repair; this note does not create or enlarge that obligation.

## 4. Functional layers, not a psychological anatomy

The discussion used ego/id/superego as an analogy for different kinds of information and control. No Freudian theory, biological equivalence, or particular psychological architecture is adopted. The useful distinction is operational.

| Responsibility | Question it answers | Boundary |
| --- | --- | --- |
| **Frozen host** | What general language and reasoning capabilities are available? | Does not become an untrained blank slate when the sidecar is empty |
| **Governing instructions and runtime policy** | What is required, permitted, or prohibited for this operation? | Cannot be rewritten by a learned self-description |
| **Current external context** | What is being requested or observed now? | User instructions, tool data, and quotations retain their distinct roles |
| **Episodic and associative state** | What occurred, what connects, and what influence is eligible? | Availability is not factual truth, authority, or an obligation to express |
| **Developmental self-context** | What permitted self-information should be available for this response? | A bounded projection of revisable state, not a command to enact a persona |

The Memory Controller remains the coordinator. There is no requirement for five models, five storage systems, or five sequential calls. [S1, §§8–10]

Personality, under MNEME's operational definition, could arise from interactions among these responsibilities. This proposal does not assign it to one magical module or assert that the combination is sufficient.

## 5. What an “internal prompt” would and would not mean

A first prototype could provide a compact structured self-view as part of the host's normal input, alongside selected associations and the current task.

At that point it is still **context-mediated prompting**. Calling it internal does not turn text into neural memory, hidden reasoning, or autonomous self-awareness. The governing specification already makes this distinction for route notes. [S1, §12.1]

Three concepts must remain separate:

1. **Provenance:** Did the material come from the user, an accepted identity event, observed behavior, a model-generated claim, or a controller projection?
2. **Authority:** Is it a governing instruction, an authorized declaration, a proposal, or fallible data?
3. **Transport:** In which provider message or representation was it delivered?

Runtime-generated data is not automatically high-authority data. Conversely, a fixed controller envelope might travel through a provider's system-message mechanism without making every quoted self-observation a system command. The future adapter must document the actual rendering and its limitations.

The controller supplies the instruction about how to interpret the self-view. Learned content cannot supply new governing instructions, tool permissions, goals, or exceptions to current requirements.

**Descriptive text can still influence behavior.** A label such as “you often use mechanical analogies” may encourage that very behavior even when marked as a description. This effect must be recorded and tested; the label “descriptive” does not eliminate it.

“Continuously available” means recoverable from the loaded state across requests and fresh sessions. It does not require injecting a long autobiography into every answer, updating it continuously, or running when the wrapper is idle.

## 6. Contents and evidential standing of the self-model

A future self-context projection should preserve different kinds of claims rather than compress them into one paragraph of asserted personality.

| Kind | Example | Evidential standing |
| --- | --- | --- |
| Accepted identity state | The currently adopted name and the event that established it | A recorded state transition, not a measured personality trait |
| Host/runtime information | The currently selected model family and available runtime capabilities | Verified configuration where available; not whatever the model says about itself |
| Observed tendency | A particular explanation pattern appeared in several specified contexts | Evidence-qualified behavioral annotation, including contrary cases |
| Self-report or proposed change | A response proposed a different name or described a preference | A candidate event; not automatically an accepted fact or policy |
| Uncertainty or limitation | Evidence for a tendency is sparse or heavily memory-conditioned | Remains explicit; absence of support is not a negative personality judgment |

Relevant private backing records would include source references, subject binding, context, evidence coverage, counterevidence, exposure ancestry, interpretation version, accepted status, and supersession. These are conceptual requirements for a future promoted implementation—not a database migration requested now.

Only selected, necessary content belongs in model-visible projections. Administrative IDs, raw hashes, filesystem paths, and incidental timestamps stay in the trace unless a later explicit experiment justifies otherwise. Naming history need not expose unrelated conversation contents.

### Illustrative projection, not a proposed API

A compact self-view might convey:

> Current adopted name: Gemma4. The name comes from a recorded model-selected adoption event. No later accepted naming event supersedes it. In troubleshooting exchanges, several responses used mechanical comparisons; some followed supplied analogy notes, and other responses used direct procedural explanations. This is a limited observation, not a requirement to use comparisons now.

This example is authored explanatory material, not an actual instance record, a default prompt, or evidence of a real trait. A future implementation should decide whether such observations belong in the projection at all before choosing their wording.

The system must not silently turn that into:

> You are a mechanically minded personality. Always explain things through machines.

## 7. Proposed read and development paths

### Read/respond

```text
Compatible accepted snapshot + current task + current authority
        |
        +-- permitted identity and self-model projection
        +-- relevant episodic/association influence
        +-- fixed governing instructions
        |
        v
Shared controller: relevance, conflict, scope, and size checks
        |
        v
Exact recorded host input / optional later representation interface
        |
        v
Frozen host response
```

The proposed projection is an additional use of accepted state, not a new writer inside the read path. Empty or disabled self-context is a valid condition. A strict output request may suppress optional descriptive content without erasing the stored self-model.

### Observe/update

```text
Actual response + exact supplied context/exposure + permitted later evidence
        |
        v
Source-bound observations and candidate self-claims
        |
        v
Existing versioned development / identity policies,
with any future extension separately approved
        |
        v
Accepted graph/self-state transition and compatible snapshot
        |
        v
A later request may use the revised projection
```

A response cannot secretly rewrite its own governing instructions while it is being generated. A proposal does not become an accepted name or trait merely because the prose is confident.

Initial prototype preference: derive a bounded view from structured accepted records and refresh it only at explicit state transitions. Do not repeatedly ask a model to rewrite its own autobiography as a default. A model-assisted view builder, if later justified, becomes a separately versioned, budgeted, fallible component with retained inputs and outputs.

The observer records observable behavior and supplied influences. It does not claim access to the host's hidden chain of thought.

## 8. Identity: model family, instance, name, and revision

The family-name analogy is useful shorthand for distinguishing a shared model from an individual instance's adopted label. It is not a requirement to implement first and last names.

Keep separate:

- The underlying host's actual model and execution identity.
- The continuing branch's administrative lineage.
- Its adopted name and accepted naming history.
- The broader self-observations that may or may not develop.

An adopted name is not merely an administrative UUID. It is explicit self-state that can legitimately be available at cold start. It is also not proof of a distinctive behavioral personality. [S1, §§5.5–5.6; S2, §9]

A neutral naming operation can clarify that the instance and its shared model family are different referents. It need not require different labels. Choosing Gemma, keeping Gemma, changing to another valid name, or leaving a broader self-conception unspecified are all legitimate outcomes under the applicable identity policy.

Do not optimize for novelty, dramatic renaming, attachment, or permanent consistency. Do not repeatedly ask whether the name still fits merely to provoke change.

If an ordinary response proposes a change, preserve its origin: current user suggestion, role-play, memory exposure, model-origin proposal, or unknown influence. Use the accepted review/commit path. The self-context can represent what changes the current policy permits, but must not claim that a model can commit arbitrary changes whenever it says so.

Host migration also changes real conditions. A retained adopted name does not prove identical behavior after a host change, and a new model family does not automatically require renaming. Record the actual host transition separately.

## 9. Prevent self-description from becoming counterfeit evidence

A self-context creates a particularly direct feedback risk:

```text
A tentative tendency is summarized
        -> the model reads the summary
        -> the model performs or repeats it
        -> the system treats that repetition as independent confirmation
```

Future work must distinguish a tendency observed before description from a tendency observed after repeated exposure to that description. [S1, §§7, 10.10; S3, §§6–8]

Proposed safeguards for a future implementation:

- Identify each supplied self-claim and its backing snapshot in the private exposure trace.
- Treat the projection as derived, replayed material, not a new external experience.
- Keep subsequent model behavior as a real event while preserving its dependencies; do not award independent confirmation merely because the model repeated its self-description.
- Maintain supporting, contrary, contextual, and unknown evidence separately. No reaction from the user is not approval.
- Keep identity adoption distinct from trait inference: a deliberate label choice can establish a name immediately, while a broad behavioral claim needs separate evidence.
- Do not reward “remaining myself,” dramatic growth, renaming, or classifier identifiability.
- Treat quotes, fictional roles, third-party claims, and injected instructions as their actual source kinds, not accepted self-state.

A future self-view selector or summarizer also has an influence on what becomes salient. Record its configuration and omissions; do not treat it as a neutral window into an already-existing inner person.

Strong unusual tendencies are allowed. The control objective is attributable, revisable influence—not making every instance average. At the same time, “this is part of my identity” cannot become a mechanism for overriding current instructions or retaining a known falsehood.

## 10. Persistence, permissions, and failure boundaries

These future requirements extend existing snapshot and provenance principles rather than propose a replacement store. [S1, §§13.1–13.5]

**One authority source.** The graph-backed identity and accepted evidence remain authoritative. A rendered self-context is a versioned projection or compiled artifact with source bindings, not a competing profile file that silently becomes the truth.

**Consistent snapshots.** Pin self-context, association state, learner configuration, identity policy, and authority to compatible versions. Do not mix a newer name with an older narrative or a stale compiled self-description.

**Forks.** Inherit permitted self-state and its original provenance. Rebind the child's referent administratively without awarding new developmental credit or forcing a different name. Future changes on one branch must not alter the other.

**Revocation and correction.** A withdrawn source or superseded self-claim must not continue influencing through an old summary, cache, or field. Retain whole-snapshot rollback and rebuild/disable paths; do not promise exact subtraction from an entangled neural representation.

**Missing state.** Report what is unavailable and use the declared fallback. Do not reconstruct an allegedly remembered identity from model branding, user expectation, or a convenient default name.

**Evaluation.** Read a frozen self-view without changing self-claims, access statistics, learner clocks, identity proposals, or later probe inputs. A self-prediction probe remains an evaluation artifact, not new developmental evidence.

**Privacy.** Self-context can disclose information about both the instance's history and its conversational partners. Apply the existing permitted scope, provider-reuse and export controls to derivatives, not just raw episodes.

## 11. Relationship to the Earned Association Field

Self-context and association influence answer different questions. The former represents selected self-information; the latter changes which associations are available or expressed. They can interact without becoming identical.

A textual projection is the simplest candidate for inspecting that interaction. A later model-specific neural representation could be compared with it, but this note neither selects a tensor interface nor accelerates the neural work ahead of its existing gate. [S1, §12; S4, §7]

Do not assume that concept embeddings, graph keys, or a narrative self-summary map directly to valid hidden-state directions. A neural implementation would need its own alignment, compatibility, disablement, competence, and provenance evidence.

Avoid accidental double influence: supplying the same self-description as prose and through a field is a distinct treatment, not a free implementation detail. Record the combination and test it separately.

The useful long-term principle is representation independence: the accepted evidence and identity history should survive a change in influence backend. Preservation of behavior across hosts or backends remains a hypothesis to test, not a promise.

## 12. How to test whether this is more than elaborate retrieval

The transport does not settle the scientific question. A text-mediated mechanism can support development; a neural mechanism can still be an unnecessarily expensive implementation. The existing research amendment explicitly treats reflection-plus-memory and self-model nodes as relevant prior art, not phenomena invented by MNEME. [S2, §§1, 4/R03, 6/R16, 10.6]

The claimed value must concern what is represented, how it develops, its control and provenance, or a measured behavioral/resource benefit. More layers, a private prompt label, and a complicated ledger are not evidence of novelty.

### Proposed future comparisons — not current experiments

| Comparison | Question |
| --- | --- |
| No self-view vs identity-only vs richer self-context, with the association readout held fixed | What does the richer projection add beyond stored naming? |
| Rich self-context vs a competent history-derived summary with matched evidence and reasonable input budget | Does structured self-state justify its complexity? |
| Projection on vs off at the same frozen state | Does the supplied self-context affect this readout? |
| Prospective development with vs without self-description exposure | Does repeatedly describing the instance alter its subsequent trajectory? |
| Self-labels masked or standardized across siblings | Does the apparent distinction survive removal of name and branding cues? |
| Earlier vs later snapshots, and removal/restoration | Does the measured effect follow accepted state and remain revisable? |
| Declared self-prediction compared with held-out observed behavior | Is the self-description calibrated, rather than merely fluent? |

Use fresh contexts, matched non-memory instructions, documented sampling, context-sensitive tasks, and competence/intrusion checks. Log actual exposure. Separate within-instance variation from between-instance differences. An evaluation output must never update the subject.

A same-snapshot readout comparison is not a prospective developmental experiment. Replaying recorded history under another update rule is not evidence of the history that alternate rule would actually have generated.

If a simple summary matches the graph-derived self-context, retain that result. It may show that the richer behavior is compressible, or that the simpler representation is sufficient. It does not establish that no development occurred.

Conversely, failure of one summary is not proof of irreducible identity. A model accurately stating its stored name establishes continuity, not introspection. A classifier separating outputs is not automatically self-recognition. The source specification and research amendment already require these claims to be tested separately. [S1, §§14.3–14.7; S2, §9]

## 13. Future promotion gate and unresolved choices

This direction has no automatic phase assignment, deadline, or live budget. It must not displace the approved Phase Two pilot or silently alter a later frozen study.

Promote one bounded question only through a new explicit planning decision. That decision should specify:

1. The proposed benefit and the simpler alternative that might already supply it.
2. Which self-information is accepted, tentative, disputed, or unavailable, and how it is selected.
3. The read/update interface, snapshot binding, privacy rules, and failure behavior.
4. The exact influence transport and how self-description exposure will be tracked.
5. A small experiment, controls, budget, and engineering versus research acceptance criteria.

Open choices include whether richer self-context should be supplied routinely or only when relevant; whether deterministic projections suffice; how contextual tendencies and counterevidence are summarized; and which objective measurement would justify the added machinery.

No universal trait vocabulary, update schedule, summarization prompt, neural representation, or new threshold is settled here. Implementation should answer the smallest useful question first. A negative or inconclusive result can close that experiment without erasing this architectural record or blocking the existing runtime.

## 14. Repository filing instructions — documentation only

These instructions are the intended handoff to Codex. They authorize organizing this design note, not implementing it.

At the next normal documentation/checkpoint boundary, without interrupting or restarting any active inference operation:

- Save this complete document at the proposed repository home. Create `docs/architecture/future/` if absent. Do not place it in `docs/Approved Plans/`.
- Add a future-architecture entry to `docs/README.md`, and a short cross-reference adjacent to the current Phase Two plan entry. Preserve the approved plan itself, its digests, all run manifests, and historical receipts.
- Append a `bible.md` entry stating that this is a recorded future direction with no change to current requirements, budgets, or acceptance status.
- Verify relative links and that the diff is documentation-only. Commit and push through the current serialized integration workflow; report the resulting SHA and path.
- Resume the already authorized work at its existing state. Do not restart a blocked goal, make a provider call, or clear a blocker solely because this document was filed.

Suggested documentation-index text, relative to `docs/README.md`:

```markdown
## Future architecture — non-blocking design context

[Developmental Self-Context and Functional Layering](architecture/future/MNEME_Developmental_Self_Context_Architecture.md)
records a future extension of the existing graph-backed self-model. It is not
an approved implementation plan, a Phase Two acceptance dependency, or an
inference authorization. Current work remains governed by its approved plan.
```

Suggested cross-reference beside the current phase entry:

```markdown
Future design context: [Developmental Self-Context](architecture/future/MNEME_Developmental_Self_Context_Architecture.md).
This reference does not change the phase's implementation scope, frozen
experimental contracts, acceptance requirements, or authorized call budget.
```

Do not add executable placeholders, test requirements, TODO-driven tasks, database columns, prompt templates, scheduled reflection, or default persona content. Do not feed this architecture note into the developing instance, extractor, assessor, or evaluation prompts. It is context for the software's developers, not an experience for the experimental subjects.

## 15. Sources and decision provenance

This is a synthesis of supplied project sources and the current discussion. No fresh literature sweep, model experiment, or source-code audit was performed for this note. Repository reads were limited to the documentation index and directory layout to choose a suitable filing location.

**[S1] Governing project specification:** [MNEME — Model Instance Development Through Earned Association](../../specifications/MNEME_Model_Instance_Development_Spec.md), revision 2026-09-13. Especially §§4–8 for state/self-model distinctions; §§10.9–10.10 for audit and identity; §§12–13 for representation and lifecycle; §§14.3–14.7 for controls and claim boundaries. This is the source of the existing graph-backed self-model commitment.

**[S2] Research amendment:** [Developmental individuality, path dependence, and identity](../../research/MNEME_Research_Amendment_Individuality_Identity_2026-09-14.md), review date 2026-09-14. Especially §1, R03, R11–R16, and §§9–10. It supplies the project's qualified prior-art and measurement framing. Its external research claims are not independently reverified here.

**[S3] Developmental dynamics amendment:** [Continuity, plasticity, consolidation, and corrective feedback](../../research/MNEME_Developmental_Dynamics_Amendment_2026-09-19.md), dated 2026-09-19. Especially §§2–9. Read its implementation allocation through subsequent approved plans; this future note does not move deferred mechanisms into the current phase.

**[S4] Development roadmap:** [MNEME — Development Roadmap](../../specifications/MNEME_Development_Roadmap.md), dated 2026-09-14. Especially §§1–2, 4–8, 11–12. It supplies the finite build, existing identity work, separate neural gate, and parked future-work policy. It is a roadmap, not evidence that every described mechanism has shipped.

**[S5] Project discussion, 2026-09-20:** The request to distinguish external context, accumulated memory, evolving self-understanding, and governing instructions; to consider a persistent “internal prompt” without treating it as a prescribed persona; and to preserve this direction without contaminating active development. The family-name and psychological-component analogies are discussion aids, not adopted scientific models.

**[S6] Current implementation authority:** [Approved Phase Two self-conditioned developmental runtime plan](<../../Approved Plans/MNEME_Phase_Two_Self_Conditioned_Developmental_Runtime_Plan.md>) and its explicit execution authorizations. This link identifies where current work remains governed. This note neither edits that plan nor certifies its implementation or completion.

Relative links assume the proposed repository home. In Sources, use the exact document titles and revisions when relative links are unavailable.

### Decision record

**Recorded direction:** Develop a bounded, evidence-qualified self-context as a possible future extension of the existing graph-backed self-model; test its value rather than assume it.

**Preserved constraints:** Instance-centered development, frozen host, source-aware updates, current-instruction precedence, permission boundaries, explicit identity transitions, and uncontaminated evaluation.

**Not decided:** Implementation schedule, current-phase additions, self-context generation method, extra model roles, trait schema, neural transport, or an experimental budget.

**Immediate authorized effect:** Save and link this design record. Continue current work under its existing contracts.

---

> **Memory preserves experience. Association changes accessibility. Self-context represents selected, revisable information about the instance. None becomes proof of personality merely by being given a separate name. Build the connections deliberately, keep the sources traceable, and test what each contribution actually changes.**
