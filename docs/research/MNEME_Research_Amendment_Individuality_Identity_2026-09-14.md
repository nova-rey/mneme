# MNEME — Research Amendment 01
## Developmental individuality, path dependence, and identity

**Research cutoff and review date:** 2026-09-14  
**Document type:** Additive research amendment; not a replacement specification or dossier  
**Project:** Model Instance Development Through Earned Association  
**Technical architecture:** Earned Association Field  
**Status:** Literature synthesis and experimental implications. No implementations or published experiments were reproduced for this amendment.

### How to use this amendment

Read this alongside **MNEME_Related_Work_Research_Dossier.docx** [P2] and the **2026-09-13 targeted revision of MNEME_Model_Instance_Development_Spec.md** [P1]. The original dossier remains useful for memory machinery. This amendment updates its interpretation of MNEME, adds the literature that interpretation requires, and qualifies several earlier comparisons. Neither original document is modified.

The specification governs project requirements. This amendment governs how the reviewed research should be used to support—or limit—claims about those requirements. Where the old dossier frames personality as something optimized through usefulness or approval, apply the clarification here and in the current specification.

**Source convention:** `[Rxx]` identifies new research; `[Lxx]` identifies a selectively rechecked legacy source; `[Pxx]` identifies a project document. Each research entry gives authors, a version or publication record, inspected sections, a finding, a limitation, and a separately labeled MNEME interpretation. Links are ordinary Markdown references so they remain usable outside this conversation.

---

## 1. What the new sweep changes

**The central phenomenon has closer prior art than the original dossier recognized.** Takata, Masumori, and Ikegami explicitly investigated agent individuality emerging without predefined personalities in a shared-LLM simulation. That is direct conceptual overlap, not merely another storage system. The broad idea of interaction-produced individuality should not be presented as unexplored. [R01]

**The measurement problem is substantial.** Favorable psychometric research and substantial methodological criticism both exist. An attractive MBTI or Big Five chart cannot, by itself, establish MNEME's developmental claim. [R06], [R07], [R08]

**Identity-related results answer different questions.** Stored self-description, predicting one's behavior, recognizing one's outputs, and detecting an injected internal representation are not interchangeable achievements. The relevant studies provide mixed and task-specific evidence, not a single verdict about a persistent self. [R11], [R12], [R13], [R14], [R15], [R16]

**Memory updating is part of the experiment, not neutral infrastructure.** Evidence about experience-following, repeated consolidation, and evaluator-mediated selection gives concrete reasons to test whether apparent development is actually stale imitation, lossy rewriting, or an inherited evaluator bias. [R17], [R18], [R19]

**Working assessment:** The reviewed literature supports pursuing a narrower MNEME contribution: controlled, persistent, instance-specific differentiation carried by inspectable developmental state, including own-output contributions and a revisable self-model. It does **not** establish that MNEME's complete mechanism works, nor that its combination is scientifically novel. That remains an empirical and broader prior-art question.

## 2. Amendment to the original dossier's framing

The governing question is now:

> Can initially identical, frozen language-model instances develop persistent individuality through external experience and their own path-dependent behavior, with continuity that supports an evolving self-model rather than an assigned persona? [P1], §1

The instance is the subject of development. A conversational partner is part of its environment, not the personality's reward function. “Earned” means supported by attributable developmental history; it does not mean every contribution was approved, correct, or useful. Own-output recurrence can support a habit without becoming independent evidence of truth. [P1], §§3.4, 4, 11

| Location in the original dossier | Amended interpretation |
| --- | --- |
| Purpose and executive takeaways | Memory is a mechanism for studying development, not the complete research objective. |
| “What appears genuinely distinctive” | Treat listed distinctions as design commitments and candidate contributions, not established novelty. Add direct individuality prior art. |
| Utility and reinforcement comparisons | Separate developmental support, task consequences, and user reaction. Do not optimize individuality for partner satisfaction. |
| Style and intrusion discussion | Characteristic style is a legitimate outcome. Contextual interference and uncontrolled repetition are separate problems. |
| Experimental ladder | Measure persistent differences and transfer alongside competence. Add shared-input development, own-output ablations, exact replay, and identity continuity. |
| Neural-backend stop rule | A field must justify itself through development, generalization, control, or efficiency. Equal factual accuracy alone does not settle its value. |
| Identity-related interpretation | Distinguish lineage, explicit self-state, behavioral traits, and deeper self-recognition. Cryptographic identity remains out of scope. |

These changes follow the current specification, especially §§3–7 and §§14–16. They are not additional claims derived from the papers. [P1]

### A substantive correction: SEAL and the frozen-base distinction

The original dossier contrasted SEAL with MNEME by saying SEAL changes the model's own weights. That captures SEAL's adaptation objective, but is too coarse as an implementation distinction: its documented experiments use **LoRA adaptation**. [L04], Appendices A–B

Consequently, “our learning is in a separate adapter” or “the underlying base tensors are frozen” is not enough to distinguish MNEME from existing adaptation methods. The useful comparison concerns **what is learned, from which evidence, toward which objective, with what lifecycle and provenance**. MNEME itself permits adapter learning; the specification already acknowledges this. [P1], §§3.3, 12

---

## 3. Search scope and evidence discipline

This was a **targeted research sweep**, not an exhaustive systematic review. Searches covered emergent LLM individuality, memory-conditioned behavioral development, shared-environment divergence, social convention formation, adaptive personas, developmental AI, self-models, self-recognition, behavioral measurement, activation steering, and memory-feedback failure modes. Historical foundations and sources available through the review date were included.

Primary papers, author manuscripts, official proceedings, and original research reports were prioritized. Search snippets and aggregators were discovery aids, not substitutes for the methods and limitations in the selected papers. For the main entries below, full-text sections were inspected; where publisher access failed, an author manuscript or indexed publication record is identified. This is not a claim to have audited every appendix or reproduced each result.

**Evidence labels used here:**

- **Direct, bounded evidence:** The work tests a relevant operation, under its own specified conditions.
- **Partial or adjacent evidence:** It supports a component or neighboring phenomenon but not the full MNEME claim.
- **Proposal or preview:** The architecture is described, but the relevant developmental claim is not adequately tested.
- **Negative evidence on a method:** A particular measurement or mechanism fails in reported settings; that does not disprove all possible individuality mechanisms.

A preprint is labeled as such where a reviewed publication record was not established. “Not demonstrated in the reviewed sources” never means “nobody has done it.” Reported findings remain the authors' findings, not verified MNEME results.

### Reading priorities

| Question | Start here | Why this group matters |
| --- | --- | --- |
| Has unassigned individuality already been studied? | R01; then R02–R03 | Direct overlap and contrasting population dynamics. |
| How could a personality result fool us? | R06–R08 | Favorable measurement work alongside methodological objections. |
| Can a frozen host be behaviorally influenced internally? | R09–R10 | Concrete intervention and internal-measurement methods. |
| What does “knowing itself” actually test? | R11–R16 | Recognition, prediction, intervention, and explicit self-state separated. |
| What might the developmental loop damage? | R17–R19 | Dependence on remembered outputs, rewriting, and selection bias. |
| What is a strong simpler alternative? | R03–R04; L01–L04 | Reflection, dynamic persona control, retrieval, and adaptation baselines. |

---

## 4. Individuality, social history, and developmental alternatives

### R01. Spontaneous Emergence of Agent Individuality through Social Interactions in LLM-Based Communities

**Authors:** Ryosuke Takata, Atsushi Masumori, Takashi Ikegami.  
**Record:** November 2024 preprint; published as *Spontaneous Emergence of Agent Individuality Through Social Interactions in Large Language Model-Based Communities*, **Entropy 26(12), 1092 (2024)**.  
**Primary:** [Author manuscript][R01] · [Journal/DOI](https://doi.org/10.3390/e26121092)  
**Inspected:** Manuscript §§2.1–2.3 and §§3.1–3.5; publication metadata and discussion. **Evidence:** Direct conceptual overlap; partial experimental match.

**Reported finding:** Ten agents use a common Llama-2-7B-chat model, local communication, movement, and evolving memory summaries without predefined personalities. The authors report differentiation in behavior and personality-test responses during the simulation.

**Boundary:** Agent identifiers and locations enter prompts; initial positions and later inputs differ. This is not MNEME's tightly matched replay condition. The measurements do not establish cold-start, cross-domain behavioral fingerprints with state removal and restoration.

**MNEME interpretation:** Make this a first-read precedent and design comparator. Borrow the minimal social-development setup, but strengthen controls before claiming persistent individuality rather than in-context differentiation. The novel contribution cannot simply be “agents develop different personalities without assigned personas.”

### R02. Emergent Social Conventions and Collective Bias in LLM Populations

**Authors:** Ariel Flint Ashery, Luca Maria Aiello, Andrea Baronchelli.  
**Record:** **Science Advances 11, eadu9368 (2025)**; inspected arXiv v2, 29 May 2025.  
**Primary:** [Full text][R02] · [Journal/DOI](https://doi.org/10.1126/sciadv.adu9368)  
**Inspected:** Convention-formation and collective-bias experiments; supplementary prompting and naming-game methods. **Evidence:** Direct for collective dynamics; adjacent for individual development.

**Reported finding:** Decentralized agents playing a naming game converge on shared conventions. Their memories contain earlier interactions and outcomes. Collective preferences can develop even when individual initial tests do not show the same bias.

**Boundary:** The environment supplies a coordination objective and payoff structure. Population consensus is not evidence that each agent develops a distinctive, general personality.

**MNEME interpretation:** Measure convergence as well as divergence. A developmental loop can favor shared attractors; do not build the evaluator so only increasing difference counts as an acceptable result. Social interaction alone does not guarantee individuality.

### R03. Generative Agents: Interactive Simulacra of Human Behavior

**Authors:** Joon Sung Park and colleagues.  
**Record:** 2023 research paper; inspected arXiv v2.  
**Primary:** [Full text][R03]  
**Inspected:** Agent initialization; memory stream, retrieval, reflection, planning, and evaluation sections. **Evidence:** Architectural and behavioral precedent with seeded identities.

**Reported finding:** The system combines remembered observations, synthesized reflections, and plans to support continuing behavior and coordination among simulated agents.

**Boundary:** Agents begin with supplied descriptions and identities. The experiment is not a demonstration that identical empty-state instances acquire unassigned personalities.

**MNEME interpretation:** Use reflection-plus-memory as a serious baseline, not a straw man. A compact history-derived reflection might reproduce much of a graph's influence. If it does, that can still be development; it changes which representation is justified. Compare retention, generalization, controllability, and provenance rather than dismissing text-mediated behavior as unreal.

### R04. Dynamic Personality Adaptation in Large Language Models via State Machines

**Authors:** Leon Pielage, Ole Hätscher, Mitja Back, Bernhard Marschall, Benjamin Risse.  
**Record:** Preprint, arXiv:2602.22157v1, 25 February 2026.  
**Primary:** [Full text][R04]  
**Inspected:** State-machine framework and medical-education/de-escalation evaluation. **Evidence:** Direct for designed personality adaptation; not organic development.

**Reported finding:** A controller scores dialogue and changes a model's prompted interpersonal state. The design uses specified personality dimensions and transitions rather than a permanently fixed persona prompt.

**Boundary:** The available states and adaptation logic are authored. Responsive demeanor is not the same as open-ended accumulation of instance-specific habits.

**MNEME interpretation:** Add a dynamic-persona alternative when comparing mechanisms. Beating a static “you are quirky” instruction is a weak test if a small state machine explains the observed effect equally well. This comparison should assess representational economy without redefining MNEME as user-approval optimization.

### R05. Language and Culture Internalisation for Human-Like Autotelic AI

**Authors:** Cédric Colas, Tristan Karch, Clément Moulin-Frier, Pierre-Yves Oudeyer.  
**Record:** Developmental-AI perspective; inspected arXiv:2206.01134v2 (2022). Associated Nature Machine Intelligence DOI below.  
**Primary:** [Author PDF][R05] · [Journal/DOI](https://doi.org/10.1038/s42256-022-00591-4)  
**Inspected:** Abstract/introduction and language-internalisation discussion; PDF pages 1 and 5, including Figure 2. **Evidence:** Conceptual foundation, not an MNEME experiment.

**Contribution:** The authors discuss agents that generate and pursue goals, with socially acquired language becoming part of their own cognitive processes. This offers an older developmental framing beyond externally assigned task rewards.

**Boundary:** It does not demonstrate persistent individuality in frozen LLM siblings, nor provide MNEME's association-update rule.

**MNEME interpretation:** Place endogenous developmental contributions in this broader lineage. Do not infer that V1 needs autonomous goal pursuit, embodied robotics, or a continuous loop. The conceptual connection is useful without importing the entire research program.

---

## 5. Measuring personality without manufacturing it

### R06. Personality Traits in Large Language Models / A Psychometric Framework for Evaluating and Shaping Personality Traits in Large Language Models

**Authors:** Gregory Serapio-García and colleagues.  
**Record:** Author manuscript arXiv:2307.00184v4, 11 March 2025; journal version indexed in **Nature Machine Intelligence (2025)** under the second title.  
**Primary:** [Inspected manuscript][R06] · [Journal/DOI](https://doi.org/10.1038/s42256-025-01115-6)  
**Inspected:** Summary, assessment methodology, and reliability/construct-validity sections and appendices; journal bibliographic record. **Evidence:** Favorable but conditional measurement findings.

**Reported finding:** Across 18 evaluated models, the authors find reliable and valid output-level personality measurements for some models under specified prompting configurations. They also demonstrate deliberate trait shaping.

**Boundary:** This does not validate every questionnaire on every model. Prompted trait shaping is not evidence of unassigned developmental individuality.

**MNEME interpretation:** Borrow the demand for reliability and construct validity, not the assumption that a human inventory automatically measures our target. Include this favorable result alongside R07–R08 rather than treating the literature as uniformly dismissive.

### R07. Self-Assessment Tests Are Unreliable Measures of LLM Personality

**Authors:** Akshat Gupta, Xiaoyang Song, Gopala Anumanchipalli.  
**Record:** Preprint first released in 2023; inspected arXiv:2309.08163v2.  
**Primary:** [Full text][R07]  
**Inspected:** Prompt-template and response-option perturbation experiments; discussion. **Evidence:** Negative evidence on a measurement method.

**Reported finding:** Personality estimates change materially under alterations such as equivalent prompt templates and reordered answer choices.

**Boundary:** Instability of self-assessment instruments does not establish that all persistent output tendencies are imaginary.

**MNEME interpretation:** Test measurement invariance explicitly: paraphrase items, reverse appropriate items, balance response positions, and repeat assessments. A classifier recognizing an instance across held-out tasks asks a different question from a model selecting “agree” on a personality inventory. Neither should substitute for the other without validation.

### R08. Apparent Psychological Profiles of Large Language Models Are Largely a Measurement Artifact

**Authors:** Jelena Meyer, David Garcia, Dirk U. Wulff.  
**Record:** Preprint, arXiv:2606.20205v1, 18 June 2026.  
**Primary:** [Full text][R08]  
**Inspected:** Response-bias decomposition, model comparisons, item-selection analysis, and discussion. **Evidence:** Recent methodological challenge.

**Reported finding:** In tests involving 56 instruction-tuned models, the authors attribute much apparent profile variation to directional response bias. High internal consistency can coexist with misleading trait interpretation; item selection can substantially change resulting profiles.

**Boundary:** The study concerns particular psychological instruments and their response structures, not every possible behavioral-individuality measure.

**MNEME interpretation:** Do not use stable scores alone as proof of stable traits. Separate observed choices from the scale used to label them. The main readout should include unfamiliar tasks and observable behavior, with questionnaire scores treated as supplementary and challenged by nuisance controls.

### R09. Persona Vectors: Monitoring and Controlling Character Traits in Language Models

**Authors:** Runjin Chen, Andy Arditi, Henry Sleight, Owain Evans, Jack Lindsey.  
**Record:** 2025 research report; inspected arXiv:2507.21509v3 and the authors' research overview.  
**Primary:** [Paper][R09] · [Author research report](https://www.anthropic.com/research/persona-vectors)  
**Inspected:** Vector extraction, monitoring, steering, limitations, and Appendix G. **Evidence:** Direct intervention machinery; adjacent developmental evidence.

**Reported finding:** Contrast-derived activation directions can monitor and influence selected behavioral traits. The reported model experiments include Qwen2.5-7B-Instruct and Llama-3.1-8B-Instruct; inference-time steering is distinct from the paper's fine-tuning experiments.

**Boundary:** Traits and contrasts are deliberately specified. A useful steering direction is not a graph-to-field compiler or evidence that an identity developed organically.

**MNEME interpretation:** This is a concrete starting reference for a later frozen-host intervention backend. Keep it separate from the developmental learner: first observe what develops, then test whether a calibrated direction represents or influences it. Do not impose these authors' trait categories as MNEME's destination.

### R10. Stable and Explainable Personality Trait Evaluation in Large Language Models with Internal Activations

**Authors:** Xiaoxu Ma, Xiangbo Zhang, Zhenyu Weng.  
**Record:** **Findings of ACL 2026**, pp. 16322–16340; inspected arXiv:2601.09833v1 and official proceedings record.  
**Primary:** [Full text][R10] · [ACL publication](https://aclanthology.org/2026.findings-acl.803/)  
**Inspected:** Method, evaluation, and limitations, especially §§3, 5, 7. **Evidence:** Candidate internal measurement method.

**Reported finding:** The proposed Persona-Vector Neutral Interpolation method uses internal activations to estimate traits and reports improved stability under evaluated prompt and role-play variations.

**Boundary:** It requires internal access and constructed trait directions. The authors discuss limitations involving judge bias, the placement of a neutral state, and interactions among directions.

**MNEME interpretation:** Use internal measurements as a second instrument, not a replacement for behavior. A stable projection may measure the chosen axis reliably while still failing to capture the developmental phenomenon. Agreement between independent readouts would be more informative than one attractive vector visualization.

---

## 6. Identity, self-prediction, and self-recognition

### R11. LLM Evaluators Recognize and Favor Their Own Generations

**Authors:** Arjun Panickssery, Samuel R. Bowman, Shi Feng.  
**Record:** 2024 author manuscript; inspected arXiv:2404.13076v1.  
**Primary:** [Full text][R11]  
**Inspected:** §§2–3 and §5.2, including ordering controls and limitations. **Evidence:** Positive, task-bounded recognition findings and evaluator-bias evidence.

**Reported finding:** In summarization experiments, models show some ability to distinguish their outputs from other sources. Fine-tuning interventions connect stronger recognition with stronger self-preference, with controls addressing several alternative explanations.

**Boundary:** Results depend on the recognition setting. The authors do not establish the full causal mechanism at individual-example level. Distinguishing different model families' summaries is not identifying developed siblings of one frozen host.

**MNEME interpretation:** Preserve this positive evidence rather than claiming self-recognition never works. Also avoid using the developing instance as its own sole quality judge: familiarity and preference can become entangled with evaluation. Test source identification and answer quality separately.

### R12. Self-Recognition in Language Models

**Authors:** Tim R. Davidson and colleagues.  
**Record:** **Findings of EMNLP 2024**, pp. 12032–12059; inspected arXiv:2407.06946v2.  
**Primary:** [Full text][R12] · [ACL publication](https://aclanthology.org/2024.findings-emnlp.703/)  
**Inspected:** Self-recognition setup, response-selection analyses, and conclusions. **Evidence:** Negative or confounded recognition results in a different protocol.

**Reported finding:** Across ten evaluated models, apparent recognition is not consistently explained by identifying the model's own output. Preference for better responses and positional effects provide important alternative explanations.

**Boundary:** This is not the same summarization protocol as R11. Treat their difference as a reason to inspect task definitions, not select whichever conclusion favors MNEME.

**MNEME interpretation:** Match candidate outputs for quality, randomize presentation order, and distinguish “which answer would you prefer?” from “which answer originated from this instance?” Cryptographic framing from neighboring work is unnecessary for our behavioral test.

### R13. Know Thyself? On the Incapability and Implications of AI Self-Recognition

**Authors:** Xiaoyan Bai, Aryan Shrivastava, Ari Holtzman, Chenhao Tan.  
**Record:** Preprint, arXiv:2510.03399v1, 3 October 2025.  
**Primary:** [Full text][R13]  
**Inspected:** Recognition tasks, attribution-bias analysis, and prompting appendices. **Evidence:** Additional negative, protocol-specific findings.

**Reported finding:** Ten evaluated models struggle with own-output recognition and exact model-source attribution. Their answers exhibit model-identity priors, including attributing strong text to prominent model families.

**Boundary:** These tasks neither prove an intrinsic impossibility of self-recognition nor test MNEME's persistent sibling-state construction. Avoid turning a negative benchmark into a metaphysical conclusion.

**MNEME interpretation:** Include unfamiliar sibling outputs and remove brand/name cues. A self-model saying “I am Nova” must not be credited for identifying Nova-like behavior unless that prediction is tested independently. Report recognition failures without treating basic identity persistence as a failed feature.

### R14. Looking Inward: Language Models Can Learn About Themselves by Introspection

**Authors:** Felix J. Binder and colleagues.  
**Record:** **ICLR 2025**; inspected author manuscript arXiv:2410.13787v1, 17 October 2024, and proceedings record.  
**Primary:** [Full text][R14] · [ICLR publication](https://proceedings.iclr.cc/paper_files/paper/2025/hash/0a6059857ae5c82ea9726ee9282a7145-Abstract-Conference.html)  
**Inspected:** §§3–4 and §6, especially cross-prediction and changed-behavior tests. **Evidence:** Positive, bounded self-prediction results with training.

**Reported finding:** Fine-tuned models predict some aspects of their own behavior better than other models trained on the same target behavior. The advantage includes some induced behavior changes, but does not extend successfully to all complex or out-of-distribution tasks tested.

**Boundary:** This uses fine-tuning, not MNEME's proposed graph-backed developmental process. Prediction accuracy is different from name recall or authorship recognition.

**MNEME interpretation:** Borrow the behavioral calibration test: ask what an instance will tend to do, then measure what it actually does. An observed tendency provides a stronger test of self-description than repeated autobiography.

### R15. Emergent Introspective Awareness in Large Language Models

**Author:** Jack Lindsey.  
**Record:** Author research paper; inspected arXiv:2601.01828v1, 5 January 2026.  
**Primary:** [Full text][R15]  
**Inspected:** Concept-injection, prior-output attribution, and internal-control experiments; discussion and limitations. **Evidence:** Causal intervention evidence about limited access to internal state.

**Reported finding:** Some tested models can, under some conditions, report or respond to deliberately injected internal concept representations. The paper also explores distinctions between intended output and artificially supplied output. The reported abilities are unreliable and context-dependent.

**Boundary:** A within-run response to an activation intervention is not a persistent self-model, acquired personal history, or proof of subjective awareness.

**MNEME interpretation:** Keep this as a later experimental-method reference. It suggests ways to test an intervention against a known cause rather than taking fluent introspective claims literally. It does not make advanced introspection a dependency for V1 identity storage.

### R16. SCM: Sleep-Consolidated Memory with Algorithmic Forgetting for Large Language Models

**Author:** Saish Sachin Shinde.  
**Record:** Research preview/preprint, arXiv:2604.20943v1, 22 April 2026.  
**Primary:** [Full text][R16]  
**Inspected:** §§3.7–3.8, benchmark design, and especially §4.4. **Evidence:** Close architectural proposal with limited validation.

**Reported contribution:** SCM places a self-model node within a persistent memory graph, with supplied capability information and runtime-state information. It is implemented around existing models rather than requiring foundation-model pretraining.

**Boundary:** Its self-label and capabilities are seeded. The paper explicitly acknowledges that its factual-recall evaluation does not establish the functional benefit of the self-model and REM components. It also states that source code is not publicly available.

**MNEME interpretation:** A self-node in a memory graph is already prior art. MNEME must test continuity, evidence-qualified self-description, and revision rather than claiming the node's existence demonstrates developed identity. Borrow the architectural comparison while keeping the evidence grade modest; biological terminology is not independent validation.

---

## 7. Developmental feedback and memory failure modes

### R17. How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior

**Authors:** Zidi Xiong and colleagues.  
**Record:** Preprint, arXiv:2505.16067v1, 21 May 2025.  
**Primary:** [Full text][R17]  
**Inspected:** Experience-following experiments and memory-management comparisons. **Evidence:** Direct evidence of memory-conditioned behavior and its failure modes.

**Reported finding:** Remembered experiences can strongly bias subsequent decisions, including reuse of mistakes or contextually unsuitable actions. The study compares memory addition and deletion rather than assuming more accumulated experience is always better.

**Boundary:** Following stored examples is not itself generalized individuality. The work primarily concerns task performance, not unscripted identity development.

**MNEME interpretation:** Include raw episodic retrieval and stale-example probes in the baseline suite. A persistent behavioral pattern may simply be repeated experience-following; test whether it transfers appropriately and yields to changed task conditions. Developmental strength should not overwrite correctness evidence.

### R18. Useful Memories Become Faulty When Continuously Updated by LLMs

**Authors:** Dylan Zhang and colleagues.  
**Record:** Preprint, arXiv:2605.12978; **v2, 29 August 2026**, inspected.  
**Primary:** [Versioned full text][R18]  
**Inspected:** §§3–6 and extended experiments in Appendix L. **Evidence:** Recent empirical warning about repeated consolidation.

**Reported finding:** Repeated textual consolidation can reduce later task performance even when source trajectories are useful or correct. Update schedule matters, and retaining raw episodes is a competitive control. The revised version adds repeated-run and attribution analyses.

**Boundary and source-quality note:** The inspected version's abstract and body use inconsistent headline failure/accuracy percentages. No headline percentage is reused here. The qualitative result should not be generalized into “all consolidation fails.”

**MNEME interpretation:** Preserve episode evidence and test rewrite schedules independently of developmental histories. Compare no consolidation, controlled consolidation, and repeated rewriting before attributing divergence to a meaningful habit. A changing summary can manufacture apparent change without healthy development.

### R19. Memory Contagion: Cross-Temporal Propagation of Evaluator Bias via Agent Memory

**Author:** Zewen Liu.  
**Record:** Exploratory preprint, arXiv:2606.23195v1, 22 June 2026.  
**Primary:** [Full text][R19]  
**Inspected:** §§3–5 and Appendix A.6. **Evidence:** Preliminary, limited-domain feedback-bias results.

**Reported finding:** Evaluator-biased selection of trajectories can transmit preferences through later stored memory, including when the consolidation step is controlled. Length-bias findings are more consistent than the authority-bias results, which vary by domain and replication condition.

**Boundary:** The experiments use one model; some favorable authority-bias evidence is single-run, and multi-seed synthetic tests do not reproduce it. Other selected properties may confound attribution.

**MNEME interpretation:** Log who selected an episode and why. An evaluator's preference can become part of an instance's history without the user explicitly asking for that trait. Do not treat an independent-looking evaluator as a neutral environmental sensor by default.

---

## 8. Updated evidence map

This map grades the **specific claim in the row**, not an entire research field. The A–H labels are dossier-navigation labels; they are not replacements for the specification's H1–H8.

| Claim | Assessment from this review | Relevant sources | What MNEME still must test |
| --- | --- | --- | --- |
| **A. External/adaptive memory can affect a frozen host.** | Direct architectural precedent for the narrow claim. | L01; R03 | Reliable integration and behavior under MNEME's own state rules. |
| **B. Structured associative retrieval can improve selected retrieval tasks.** | Direct, task-bounded evidence. | L02–L03 | Whether its selection mechanism supports developmental individuality rather than better recall alone. |
| **C. Post-deployment history can change later behavior.** | Supported through several memory/adaptation mechanisms; persistence and generalization vary. | R01–R03, R17; L04 | Durable effects across fresh conversations and unfamiliar tasks under controlled snapshots. |
| **D. Unassigned agent individuality can emerge through interaction.** | Partial direct prior art, not merely a speculative analogy. | R01 | Deconfounded, cross-domain individuality among otherwise matched instances. |
| **E. Shared external inputs plus own-output history can produce persistent sibling differences.** | Adjacent evidence; the full specified shared-input and frozen-checkpoint protocol was not established in the reviewed sources. | R01–R02 | Own-output causality, seed controls, structured persistence, and convergence alternatives. |
| **F. An instance can retain and revise a self-model.** | Explicit self-state has architectural precedent; deeper prediction/recognition evidence is mixed and task-specific. | R11–R16 | Separate cold-start persistence, justified revision, calibrated self-description, and optional deeper recognition. |
| **G. Developmental individuality can be removed, restored, and transferred with a separable sidecar.** | State serialization is an engineering operation; the complete causal individuality claim was not verified here. | P1 defines the test; L01 and R09 provide adjacent machinery | Whether a held-out fingerprint follows the developmental snapshot rather than labels, host identity, transcript, or process. |
| **H. Graph-backed developmental history can be compiled into neural influence with useful provenance.** | Relevant steering machinery exists; the graph-to-field developmental compiler remains unestablished in this review. | R09–R10; P1 | Alignment, retained competence, comparison to text, attribution, and rollback/rebuild semantics. |

**Connection to the current hypotheses:** D addresses part of H1; E addresses H6–H7; F addresses H8; G strengthens attribution for H1–H2; H is central to H5. Measurement work bears on all of them. H3–H4 require competence and learning-rule tests that these component precedents do not settle. [P1], §14.1

No broad MNEME hypothesis is marked “contradicted” solely because a particular questionnaire, recognition task, or consolidation method fails. Conversely, success on a component is not promoted into evidence for the whole architecture.

## 9. What “identity evidence” should mean going forward

The following is a **proposed interpretation of the literature for MNEME**, consistent with the specification, not a new universal theory of identity.

| Operation | Example measurement | Insufficient substitute |
| --- | --- | --- |
| **Continuity of explicit self-state** | Correct adopted name and permitted history after clearing conversation context. | Repeating a name supplied in the test prompt. |
| **Self-model accuracy** | Compare an evidence-qualified self-description with independently measured tendencies. | Repeatedly declaring the same trait. |
| **Self-prediction** | Predict choices on held-out prompts, then compare predictions with actual outputs. | A plausible autobiographical explanation. |
| **Behavioral individuality** | A blinded evaluator distinguishes sibling states across new tasks, after cue controls. | Different model families, names, catchphrases, or random samples. |
| **Own-output recognition** | The instance identifies its own products among quality-matched alternatives. | Selecting the best answer or the most familiar brand style. |
| **Causal internal-state reporting** | A known intervention changes a report in a controlled way. | Fluent claims of introspection without an external check. |

The first operation is enough to justify a basic identity feature. It does not need to wait for the last operation. The reviewed recognition findings [R11], [R12], [R13], self-prediction results [R14], intervention results [R15], and explicit graph self-model [R16] should be cited for their respective tasks, not combined into a blanket claim that models either “have” or “lack” selves.

An intentional name choice establishes an adopted label under the system's policy. It is not evidence that the name's associations describe the instance's behavior. A rename can be a valid state transition without demonstrating a feeling of resonance. Those distinctions preserve the project's intended identity continuity without requiring unsupported claims about subjective experience. [P1], §§5.6, 10.10, 14.7

## 10. Research implications for the roadmap

These are recommendations for the upcoming roadmap, **not another architecture rewrite**. The current specification already anticipates many of them; the sweep supplies reasons to retain and prioritize those controls.

### 10.1 Treat direct prior art as a comparator, not a threat

Use R01 to ask what additional evidence a MNEME prototype supplies. The desired contribution is not that agents sometimes differ. It is a better-controlled developmental process and demonstration, potentially with an inspectable association representation. Prior work reduces uncertainty about the broad phenomenon without validating our particular implementation.

### 10.2 Keep development and measurement separate

Do not feed the desired fingerprint or personality-test score back as the developmental objective. That would train the answer into the experiment. Reserve unseen prompts and separate evaluation random streams; freeze developmental state during readout. Label a trait only after behavior supports the label, and test whether supplying that label back to the model changes the result. [P1], §§7, 14; methodological motivation: [R06], [R07], [R08], [R09], [R10]

A practical readout should combine observable explanatory choices, cross-task identification, sensitivity to current instructions, competence, and repetition. Each can be informative without pretending to be a human psychological inventory. The reader that assigns identity labels and the rule that updates memory should not be the same unchecked loop.

### 10.3 Keep the two twin experiments and the exact-replay control

Different-environment development, shared external prompt sequences, and interactive environments answer different causal questions. Hold everything deterministic when testing reproducibility; introduce independently sampled development when testing path dependence. Evaluate developed snapshots with paired seeds and repeated trials, not a demand that every answer differ. [P1], §§3.5, 14.2

Include an own-output masking condition, and distinguish generation randomness from extractor or summarizer randomness. Divergence caused entirely by a noisy memory editor is not the same claim as development shaped by the host's prior behavior. This is an experimental distinction, not a presumption that only one source of variability is legitimate.

### 10.4 Make raw episodes and memory editing separate experimental factors

Preserve the distinction between source events and their interpretation. Compare episodic-only memory, graph selection, history-derived summaries, and repeated consolidation under matched histories and budgets. Add provenance for episode selection as well as graph insertion. The goal is not to prevent all endogenous reinforcement; it is to tell whether an apparent tendency came from behavior, memory rewriting, or an evaluator's selection rule. [P1], §§10–11; [R17], [R18], [R19]

### 10.5 Put basic identity into V1; keep stronger claims optional

Test name adoption, deliberate revision, fresh-conversation access, ancestry, forks, and restoration as state-management properties. A graph-backed self-model is a reasonable implementation choice, not evidence of self-awareness. Save self-prediction and own-output recognition for separately scored experiments. Do not make the first wrapper depend on solving them. [P1], §§5, 13.5, 14.7; [R11], [R12], [R13], [R14], [R15], [R16]

### 10.6 Let simpler methods compete fairly

The reference stack should include no memory, raw episodic retrieval, graph memory, a history-derived persona/reflection summary, and eventually dynamic persona control and neural influence. Match evidence access and explain differences in token or compute budgets. Not every baseline needs to be implemented on day one; the roadmap should select the smallest comparison capable of resolving the next claim. [P1], §§14.3, 16; [R03], [R04], [R09]; [L01], [L02], [L03], [L04]

If a summary matches a developed graph, that may demonstrate compressible development. If a neural vector changes behavior, that demonstrates an intervention. Neither result alone establishes or refutes organic individuality. The experiment must identify which claim it actually tested.

---

## 11. Selectively rechecked legacy sources

This is a limited verification and interpretation pass, **not a fresh audit of every source or performance claim in the original dossier**. The existing entries for Titans/MIRAS, MemoryLLM, Larimar, MemoryBank, Memorizing Transformers, Memory Layers at Scale, Memory³, and Graphiti remain background references in [P2]; their full methods and numerical claims were not re-audited for this amendment.

| ID and source | What was checked | Current role in MNEME |
| --- | --- | --- |
| **L01 — LongMem**, Wang et al., 2023 | Primary abstract: frozen backbone as encoder; trained residual side-network for retrieval/reading. | Frozen-host integration precedent, not proof of developmental individuality. |
| **L02 — A-MEM**, Xu et al., 2025 | Primary abstract and NeurIPS 2025 record, arXiv v11: structured notes and evolving links. | Candidate graph-memory baseline. |
| **L03 — HippoRAG**, Gutiérrez et al., 2024 | Primary abstract and NeurIPS 2024 record, arXiv v3: graph/PageRank retrieval and multi-hop QA evaluation. | Associative-retrieval baseline with task-scoped evidence. |
| **L04 — SEAL**, Zweiger et al., 2025 | Full v1 methods and LoRA training appendices; metadata also shows v2. | Outcome-directed adaptation comparator; not cleanly excluded just because MNEME also freezes base tensors. |
| **L05 — TTT**, Sun et al., ICML 2025 | Original proceedings link and canonical title. | Correct title: *Learning to (Learn at Test Time): RNNs with Expressive Hidden States*. The existing dossier URL is valid. |
| **L06 — M+**, Wang et al., ICML 2025 | Proceedings record and corresponding arXiv identifier. | The dossier's proceedings link and arXiv:2502.00592 refer to the intended work; no replacement citation is needed. |

The important change is interpretive: references about retention, retrieval, parameter-efficient adaptation, or steering support mechanisms. They do not automatically establish a history-shaped individual or a provenance-preserving compiler.

## 12. Coverage limits and unresolved leads

**Publication versus manuscript:** Where a journal or conference record is supplied alongside an arXiv manuscript, the card identifies the version actually inspected. A publication record verifies bibliographic status; it does not imply that every change in the final publication was compared with the manuscript.

**A particularly relevant unassessed lead:** *The Narrative Self, Instantiated: Memory Architecture Creates Persistent Identity in Stateless AI Systems*, attributed to Shehzad Ahmed, surfaced with [SSRN DOI 10.2139/ssrn.6407978](https://doi.org/10.2139/ssrn.6407978). The primary SSRN page was not retrievable in this review. It is recorded as a follow-up lead, **not used as evidence**, and its reported experimental claims are not adopted here.

**Intentionally excluded:** Marketing assertions about conscious agents; authentication or watermarking papers treated as personality evidence; behavioral classifiers that only distinguish unrelated base-model families; and user-cloning systems treated as equivalent to instance-centered development. Adjacent work can be useful, but should enter through the specific operation it tests.

**Unverified implementation details:** No linked repository was installed, no model was run, no benchmark was reproduced, and no license or hardware suitability audit was performed. The amendment identifies research references, not a ready-to-deploy software bill of materials.

**What remains insufficient:** The reviewed sources do not jointly supply a demonstrated system with the full MNEME specification's shared-input developmental controls, generalized sibling fingerprints, evolving self-model, graph-backed neural compilation, and state-transfer attribution. That is a gap in the evidence assembled here—not a claim that MNEME is first, or that those goals are impossible.

---

## 13. Source register

All external sources below were reviewed or bibliographically checked on **2026-09-14** to the extent stated in their entries. Versioned links identify the inspected manuscript where possible. The project file links assume the companion files are stored beside this amendment; their names and revision remain usable identifiers when a Sources interface does not resolve relative links.

### Project documents

**P1 — Current specification:** `MNEME_Model_Instance_Development_Spec.md`, internal revision “2026-09-13 — targeted update: instance-centered development, path dependence, and identity.” The supplied latest `(2).md` copy matches this revision. Key sections: §§3.4–5.6, 10.10–11, 14–16.  
**P2 — Original research dossier:** `MNEME_Related_Work_Research_Dossier.docx`. Retained unchanged; use this amendment for its updated MNEME interpretation.  
**P3 — Original architecture spec:** `MNEME_Earned_Association_Field_Spec.md`. Historical architecture basis, not the governing project framing.

### New research links

- **R01:** Takata et al. — individuality in shared-LLM communities. https://arxiv.org/html/2411.03252v1
- **R02:** Ashery et al. — social conventions and collective bias. https://arxiv.org/html/2410.08948v2
- **R03:** Park et al. — Generative Agents. https://arxiv.org/html/2304.03442v2
- **R04:** Pielage et al. — dynamic personality state machines. https://arxiv.org/html/2602.22157v1
- **R05:** Colas et al. — language/culture internalisation and autotelic AI. https://arxiv.org/pdf/2206.01134v2
- **R06:** Serapio-García et al. — personality measurement and shaping. https://arxiv.org/html/2307.00184v4
- **R07:** Gupta et al. — self-assessment reliability. https://arxiv.org/html/2309.08163v2
- **R08:** Meyer et al. — psychological profiles as measurement artifacts. https://arxiv.org/html/2606.20205v1
- **R09:** Chen et al. — Persona Vectors. https://arxiv.org/html/2507.21509v3
- **R10:** Ma et al. — internal-activation personality evaluation. https://arxiv.org/html/2601.09833v1
- **R11:** Panickssery et al. — recognition and self-preference. https://arxiv.org/html/2404.13076v1
- **R12:** Davidson et al. — self-recognition tests. https://arxiv.org/html/2407.06946v2
- **R13:** Bai et al. — Know Thyself? https://arxiv.org/html/2510.03399v1
- **R14:** Binder et al. — self-prediction/introspection. https://arxiv.org/html/2410.13787v1
- **R15:** Lindsey — causal introspection experiments. https://arxiv.org/html/2601.01828v1
- **R16:** Shinde — SCM graph-backed self-model. https://arxiv.org/html/2604.20943v1
- **R17:** Xiong et al. — experience-following behavior. https://arxiv.org/html/2505.16067v1
- **R18:** Zhang et al. — repeated consolidation failures, revised version. https://arxiv.org/html/2605.12978v2
- **R19:** Liu — evaluator-bias propagation through memory. https://arxiv.org/html/2606.23195v1

### Legacy sources checked in this amendment

- **L01:** LongMem. https://arxiv.org/abs/2306.07174v1
- **L02:** A-MEM. https://arxiv.org/abs/2502.12110v11
- **L03:** HippoRAG. https://arxiv.org/abs/2405.14831v3
- **L04:** SEAL, inspected methods version. https://arxiv.org/html/2506.10943v1
- **L05:** TTT proceedings. https://proceedings.mlr.press/v267/sun25h.html
- **L06:** M+ proceedings. https://proceedings.mlr.press/v267/wang25au.html ; corresponding manuscript: https://arxiv.org/abs/2502.00592

---

## Closing assessment

The stronger literature position is not “nobody has tried to make models individual.” It is:

**Related systems already investigate emergent differences, persistent memory, self-related behavior, and controllable representations. MNEME asks whether these can support a carefully measured, instance-centered developmental process whose state remains inspectable and separable from its host.**

That question is narrow enough to test and broad enough to justify building the laboratory. The amendment does not add another required mechanism. It identifies the comparisons and failure modes the roadmap should preserve.

**Memory remains the mechanism. Development remains the subject. The papers constrain what we may claim; the prototype must supply the missing evidence.**

[P1]: MNEME_Model_Instance_Development_Spec.md
[P2]: MNEME_Related_Work_Research_Dossier.docx
[P3]: MNEME_Earned_Association_Field_Spec.md
[R01]: https://arxiv.org/html/2411.03252v1
[R02]: https://arxiv.org/html/2410.08948v2
[R03]: https://arxiv.org/html/2304.03442v2
[R04]: https://arxiv.org/html/2602.22157v1
[R05]: https://arxiv.org/pdf/2206.01134v2
[R06]: https://arxiv.org/html/2307.00184v4
[R07]: https://arxiv.org/html/2309.08163v2
[R08]: https://arxiv.org/html/2606.20205v1
[R09]: https://arxiv.org/html/2507.21509v3
[R10]: https://arxiv.org/html/2601.09833v1
[R11]: https://arxiv.org/html/2404.13076v1
[R12]: https://arxiv.org/html/2407.06946v2
[R13]: https://arxiv.org/html/2510.03399v1
[R14]: https://arxiv.org/html/2410.13787v1
[R15]: https://arxiv.org/html/2601.01828v1
[R16]: https://arxiv.org/html/2604.20943v1
[R17]: https://arxiv.org/html/2505.16067v1
[R18]: https://arxiv.org/html/2605.12978v2
[R19]: https://arxiv.org/html/2606.23195v1
[L01]: https://arxiv.org/abs/2306.07174v1
[L02]: https://arxiv.org/abs/2502.12110v11
[L03]: https://arxiv.org/abs/2405.14831v3
[L04]: https://arxiv.org/html/2506.10943v1
[L05]: https://proceedings.mlr.press/v267/sun25h.html
[L06]: https://proceedings.mlr.press/v267/wang25au.html
