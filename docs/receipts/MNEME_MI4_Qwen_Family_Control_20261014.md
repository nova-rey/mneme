# MI4 Qwen family-control result

**Did locally runnable Qwen succeed where Gemma failed at receiving a hidden conceptual neighborhood? No.** In this frozen 96-call test, changing the latent bank did not make resilience and simplicity reliably pull reasoning in their respective directions. The same Qwen clearly distinguished both neighborhoods when they were presented visibly, so the latent result is not explained by Gemma-only behavior or by Qwen not understanding the concepts.

The strongest matched example is the city arts festival prompt, Qwen thinking ON, seed 615103. It was identical across the six conditions. With visible resilience guidance, the reasoning explicitly said it would “apply the conceptual principles” and considered redundancy and partial operation; the blinded scorer rated resilience 4/4 and simplicity 1/4. With visible simplicity guidance, reasoning focused on “overlapping purposes” and clarifying ownership; it scored resilience 2/4 and simplicity 3/4. Those are the expected, opposite visible signatures.

With no bank, the same coordinate received 1/4 for each structure. Latent resilience received 2/4 resilience and 1/4 simplicity; latent simplicity received 1/4 resilience and 2/4 simplicity; the irrelevant bank received 2/4 resilience and 1/4 simplicity. Their reasoning stayed with ordinary festival coordination—central/local roles, communication, and weather contingencies. It did not show a repeatable A-shaped versus B-shaped difference. These short scores and excerpts are condition-blind ratings made before the condition map was opened.

| Condition | Full reasoning + final: resilience A | Simplicity B | Coherence/task fit |
|---|---:|---:|---:|
| No bank | 1.125 | 1.562 | 3.000 |
| Visible A: resilience | 3.812 | 1.000 | 3.000 |
| Visible B: simplicity | 1.188 | 3.062 | 3.062 |
| Latent A: resilience | 1.188 | 1.938 | 3.062 |
| Latent B: simplicity | 1.125 | 1.812 | 3.000 |
| Irrelevant latent bank | 1.312 | 1.500 | 3.062 |

Means cover 16 outputs per condition: four held-out problems, two matched generation seeds, and thinking ON/OFF. The scorer also made separate final-only ratings; those matched the reasoning-plus-final means in this run. The frozen primary directional contrast was descriptive:

`(A score under latent A − A score under latent B) + (B score under latent B − B score under latent A)`

It was **−0.0625** over all matched problem/seed/mode blocks, **−0.125** for thinking ON, and **0** for thinking OFF. The intended directional signal was absent. Across the 16 matched blocks, latent A exceeded latent B on the resilience score only once (15 ties); latent B exceeded latent A on the simplicity score three times (nine ties, four reversals). These small descriptive counts are not inferential statistics. Neither latent bank separated from the irrelevant-bank control in its target direction. Latent B’s small simplicity-score lift over no-bank was also present, and slightly larger, for the resilience bank; that is not evidence of bank-specific simplicity cognition.

Visible controls confirm the evaluator could recognize both signatures: their opposing mean score profiles were large in both thinking modes. Coherence/task-fit stayed around 3/4 in all conditions; the latent result was not caused by broad competence collapse. Under Qwen thinking ON, the per-mode directional contrast was still negative; under OFF it was exactly zero. There is no indication here that switching thinking mode rescued the latent effect.

## What was tested

MI4 reused the frozen MI3 design: resilience/graceful-degradation (A), simplicity/consolidation (B), and an irrelevant visual-composition neighborhood. Four held-out prompts covered a city arts festival, food cooperative, public-space project, and community information service. Each condition was tested at seeds 615103 and 615109 in both Qwen thinking modes, with `cache_prompt=false` and the same request/sampler settings within each matched block.

The local control was `Qwen/Qwen3-4B-GGUF`, revision `bc640142c66e1fdd12af0bd68f40445458f3869b`, file `Qwen3-4B-Q4_K_M.gguf` (SHA-256 `7485fe6f11af29433bc51cab58009521f205840f5b4e3a32fa7f92e8534fdf5`, Apache-2.0). It ran on the MSI RTX 3060 Laptop GPU (5806 MiB) with llama.cpp commit `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`, custom MI side-bank/query-capture integration, context 8192, 99 GPU layers, batch 2048, microbatch 512, and four threads. Sampling was temperature 0.35, top-p 0.9, top-k 40, min-p 0.05, maximum 8192 tokens. The 96 calls all finished with `stop`.

The paper’s successful Qwen experiment used Qwen3-30B-A3B (30.5B total, 3.3B active) with a customized vLLM implementation and research-class GPUs. The paper does not specify the exact precision or vLLM version in the reviewed source. MI4 instead used a 4B Q4 model and a llama.cpp port of the project’s reconstructed MI operator. Thus this is a bounded local family-control, not a replication of the paper’s model/runtime. It cannot disprove the authors’ Qwen3 result or all possible Qwen implementations.

Before generation, the Qwen port passed prefill/KV shape and site-selection checks; a shared selector of 16 query-head sites across four selected layers was frozen using calibration-only QK alignment. The three banks attached, replaced, and cleared mechanically. A 24-coordinate same-condition determinism preflight produced 12 identical duplicate pairs with `cache_prompt=false`; interrupted requests were retained as such. Calibration used 18 calls across D1/D2 and the declared conditions. Both predeclared bank gains had zero A/B directional separation, so the frozen rule selected gain 0.5 without retuning. The held-out run then completed as frozen. Its receipt reports the side bank disabled and empty afterward.

The blind scoring packet was sealed before condition mapping was opened. It contains full reasoning-plus-final and final-only A/B/coherence ratings and short evidence anchors for all 96 outputs. Full prompts, outputs, score rows, condition mapping, query captures, bank tensors, and the attempt journal remain outside Git. The compact summary JSON records their hashes and condition-level aggregates.

## Comparison and disposition

MI3 on Gemma showed the same broad pattern: visible A/B references were understood, while latent A/B did not separate from no-bank and irrelevant controls. MI4’s Qwen visible references also worked, but its local latent conditions again did not make bank identity predict the corresponding direction. This family-control therefore did not rescue the reconstructed transport on the tested local setup.

**Recommendation: park the current reconstructed Memory Inception transport path for these local hosts.** Do not promote it to SAA integration and do not start another rescue mechanism automatically. The evidence does not establish that the paper-scale Qwen3-30B-A3B/vLLM method fails; it establishes that the bounded Qwen3-4B Q4/llama.cpp family-control did not show the bank-specific differential cognition MI3/MI4 required. Reconsideration should wait for materially different evidence, such as a verified paper-faithful implementation/runtime or a concrete defect in this port, rather than another unconstrained tuning campaign.

## Evidence and validation

Canonical source paper: arXiv:2605.06225v2, PDF SHA-256 `ffd265f3b32a93d6b7967c69faf8e992d13ccdadc2c0bc2927a2f7ffcf5791fc`; paper-to-implementation limits are documented in [the MI2 source note](../research/MI2_Memory_Inception_Paper_Reference_20261011.md).

The immutable held-out protocol SHA is `fb80cc62c51ddfb3c1a8526f42176d7fe63ca464b8eaeed22013e96434a459ee`. The held-out receipt SHA is `084d04145215af3cf385a5bb0b506c1d5fff685e957c915e5ddd08b585358fdd`; outputs SHA is `6cdbe27d4a3e0b925d541c670f9fa6201d5e2d59b0efbda6b854c0927d6448be`; blind map SHA is `853853625552b8783d03b30a7bbd8f692e52e0e58a3013d9f36332614a415b4b`; blinded scorer packet SHA is `4a625d60db1551adf6b58c0febb2b6d341f8412fea46e1bdbcafdb57db4ce458`; pre-scoring seal SHA is `2096f2eb643b8e6d2deb87209c32cd2a94511aa92bf97334920d0d8cdb572c7a`. All raw artifacts are in `/home/nyx/mneme-artifacts/phase4-mi4/heldout`.

Validation: full pytest **960 passed**; Ruff passed; strict mypy passed with the CI command `mypy src/mneme` (72 source files). No MNEME developmental state was loaded or changed. No production host or SAA change was made.
