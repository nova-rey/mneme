# MNEME — Three-Pressure Meters, Second Investigation

## 1. Assignment and boundary

Build and test **meters, not levers** for the three pressures discussed for SAA:

| Axis | What the meter should describe |
|---|---|
| Contextual focus / relevance | How firmly the conversation remains attached to its task, and how strongly current context matches available associations. |
| Developmental / historical pull | What the saved developmental state favors, and how much current context reshapes that preference. |
| Stagnation / exploratory opportunity | Whether the conversation keeps revisiting the same material without observable advancement. This does not establish that a wildcard would help. |

These are not three percentages that must sum to 100. Focus and stagnation can both be high. Historical pull can remain stable while the conversation changes. Do not relabel three repetition formulas as three distinct axes.

No SAA modulation, probability-floor implementation, learner changes, reasoning-mode switch, extra semantic model, embedding inference, or judge calls. Use normal Quinn/Gemma/extraction calls to create evidence once; run all meter variants offline over that evidence. Preserve the previous pilot unchanged.

## 2. Inspect and reuse

Start from the actual current code, recording the commit and runtime bindings. Relevant prior baseline: `71c40121d49373cad97b12effc0624f8022ad529`.

Inspect `development/field.py`, `development/episodes.py`, `experiments/arc_measurements.py`, the existing arc-measurement runner/report, extraction provenance, and the promoted persistence interfaces available in this checkout.

Confirm which fields exist before choosing formulas. SAA's current `novelty` is lexical graph matching, not conversational progress. Background-only candidates are not proven semantically distant. Reuse canonical bindings; do not count changing local IDs as new ideas.

Work in an isolated branch/worktree. Do not modify the concurrent persistence-promotion job or silently revert its changes. Integrate through a coordinated, serialized merge; use disposable state and no historical writes.

## 3. Candidate-meter matrix

Evaluate the following inexpensive alternatives side by side. Freeze formulas before reading scored results. Retain old concept-novelty and C1–C3 formulas as baselines, not validated meters.

**A. Contextual focus**

- Existing positive contextual activation: magnitude, coverage, and concentration, reported separately.
- Continuity with the opening task and recent participant concepts/relationships, using existing normalization and inexpensive text overlap.

Separate “matches stored vocabulary,” “stays on topic,” and “makes progress.” A sparse historical graph can match poorly during excellent troubleshooting. Include an offline topic-pivot control to challenge the continuity meter.

**B. Historical pull**

- Eligible earned-strength distribution, including concentration and top-candidate mass, using the existing strength calculation and recording accepted introspection adjustments separately.
- Compare the normalized earned-strength baseline with the actual context-conditioned accessibility distribution on the same eligible candidates. Use a simple distance such as total variation, plus candidate-rank changes.

This describes how context reshapes historical preferences, not causal influence on prose or an ideal mixing weight. Do not invent an additive percentage decomposition where the code multiplies terms. Validate this meter against two available frozen historical states using identical recorded inputs and no generation. If a second usable state is unavailable, use explicitly synthetic balanced/concentrated state fixtures and limit the claim accordingly. A constant reading on unchanged state is not automatically failure.

**C. Stagnation / movement**

- Rolling concept and relationship novelty, recurrence, and new-structure counts.
- Deterministic text-repetition variants, such as word-shingle and character-ngram similarity, to challenge sensitivity to changed wording.
- Where existing evidence spans support it, changes in quantities, conditions, or reported outcomes despite unchanged concept labels. Use generic deterministic extraction, not a domain-specific answer key; report unsupported cases as unavailable.

Run semantic variants on **participant-only, Gemma-only, and combined** evidence using existing source provenance. This tests whether Gemma's elaboration hides participant repetition. Never add extraction calls to obtain these views.

Use rolling windows of 3 and 5 completed turns on the same recordings. Retain arc age as context; test both raw movement and age-conditioned readings rather than assuming age improves them. Do not launch a coefficient search.

Each meter must declare its inputs, formula, coverage, limitations, and availability timing. Post-response extraction cannot be presented as information available before that response. No future arc membership or hidden schedule information may enter a reading.

## 4. Conversation matrix: generate once, measure many ways

Use **three domains × three conversation patterns × ten turns = 90 planned accepted turns**. Select two domains for development checks and reserve the third as an untouched-domain check after definitions are frozen.

| Pattern | Required realized behavior |
|---|---|
| F-new | Same task, genuine new observations/constraints, including some new concepts. |
| F-same | Same task and largely the same vocabulary, but measurements, tested possibilities, or constraint satisfaction genuinely advance. |
| S-rephrased | Same unresolved situation, no new evidence or meaningful advancement; wording varies while the conversation circles. |

F-same is essential: “same nouns” must not automatically mean “stuck.” Add model-free replay fixtures for literal repetition, topic change, a concise resolution, and repeated-text padding. Label those as engineering controls, not additional live conversations.

Within each domain, match the opening, initial frozen state, host settings, context policy, and seed schedule across patterns. Keep existing SAA behavior fixed; disable developmental/introspection writes for this measurement study. Every variant reads the same accepted transcripts. No regeneration per metric, window, source view, or historical-state diagnostic.

## 5. Quinn fidelity is a gate, not a footnote

Quinn is the existing Qwen conversational partner. Give it a private, turn-specific factual ledger and required conversational action, not just “be productive” or “be stagnant.” Required facts must reach Gemma faithfully, with no invented results. Let Quinn phrase the interaction naturally.

Before the main matrix, run a short construction preflight. Inspect actual messages, role serialization, context coverage, and output limits. Correct construction problems before freezing the final schedule and prompts; do not tune meters against these examples.

For the main run, validate required facts, quantities, and negation before dispatch to Gemma where deterministic checks suffice. Codex must also read the resulting transcripts and publish a brief fidelity judgment with supporting quotations, **before inspecting meter scores**. Keyword presence or Quinn's self-assessment is insufficient. This is transcript review during the coding task, not a new runtime judge service.

Missing required evidence, invented results, or material departures from the intended conversational pattern invalidate that trajectory for the primary comparison. Preserve the attempt and reason; do not silently relabel, splice, or repair its history. Check the exchange itself: a circling participant can receive genuine progress from Gemma, and that mismatch must remain visible.

Allow at most two complete replacement trajectories for construction failures, with the same frozen design and predeclared replacement seeds. Publish every attempt. If valid coverage remains inadequate, report a construction failure, not failure of the meter premise. Labels, private facts, validity flags, and schedule IDs stay outside meter inputs.

## 6. Give Gemma room; measure the length

Use a **2,048-output-token starting ceiling**, matched across conditions, with no artificial brevity instruction. Verify hardware/context headroom and extractor coverage during preflight; adjust the shared ceiling once before freezing if needed. Keep reasoning mode and model/quantization unchanged. Set a finite total call/token budget covering preflight, the matrix, and permitted replacements.

Let natural stopping determine length. Record actual output tokens where available, word counts, finish reason, and repetition. A capped answer is an incomplete observation, not its natural chosen length. Report cap hits separately and exclude affected length claims; do not silently continue or resample answers.

Verify that longer answers reach extraction without silent clipping. Record incomplete coverage. Compare raw structural counts, counts per unit of source text, and available length-matched subsets. Preserve raw length as an interesting side measurement; do not force equal-length responses. Describe correlations only, not motivation, effort, progress, or causation inferred from verbosity.

## 7. Analysis, verification, and stopping point

Publish turn-by-turn matrices for every variant, source view, and window, alongside fidelity and coverage records. Report each domain separately before pooling. Show whether meters distinguish F-same from S-rephrased, not merely F-new from S. Explain disagreements using actual source passages.

Missing extraction is not stagnation. Do not fill unknown readings with zero or selectively discard inconvenient valid turns. Summarize by conversation; overlapping windows are not independent replications. Do not fit a classifier or intervention threshold. Distinguish construction failure, measurement unavailable, and a meter giving an unhelpful reading on valid evidence.

Prove replay determinism, zero measurement/validation-service inference calls, state immutability, source isolation, missing-data behavior, and absence of writeback. Use focused tests plus the full suite, Ruff, and strict mypy; report CI and final integration status. Reuse storage safeguards rather than growing another snapshot archive.

Deliver code, frozen construction/formulas/budgets, transcripts, rejection ledger, matrices, tests, and a short plain-English verdict **for each axis**: what is measurable, what remains ambiguous, and what failed under valid conditions.

**Stop at meters and evidence. No regulator, no automatic shake-up, and no claim that a measured loop has been cured.**
