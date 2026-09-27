# MNEME — Phase Four Research & Architecture Brief
## From SAA pressure to on-demand, host-specific neural influence

**Document ID:** P4-RB-NEURAL-2026-09-27  
**Revision:** 1  
**Date / source review:** 2026-09-27  
**Status:** Research reference and proposed architecture; not an implementation order or execution authorization  
**Audience:** Rey, Codex, and future MNEME planning/review sessions  
**Suggested repository location:** `docs/research/MNEME_Phase_Four_Research_Brief_On_Demand_Neural_Influence_2026-09-27.md`

> **MNEME keeps the history. SAA selects what becomes active. A host-specific translator determines how that active state can influence the host internally.**

---

## 1. The decision in plain English

Phase Four should investigate replacing the **textual delivery of SAA influence**, not replacing the developmental system that produces it.

Today, SAA selects an earned associative neighborhood and a renderer turns its pressure into words for the host. The proposed neural backend would instead convert that selected state into a small numerical intervention in the host's ongoing computation. The base model's weights remain frozen. This follows the governing specification's separation of portable graph state from model-specific compiled influence. [P1–P3]

**We do not need to map the model's entire conceptual universe before trying this.** A first experiment can translate a handful of selected neighborhoods. An early operational design could compile a translation when first needed and cache it. A more scalable design could learn a translation function that handles new neighborhoods without a fresh per-neighborhood training exercise.

These are three different levels of ambition:

| Level | What it means | What it does not mean |
|---|---|---|
| Small neural trial | Derive and test a few candidate interventions. | Catalog every concept or neuron. |
| On-demand compilation and caching | Pay a construction cost on a cache miss; reuse qualified artifacts later. | Compilation becomes free or instantaneous. |
| Learned translator | Learn to generate interventions from a description of the active state. | Generalization to arbitrary MNEME states or new hosts is guaranteed. |

The first level is the proposed Phase Four entry point. The other two define the direction of travel, not prerequisites for beginning.

## 2. What is already established, and what remains a hypothesis

### Project evidence and inherited design

The R8 terminal receipt reports a completed text-mediated C/SAA study, nonzero treatment at its required measurement coordinates, paired responses, and removal/restoration records. Its Thread 10 contained **four C/SAA pairs: eight individual responses**, followed by twelve held-out pairs. That receipt is evidence for the existing interface, not a neural result or proof that every output difference expresses the selected association. This brief does not independently re-audit its complete evidence bundle. [P4]

The governing architecture already calls for calibrated route vectors followed, potentially, by a low-rank field or side adapter. It explicitly warns that ordinary text embeddings are not interchangeable with host hidden states and that portability of the graph does not guarantee unchanged behavior after recompilation. [P1]

The SAA amendment contributes the upstream mechanism: history-shaped weighted selection, a separately seeded landing, and bounded neighborhood activation. It does not supply a ready-made neural coordinate system. [P2]

### Proposed extension

The hypothesis is that a model-specific translator can preserve some of this active neighborhood's characteristic influence without sending its textual cue into the target conversation.

SAA makes the problem **better specified**, not already solved: it supplies a small, inspectable target instead of asking a neural backend to interpret an entire lifetime at once. Its graph weights still need calibration into intervention strength. A graph weight of `0.7` is not a neural injection coefficient of `0.7`.

The current text backend is a **comparison and possible training reference**, not an infallible answer key. Matching a lossy renderer could faithfully reproduce the wrong abstraction. Preserving more of the active neighborhood than the renderer preserves is a separate, interesting objective.

## 3. Research map: the relevant existing approaches

The descriptions below report published methods. Their adaptation to MNEME is a proposal.

### ActAdd and CAA — the simplest first attachment

Activation Addition derives a candidate steering pattern from differences between a host's internal activations on contrasting prompts. Contrastive Activation Addition averages differences across paired examples and adds the resulting direction during generation. Both provide precedents for modifying inference without updating the base weights. [R1, R2]

For MNEME, a contrast could emphasize a selected framing in one condition and omit it in a matched condition. “Positive” and “negative” here mean presence and absence of the target property—not good and bad answers.

**Why start here:** limited machinery, directly inspectable vectors, and a clear way to compare text influence with internal influence. **Limitation:** a successful contrast does not establish a universal concept knob. Example construction, layer, token position, gain, and context still matter. [R1, R2, R7]

### Prompt Steering Replacement — imitate how a prompt exerts influence

*Steer Like the LLM* proposes Prompt Steering Replacement (PSR): trained interventions that approximate prompt-induced changes, with strength depending on token activations rather than remaining identical everywhere. The paper presents attribute-specific parameters; it is not, by itself, a universal translator for unseen concepts. [R3]

**MNEME use:** a next candidate when a constant vector is too blunt. It provides a concrete reference for transferring a measured text-mediated effect into internal intervention. The released code calls PSR `Focused` and often calls its MSE objective `psi` or “Prompt Steering Imitation”; those names matter when navigating the implementation. [I4]

### HyperSteer — the strongest direct reference for avoiding endless individual mapping

HyperSteer trains a hypernetwork to generate steering vectors from a natural-language steering description, optionally conditioned on the base prompt and host activations. It reports generalization to steering prompts withheld from training. This is direct precedent for learning the translator rather than maintaining only individually constructed vectors. [R4]

It is **not a ready-made lightweight MNEME component**: the paper uses Gemma 2 hosts, substantial concept-training data, truncated copies of the host as hypernetworks, and A100-80GB training hardware. Its tested performance does not establish fit on the MSI or support for our current host. [R4]

**MNEME use:** a principal scaling reference. SAA—not a user command to adopt a persona—would supply the state to translate.

### ReFT / LoReFT — learned intervention without changing base weights

Representation Finetuning learns task-specific interventions on frozen-model hidden representations. LoReFT constrains these edits to a low-rank subspace. It is an alternative when a simple additive vector lacks the needed expressiveness, but introduces training, deployment, and validation work. [R5]

**MNEME use:** an optional later backend, not a requirement to build before testing a vector. Keep learned side parameters separate and unmerged from the base model. A task-specific ReFT module is not automatically a generalized SAA compiler.

### Feature dictionaries / Gemma Scope — optional interpretability tools

Sparse autoencoder features offer another route: identify an internal feature and adjust its activation. Golden Gate Claude illustrates both that this can affect generation and that strong steering can produce pervasive, irrelevant fixation. [R6a]

Google's inspected Gemma Scope releases cover Gemma 2 and Gemma 3. They are not an established feature dictionary for our Gemma 4 E4B runtime. [R6b]

**MNEME use:** optional analysis and comparison where compatible resources exist. Building a complete feature atlas is not the entry requirement for Phase Four.

### Reliability research — why a vector is a candidate, not a translation certificate

Braun and colleagues report substantial sample-level variation, including opposite-direction effects, across the steering prompts they examined. Their results connect reliability to whether activation differences align coherently. [R7]

**MNEME implication:** evaluate translation on held-out contexts. A readable label, high similarity score, or one successful completion is not enough to establish faithful intervention.

## 4. An existing implementation attachment point

Source inspection found a concrete path in **llama.cpp**, the runtime identified in the project's earlier local experiments. This is upstream code evidence, not verification of the installed MSI binary.

At inspected revision `97e4ca73582084f2751767f80c86237483ecc381`:

- `tools/cvector-generator/README.md` documents GGUF control-vector construction, including mean/PCA options, and CLI controls for scaling and layer range. [I1]
- `src/models/gemma4.cpp` calls `build_cvec(cur, il)` before passing a layer's output onward. [I2]
- `src/llama-adapter.cpp` implements vector addition in `llama_adapter_cvec::apply_to`; its application path checks embedding width and can disable the current vector. [I3]

This supplies an **injection mechanism**, not the semantic translator. Before using it, verify the exact local build, model file, tensor dimensions, layer numbering, extraction location, and whether the implementation applies pressure during prompt processing, generated tokens, or both. A paper's intervention location cannot simply be assumed equivalent to this hook.

The static vector path also does not automatically implement PSR's token-dependent gains or HyperSteer's learned generator. Those would require a separate integration decision. Do not replace a working local runtime or disturb the ongoing study merely to inspect them.

## 5. Proposed architecture

```text
Earned developmental graph + current context
                    |
               SAA selection
       seeded landing + neighborhood activation
                    |
       Portable active-neighborhood description
           /                            \
Existing text renderer             Host-specific translator
           |                      cache / compiler / learned model
     Text comparison                         |
                                   Bounded neural intervention
                                             |
                                    Frozen host generation
```

### Keep selection, translation, and application separate

**Selection:** MNEME/SAA decides what becomes accessible from earned state. The neural backend must not substitute the most convenient cached topic for the actual selected neighborhood.

**Translation:** build a model-specific intervention representing that neighborhood's relations, composition, and relative pressure. The input should preserve more than a generic sentence such as “things affect other things.” Retain provenance in audit data without injecting administrative identities into generation.

**Application:** place the intervention at verified internal locations with calibrated strength and a defined lifetime. Clear it between conditions and requests as required by the experimental protocol.

**Development:** ordinary learning and any accepted introspection updates remain upstream. Constructing contrastive examples, testing vectors, or replaying calibration prompts must not silently become new lived experience for the instance.

This separation extends the existing compiler contract rather than redesigning the graph or replacing SAA. [P1–P3]

## 6. What “compile on demand, then cache” actually entails

This section is a proposed MNEME design, not a capability already demonstrated by R8.

When SAA selects a neighborhood, the backend checks for a compatible, qualified artifact. A cache hit reuses its numerical direction or intervention module and applies the current calibrated pressure. A cache miss initiates a bounded construction process: form contrasts, collect host activations, derive a candidate, and test it on calibration material before admitting it to the cache.

**Yes, the early design still performs individual translation work.** Doing it lazily avoids translating unused state in advance; it does not eliminate the per-miss work. The unit should usually be a meaningful active neighborhood or reusable framing, not every atomic node. Whether two neighborhoods genuinely share a usable intervention must be tested, not assumed from similar labels.

### Cache identity and invalidation

A cache record should bind the target host/checkpoint, tokenizer and chat template, quantization, runtime/extraction method, intervention site, compiler version, semantic neighborhood descriptor, and qualified gain range. Store construction evidence and dependency provenance alongside it.

Initially prefer exact semantic-contract matches. Similarity-based reuse can be investigated later; otherwise distinct histories can collapse into a small set of generic “resilience,” “creativity,” or “coordination” buttons. If neighborhood structure changes materially, revalidate. A change only in current pressure may permit reuse with a new calibrated gain. Unrelated graph edits need not invalidate every cached artifact.

Quarantine and revocation must invalidate dependent compiled influence as well as visible graph state. Removing a vector does not retroactively remove text already generated under it; independent trials must also restore or reset their conversation and inference state. [P1]

### Cache misses must not erase the distant thoughts SAA was built to admit

A novel, rarely used neighborhood is especially likely to miss the cache. Consequently, cache convenience must not become a hidden relevance gate or a reason to resample the SAA lottery.

For a declared hybrid operational mode, the existing text backend could carry the same selected influence while neural construction is deferred. Mark that generation as text-mediated. In a **neural-only experiment**, a missing qualified intervention must be recorded as unavailable treatment, not silently replaced with text or interpreted as behavioral failure.

Compile during explicitly scheduled maintenance or accept measured first-use latency. Bound construction cost and log rejected candidates so the same failed compilation is not retried indefinitely. An effective cache needs measured hit rates, not optimistic assumptions about concept reuse.

## 7. Constructing the first candidate without mapping a whole model

Select one small earned neighborhood from a frozen developmental snapshot. Define, before evaluation, the observable framing that the translator is meant to make available. Do not hand-author a personality or demand a literal callback.

Create a modest, varied contrast set in which that framing is present versus absent while controlling topic, wording, and formatting as far as practical. Have the exact target host process the examples and record activations at a small predeclared set of candidate sites. Derive a difference-based candidate following a published method. [R1, R2]

The convenient shorthand is:

```text
candidate direction = average(with-framing activity - matched baseline activity)
```

That subtraction requires a specified correspondence between the measurements. Do not subtract unrelated tokens from independently generated answers and call the result a concept. Use a method-appropriate aligned position or pooled representation; prompt-replacement approaches can compare corresponding tokens under matched continuations. [R2, R3]

Calibrate a limited range of gains and locations on construction/validation examples, then freeze them for held-out testing. Keep the sign and magnitude of the intervention separate from the probability that SAA selected the neighborhood.

If this fails, diagnose whether the failure lies in the descriptor, contrasts, activation extraction, hook, or representation. Do not respond by mapping thousands more concepts or increasing pressure until a conspicuous word appears.

## 8. Scaling beyond the cache

A generalized translator could consume a portable neighborhood representation, perhaps together with host context, and emit a candidate intervention directly. Qualified cached examples could become one source of training data, but no particular number of examples guarantees generalization.

HyperSteer is the main published reference for this direction; PSR addresses a complementary issue—how intervention strength should vary while a response is generated. Combining these ideas is a research proposal, not a published MNEME solution. [R3, R4]

The long-term interface might be:

```text
translator(active neighborhood, host context) -> bounded host-space intervention
```

Test genuinely unseen neighborhood descriptions, not just paraphrases of training examples. Do not claim generalization because the translator reconstructs its training vectors. A compressed shared translator may entangle its training sources: retain whole-version rollback and a rebuild path rather than promising exact deletion of one memory from its parameters. [P1]

Neither a large hypernetwork nor a comprehensive feature dictionary is required for the initial experiment. Prefer the smallest adequate translation mechanism, but do not label it lightweight until its actual memory, training, and inference costs are measured.

## 9. Gemma is a test host, not the destination

The **graph, source history, and conceptual definitions** are the portable layer in the design. Vectors, layer choices, gains, runtime hooks, and learned translator parameters are host-specific compiled material. [P1]

Moving to a larger or different host therefore means preserving the developmental source and establishing a compatible translator for the new host. It does **not** mean replaying an entire life as fresh evidence. It may still require significant new calibration or translator training. Matching tensor dimensions alone is not evidence that old vectors retain their meaning.

Larger hosts also make the forward passes used for compilation more expensive. A small output vector can be cheap to store while expensive to obtain. Avoid making full activation dumps the default; collect the sites and statistics needed by the chosen method.

Direct neural influence requires an execution environment that exposes internal activations. A service exposing only text generation is not automatically compatible. Retain the text backend as a distinct supported option rather than implying every future hosted model has a neural socket.

**Portability is a design goal and future test—not a promise that the same history will express an identical personality through every model.**

## 10. A small first experiment, not another hundred-thread campaign

The suggested entry study uses frozen developmental state and a few representative neighborhoods. It tests the interface before adding new development.

| Condition | What reaches the host |
|---|---|
| No influence | Ordinary prompt/context only. |
| Text SAA | Existing renderer's output for the selected state. |
| Neural SAA | Candidate internal intervention; no SAA text payload. |
| Matched random perturbation | An unrelated numerical nudge with matched site, timing, and norm. |

Reuse the same selected SAA state, host configuration, held-out prompts, and paired generation seeds across relevant conditions. Seeds control an input to randomness; they do not prove full determinism or make text and neural prompts identical. Explicitly label any optional hybrid condition.

The central question is whether the **direction and character of influence** follow the developed state, rather than merely whether output strings differ. Assess framing, salience, analogy, organization, and cross-domain transfer alongside coherence, repetition, instruction sensitivity, and obvious competence failures. Quality and uniqueness are separate observations; a distinctive but poor response is not automatically instrument failure or a desirable deployment outcome.

Check intervention removal/restoration, correct host binding, real nonzero exposure, and absence of cross-request carryover. Turning steering off without resetting affected inference caches or restoring the prescribed conversation is not a clean removal control. Freeze the cache or build all required candidates before the held-out measurement; cache growth during evaluation can otherwise change the treatment.

The experiment should have a finite calibration budget and a declared stopping point. A null or unstable translation result informs the next mechanism choice; it does not authorize endless layer searches until something amusing happens.

## 11. Proposed implementation order and open decisions

**First: establish one controlled neural path.** Verify the exact runtime hook, construct a small contrastive candidate, and compare it against text and random controls. Keep the existing development study untouched.

**Second: investigate reuse only if the first path is informative.** Add dependency-aware caching and measure first-use cost, hit rate, interference, and behavior on cache misses. Do not make an entire cache service a prerequisite for the first vector.

**Third: investigate learned translation when per-neighborhood construction becomes the measured bottleneck.** Study HyperSteer for generalization and PSR for token-dependent application. ReFT and compatible feature dictionaries remain alternatives, not mandatory extra phases.

Before implementation, Codex still needs to specify the exact descriptor, contrast construction, extraction site, injection timing, gain calibration, cache-miss policy, finite evaluation budget, and handling of multiple simultaneous contributions. In particular, adding two individually useful vectors need not preserve both effects; begin with a single neighborhood before assuming linear composition.

Do not silently redefine Phase Four's formal completion criteria. The governing specification asks for a bounded internal backend compared against the best text/graph baseline, including compatibility, competence, quarantine, and restoration. This brief proposes a tractable entry study; it does not declare Phase Three closed or all portability questions answered. [P1]

## 12. Instructions to carry into future Codex planning

This is a reference dossier, not permission to interrupt the current campaign. On the eventual Phase Four handoff, preserve the following:

- Keep SAA's history-shaped selection intact. Do not replace it with hand-selected traits, cache popularity, or relevance-only retrieval.
- Keep base weights frozen and any trained translator separate. Preserve source provenance and reverse or rebuild derived influence when its sources are revoked.
- Do not equate graph scores, text embeddings, and host activation coordinates. Verify both the translation and the runtime injection.
- Start with the existing small-vector path. Study the generalized translator as the scaling route, not as something Codex must invent unaided.
- Preserve unusual history-derived influence without demanding either maximal usefulness or conspicuous weirdness. Do not train a generic approval optimizer under the name of MNEME.

> **The first aim is not to translate every possible thought. It is to demonstrate a faithful translation path, then learn how to reuse and generalize it without losing the history that made the influence distinctive.**

---

## Source index and reading order

Inline labels distinguish project sources (**P**), external research (**R**), and inspected implementations (**I**). Architecture choices in Sections 5–11 are proposals unless explicitly attributed. External sources were checked on 2026-09-27; no neural intervention or compiler benchmark was executed for this brief.

### Project basis

**[P1] Governing specification.** *MNEME — Model Instance Development Through Earned Association*, supplied as `MNEME_Model_Instance_Development_Spec(2).md`, internal revision 2026-09-13. Read §§12.1–12.4 for backends, non-interchangeable representation spaces, the compiler contract, and reversibility; §16 for the Phase Four boundary.

**[P2] SAA amendment.** *Stochastic Associative Accessibility and Consequence-Shaped Geometry*, RA-SAA-2026-09-26, revision 1. Supplied as `MNEME_Research_Architecture_Amendment_Stochastic_Associative_Accessibility_2026-09-26(1).md`. Read §§4–8, 17–20, and 25–28 for selection, activation, expression, and experimental intent.

**[P3] Deformation-field amendment.** `MNEME_Research_Architecture_Amendment_Associative_Deformation_Field_2026-09-26(1).md`. Read §§9–13 for text controls, portable source state, and the later neural compiler target.

**[P4] R8 terminal receipt.** `p23-saa-ten-thread-20260927-r8`, archived at MNEME commit `72bc69bd78ec9d80de193c76a44dd0e716f862d8`. [Pinned receipt](https://github.com/nova-rey/mneme/blob/72bc69bd78ec9d80de193c76a44dd0e716f862d8/docs/receipts/MNEME_P2_SAA_Ten_Thread_Run_r8_20260927/TERMINAL_VALID.md). Historical text-mediated evidence, not a neural benchmark or the subsequent hundred-thread result.

**Owner discussion, 2026-09-27.** Source for this brief's intended direction: Gemma is a convenient test host; exhaustive manual mapping is undesirable; lazy compilation/caching and eventually a learned host-specific translator are candidates. Those preferences are not experimental findings.

### Research: start with R2 and R7; read R4 for the scaling question

**[R1] ActAdd.** Turner et al., *Steering Language Models With Activation Engineering*, arXiv:2308.10248v5, 2024 revision of the 2023 work originally titled *Activation Addition: Steering Language Models Without Optimization*. [Paper](https://arxiv.org/abs/2308.10248v5). Starting point for contrast-derived activation interventions.

**[R2] CAA.** Rimsky et al., *Steering Llama 2 via Contrastive Activation Addition*, ACL 2024, pp. 15504–15522. [Paper and publication record](https://aclanthology.org/2024.acl-long.828/). Starting point for averaging contrast pairs and testing behavior beyond construction examples.

**[R3] PSR.** Heyman and Vandeputte, *Steer Like the LLM: Activation Steering that Mimics Prompting*, arXiv:2605.03907v1, May 2026; arXiv records acceptance to ICML 2026. [Paper](https://arxiv.org/abs/2605.03907v1) · [Method, especially §§3.2–3.6](https://arxiv.org/html/2605.03907v1). Reference for prompt replacement and token-specific intervention strength.

**[R4] HyperSteer.** Sun et al., *HyperSteer: Activation Steering at Scale with Hypernetworks*, arXiv:2506.03292v1, June 2025. [Paper](https://arxiv.org/abs/2506.03292v1) · [Architecture, evaluation, and limitations](https://arxiv.org/html/2506.03292v1) · [Authors' code location: AxBench](https://github.com/stanfordnlp/axbench). Reference for generating interventions for unseen steering descriptions; inspect compute requirements before adopting.

**[R5] ReFT.** Wu et al., *ReFT: Representation Finetuning for Language Models*, arXiv:2404.03592v3, May 2024. [Paper](https://arxiv.org/abs/2404.03592v3) · [Authors' library: pyreft](https://github.com/stanfordnlp/pyreft). Reference for learned low-rank representation interventions.

**[R6a] Feature-steering demonstration.** Anthropic, *Golden Gate Claude*, May 2024. [Primary demonstration](https://www.anthropic.com/news/golden-gate-claude). Illustrates direct feature influence and pervasive fixation under strong amplification; not evidence of experience-shaped development.

**[R6b] Feature dictionaries.** Google DeepMind, *Gemma Scope*. [Official overview and release links](https://deepmind.google/models/gemma/gemma-scope/). Inspected coverage: Gemma Scope for Gemma 2; Gemma Scope 2 for Gemma 3. Recheck compatibility for the exact future host.

**[R7] Steering reliability.** Braun et al., *Understanding (Un)Reliability of Steering Vectors in Language Models*, arXiv:2505.22637v1, May 2025. [Paper](https://arxiv.org/abs/2505.22637v1). Read before treating a candidate vector as a reliable semantic control.

### Implementation starting points

The three llama.cpp references below use inspected upstream revision `97e4ca73582084f2751767f80c86237483ecc381`. This is **not** a claim about the MSI's installed revision.

**[I1] Control-vector generation and CLI application.** [llama.cpp cvector-generator README](https://github.com/ggml-org/llama.cpp/blob/97e4ca73582084f2751767f80c86237483ecc381/tools/cvector-generator/README.md). Recheck executable names and flags against the actual build; do not copy example layer indices as universal defaults.

**[I2] Gemma 4 injection call.** [llama.cpp `src/models/gemma4.cpp`](https://github.com/ggml-org/llama.cpp/blob/97e4ca73582084f2751767f80c86237483ecc381/src/models/gemma4.cpp). Locate `build_cvec(cur, il)` and inspect the surrounding normalization, residual, and per-layer operations.

**[I3] Control-vector application.** [llama.cpp `src/llama-adapter.cpp`](https://github.com/ggml-org/llama.cpp/blob/97e4ca73582084f2751767f80c86237483ecc381/src/llama-adapter.cpp). Inspect `llama_adapter_cvec::apply_to` and `apply` for addition, dimensions, layer bounds, and disable behavior.

**[I4] PSR implementation.** [Nokia Bell Labs, steer-like-the-llm](https://github.com/Nokia-Bell-Labs/steer-like-the-llm). README inspected at blob `0f5a4f5508a9b04171e97eecec1524ff6b55ebb0`. Start in `src/ase/steering`; note `Focused`/`psi` naming. Its benchmark setup includes external services and additional repositories—consult the method without automatically installing the entire evaluation stack.

**End of brief.**
