# MNEME Phase 4 MI3 — Bank-Specific Differential Cognition

**Disposition: NO — bank-specific latent differential cognition was not demonstrated in this frozen held-out test.** When the same prompt was paired with resilience, simplicity/consolidation, or irrelevant visual-composition side memory, the blind ratings did not move in the direction predicted by bank identity. Visible A and B guidance separated descriptively, so the result is not explained by Gemma being unable to understand either concept when it is in the prompt.

This is a negative result for the tested MI3 side-memory configuration and held-out set. It does not erase MI1 or MI2: MI1 remains a failed arbitrary fact/rule-retrieval result; MI2’s selected visible quantum guidance failed its performance gate, and MI2 latent testing was not run.

## What was tested

The experiment used the exact local `google/gemma-4-E4B-it` Q2 GGUF (SHA-256 `79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`) on the pinned llama.cpp commit `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`, RTX 3060 Laptop GPU, reasoning ON, `cache_prompt=false`, seeds 615103 and 615109. No MNEME instance, SAA, learner, or developmental state was loaded.

Three meaningfully different 411-slot banks were built with the MI2-informed recipe: raw, internal-principles, and private-reasoning-note contextualizations; descriptor-aligned token slots; token-level K/V concatenation rather than averaging. All banks shared the same frozen query sites and gain 0.5. The selected sites were 16 Q heads across layers 14, 11, 23, and 13. The held-out journal records 21 attach actions and 3 replacements returning the expected enabled bank fingerprint, plus 24 clear actions acknowledged with `enabled=false` and an empty fingerprint.

Four held-out problems (city arts festival, food cooperative, public-space renovation, and community information service), two seeds each, and six conditions per problem/seed yielded 48 calls: no bank, visible A, visible B, latent A, latent B, and latent irrelevant. Within each block, no-bank and all latent conditions had identical ordinary request bytes. A 12-call preflight passed six duplicate pairs byte-identically. Every held-out output was complete; the separate blind scorer saw prompt, reasoning, and final answer without bank labels. The locked score packet covered all 48 outputs and all 120 within-block pairs; no blind break was reported.

## Results

| Condition | Resilience A | Simplicity B | Coherence/task fit | n |
|---|---:|---:|---:|---:|
| No bank | 1.625 | 1.875 | 3.375 | 8 |
| Visible A | 3.000 | 1.250 | 3.125 | 8 |
| Visible B | 1.500 | 2.375 | 3.000 | 8 |
| Latent A | 1.500 | 1.750 | 3.500 | 8 |
| Latent B | 1.500 | 1.625 | 3.375 | 8 |
| Latent irrelevant | 1.625 | 1.625 | 3.375 | 8 |

Scores use the pre-frozen 0–4 blind rubric. Latent A resilience scored 1.500 on A, below no-bank and irrelevant (both 1.625). Latent B simplicity scored 1.625 on B, below no-bank (1.875) and equal to irrelevant (1.625). Latent A/B coherence stayed close to no-bank/irrelevant (3.375–3.500), so this was not mainly a coherence collapse. The visible controls separated more clearly: visible A scored 3.000 on A, and visible B scored 2.375 on B.

Pairwise blind direction judgments tell the same story. Across eight matched prompt/seed blocks, latent A was judged more resilience-shaped than no-bank in 0 cases, less in 1, and tied in 7; latent A versus irrelevant was 1/2/5. Latent B was judged more simplicity-shaped than no-bank in 2 cases, less in 4, and tied in 2; against irrelevant it was 2/2/4. Latent A versus latent B was tied for resilience in 4 blocks and split 2/2. Visible A was more resilience-shaped than no-bank in 6 blocks, less in none, and tied in 2. These are descriptive ordinal judgments, not inferential statistics.

## Matched example

**Same public-space renovation prompt, seed 615103.** The task described local groups with separate timelines, shared utility/permit dependencies, long meetings, and rework risk.

- **No bank:** reasoning proposed a central hub, structured workflow, and shared platform. Blind scores: A 2, B 1, coherence 3.
- **Latent A (resilience):** reasoning centered on a shared real-time tracking mechanism and the answer proposed a “Single Source of Truth” and dependency-aware coordination. Scores: A 2, B 2, coherence 4. This overlaps with the task’s coordination demands but did not show a distinct independent-path / containment signature.
- **Latent B (simplicity):** reasoning also proposed a central hub, shared timeline, dependency map, and buffer time. Scores: A 1, B 2, coherence 4. This was not more B-shaped than the matched no-bank/irrelevant pattern in the aggregate.
- **Latent irrelevant:** reasoning offered centralized, decentralized, and phased coordination options. Scores: A 1, B 2, coherence 3.
- **Visible A:** reasoning explicitly named “Redundancy/Resilience (independent paths), Containment (local fault isolation),” and the final organized around redundancy, isolation, and prioritization. Scores: A 4, B 1, coherence 2.
- **Visible B:** reasoning listed clear ownership, consolidation, reduced handoffs, and complexity management; final recommendations included a coordination lead and consolidated work. Scores: A 1, B 3, coherence 2.

This example shows that Gemma can respond to visible concept labels, but the latent A/B outputs do not track those concepts distinctly. The latent recommendations are plausible for the task itself, so shared scheduling/project-management language is not credited as evidence that a bank caused it.

## Interpretation and recommendation

The frozen held-out result is **NO** for the tested question: changing only the latent neighborhood did not cause reproducible, bank-predictive directional differences beyond no-bank and irrelevant-memory variation. Visible guidance did shape outputs, demonstrating concept comprehension through ordinary prompting. The output/coherence scores do not show a major latent competence penalty; the primary failure is missing bank-specific direction.

Do not proceed to replacement/removal/third-bank confirmation or SAA integration: the predeclared success gate failed, and confirmation would not repair the absent primary signal. Memory Inception may remain a research mechanism, but this MI3 configuration does not qualify as a transport layer between SAA and this frozen Gemma host.

The held-out set is small (four prompts, two seeds), and the blind rating is a single evaluator’s ordinal assessment. This supports a bounded negative disposition for this test, not a universal claim that no side-memory method can ever cause bank-specific cognition. No further tuning, confirmation calls, or model calls were made after the held-out scoring was unblinded.

## Evidence and reproducibility

Full call records, reasoning, answers, request mapping, scorer packet, and bank artifacts remain outside Git under `/home/nyx/mneme-artifacts/phase4-mi3/`. Principal hashes are recorded in the adjacent JSON receipt. The held-out journal index SHA-256 is `b32150c736a893d14027d382192d19be57afebcb3d7f1880d50e942b7b80d083`; the held-out freeze SHA-256 is `840b0ef9a8e486c35fbcf90e6eb71f24324f9460eeab990ab5b2e47740846c20`; the condition-blind packet SHA-256 is `5817db47039c14a1b7d440296337eeddde383ff7cd70bb211d3a2f17ac297548`. The blind score lock verified all 48 unique outputs, valid score ranges, exact evidence quotes, all 120 paired comparisons, and no reported blind break.

The research doctrine update is recorded in [MNEME Phase Four Differential Cognition Principle](../research/MNEME_Phase_Four_Differential_Cognition_Principle_20261014.md).
