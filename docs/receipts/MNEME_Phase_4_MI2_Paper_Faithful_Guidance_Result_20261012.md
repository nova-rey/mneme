# MNEME Phase 4 MI2 paper-guidance result

**No: we did not demonstrate that meaningful guidance in side memory changes this Gemma’s reasoning. The necessary visible-guidance control did not pass, so no MI2 latent-memory condition was run.** The evidence is a negative result for advancing this Gemma 4 E4B Q2/llama.cpp path, not a direct latent-memory failure measurement and not a universal claim about Memory Inception.

The strongest paired example shows why the gate matters. On the same quantum double-delta-well task and seed, baseline Gemma outlined the time-independent Schrödinger equation but gave an incorrect, vague localized-state answer. With the paper’s Quantum process card visible, it identified the same problem category, then repeated a short TISE/ground-state loop until the 8,192-token allowance ended; it returned no final answer. That single pair is not proof the card caused the loop, but it is not evidence of a useful visible effect either.

## What was tested

We reused the representative Quantum process card in Memory Inception v2 Appendix E, Table 5. In substance, it asks the solver to distinguish spectral, dynamical, measurement, perturbative, and asymptotic questions, choose a matching method, and avoid confusing similar quantum symbols. The v3.4 visible-only gate paired problem-only requests with requests that added that same card in the system context, over all 33 previously unused text-self-contained Quantum PHYSICS-eval items (31 direct process items and two broad items), three seeds, reasoning ON, and prompt caching disabled.

| Paper component | v3.4 correspondence |
|---|---|
| Source guidance | Representative Quantum card from Appendix E/Table 5. |
| Contextualization and variants | Not run. This was a visible prerequisite gate, not bank construction. |
| K/V extraction and bank composition | Not run. |
| Layer/head selection | Not run. |
| Injection/application | Not run. |
| Evaluation | Matched BASELINE versus VISIBLE_GUIDANCE system context. |
| Controls | Duplicate deterministic baseline preflight and baseline headroom gate. No latent, irrelevant-bank, removal, or replacement condition. |

This is deliberately narrower than a full reproduction of the paper. The paper’s PHYSICS cards are built from multiple construction questions and solutions, stripped to process-only guidance, then compared across visible and latent conditions on held-out questions. v3.4 tested the paper’s representative card as visible guidance; it did not rebuild the paper’s construction pipeline or test side memory. The exact Gemma Q2/llama.cpp host is also outside the paper’s evaluated backbones. The project’s [paper correspondence note](../research/MI2_Memory_Inception_Paper_Reference_20261011.md) documents the full mapping and code-release provenance; no authenticated author implementation was used.

## Result and execution integrity

The duplicate baseline preflight passed, the baseline-only headroom rule passed, and all 99 baseline calls ended with `finish_reason=stop`. The visible matrix has 98 normal stops and one `finish_reason=length` with an empty final answer. All 200 requests/results are preserved. No bank, K/V, selector, latent, irrelevant-memory, removal/reuse, held-out, PHYSICS-test, or MNEME/SAA call occurred.

The frozen approval required stopping immediately on any abnormal coordinate. The v3.4 runner durably stored the length-truncated output but failed to stop before dispatching 93 later visible coordinates. Therefore v3.4 is **not a clean, protocol-compliant completed gate**. The failure is retained; it was not retried. A runner correction now raises immediately after durably recording an abnormal finish, with regression coverage proving the next coordinate is not dispatched.

As a conservative descriptive analysis only, the truncated coordinate receives zero rather than being retried or excluded. Under the same mechanical process annotations used for the baseline headroom gate, the 31 direct items have mean process scores of 2.129/3 baseline and 2.086/3 visible, a delta of **−0.043/3**. Five item means improve, seven decline, and nineteen tie (one-sided exact sign-test p=0.806). This is nowhere near the frozen +0.25/3, positive-greater-than-negative, p≤0.05 pass rule. Exact normalized official-answer component matches were 16/255 baseline and 11/255 visible; this exact-only count does not award semantic-equivalence partial credit. The normalized task-mean answer harm is 0.013, within the 0.05 limit, but no answer-harm allowance can substitute for missing process improvement.

Because the official scorer correctly rejects the abnormal finish, these descriptive values do not repair or retroactively validate the gate. Even the conservative zero-scored analysis fails the visible criterion. The machine-readable result records both facts separately.

## How this relates to MI1

MI1’s **8/8** was visible text on four short, single-target directed paths. It showed that Gemma could follow simple rules printed in its ordinary prompt; it was not hidden-memory success or procedural-guidance success. MI1’s harder C2 visible control scored **2/6**: one answer omitted full path labels and three made substantive reachability or invented-edge errors. C3 returned to the simple path fixture and again scored 8/8. Those outcomes differ in fixture difficulty and do not conflict.

MI1’s complete Test A/B/C result remains unchanged: latent exact retrieval was 0/24 for each polarity; Test B did not establish attributable neighborhood influence; Test C mechanically attached, replaced, disabled, and restored banks, but its 16 outputs remained `unknown`. Its detailed [continued-resolution report](MNEME_Phase_4_MI1_Continued_Resolution_20261011.md) preserves those results and measured lifecycle costs. The synthetic MI1 task was not the paper’s strongest use case, so it cannot settle procedural side-memory. MI2 corrected the task family at the visible-control stage, but Gemma still did not show a reliable visible process-prior effect on the broad frozen cohort.

## Disposition

**Recommendation: do not advance Memory Inception toward SAA integration on this Gemma host.** The paper-style visible prerequisite is weak/inconsistent across prior small subject cards and fails this broad Quantum cohort; MI1 side-memory retrieval and lifecycle experiments remain negative. No latent meaningful-guidance comparison or secondary MNEME-shaped neighborhood test is justified by these results. This does not prove that a different Gemma-aware attention/KV implementation or another host could never work; it means this local path has not earned that next step.

The canonical v3.4 journal remains outside Git at `/home/nyx/mneme-artifacts/phase4-mi2/calibration-run-v3.4/journal/` (235,603,921 bytes; index SHA-256 `c68ee4b6bb4a91db9a8a7d84cfd54ab8d3c7e8a1c5ef2275294bb7ef67565625`). Full paired annotations are also outside Git, SHA-256 `67aa1fef26699daf6aad05af5a6f3f670b2d55f5417ee4c42da3e7f1c257bcfc`. The compact per-task result is in [the JSON receipt](MNEME_Phase_4_MI2_Paper_Faithful_Guidance_Result_20261012.json). After the run, the isolated Gemma server received SIGTERM; the remote process/listener and local tunnel were verified stopped.
