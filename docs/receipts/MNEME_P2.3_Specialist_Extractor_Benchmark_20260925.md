# P2.3 specialist extractor benchmark

Date: 2026-09-25  
Status: **candidate instrument selected for downstream integration; benchmark remains exploratory**

This receipt records a provider-free local benchmark. The historical v5
conversation, its `relationships-v1` empty results, and its
`NOT_DEMONSTRATED` disposition are unchanged.

## Instrument and host

- instrument: GLiNER2.5 base boundary extractor
- model: `fastino/gliner2.5-base-v1`
- model revision: `b0c10b23313ec3ff028821dff298dd743e010706`
- model file: `model.safetensors`, SHA-256
  `7274094de2e0c2a37a386f55fc4e23061a954da5bd7a335e7dfe56f2743c277a`
- library: `gliner2` 2.0.0 (current upstream commit `55656fbfa01d3d4a77485e1a1eeeaf682990ccdf`)
- runtime: PyTorch 2.14.0+cpu, Transformers 4.57.6, Python 3.14.4
- execution: MSI GS66 Stealth 11UE (`brokeass-msi`, Tailscale endpoint recorded
  privately), CPU inference for the specialist; no MNEME state or network
  service was exposed by the benchmark
- relation threshold: 0.35; source spans were returned by the model and then
  independently checked by MNEME tooling
- raw output: [JSONL receipt](MNEME_P2.3_specialist_benchmark_gliner2.5_base_raw_20260925.jsonl)
- reviewed fixture: [benchmark fixture](../experiments/extraction/P2.3_specialist_benchmark_fixture_v1.json)

The MSI was also prepared for the canonical local Gemma role. The exact
`google/gemma-4-E4B-it` family was obtained as
`unsloth/gemma-4-E4B-it-qat-GGUF/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`; current
llama.cpp was built with CUDA 12.4 for the RTX 3060 (SM 8.6). A one-turn local
smoke returned `Hello.` with GPU offload. Full conversation execution is a
separate gate; the historical DeepInfra transcript remains the source for
retrospective extraction and is not regenerated.

## Benchmark result

The fixture contains ten reviewed relationship-bearing cases and two negative
or abstention cases, with two held-out cases. At the fixed threshold, the base
instrument returned at least one source-grounded proposal for 7/10 reviewed
positive cases and both held-out cases returned a source-grounded proposal or
an interpretable partial proposal. It abstained on the explicit metaphor and
the negated dial case. It missed the gravel/evaporation and abstract-routine
positives, so this is not a claim of complete recall.

| case | result at threshold 0.35 | review disposition |
| --- | --- | --- |
| wick keeps moisture | `wicks(soil, moisture)` | usable candidate |
| gravel reduces evaporation | empty | missed positive; downstream cannot recover absent candidate |
| shade cools basil | `affects(shade, basil)` | usable candidate, semantic review required |
| reservoir enables wicking | `depends_on/requires(wick, water)` | usable candidate, direction review required |
| abstract routine/grounding | empty | acceptable abstention for this instrument |
| explicit dial negation | empty | no false positive candidate |
| kitchen metaphor | empty | correct abstention |
| mint used for tea | empty | missed positive |
| repeated reservoir/soil statement | multiple variants | deterministic duplicate handling required downstream |
| wick recurrence under two plants | two wick candidates | recurrence is observable |
| held-out tray supplies water | `provides(tray, water)` | usable held-out candidate |
| held-out paprika/lentils | `uses(lentils, paprika)` | partial candidate; semantic review required |

The model deliberately returns source-language spans and relation phrases. It
does not receive MNEME IDs, learner state, provenance, or canonicalization
instructions. The benchmark therefore selects the base checkpoint as a
reasonable **candidate observation instrument**, while retaining strict
downstream grounding and semantic assessment. The small checkpoint was not
selected: on the same fixture it produced substantially fewer proposals and
missed the clear concrete positives.

## Scope and limitation

The benchmark measures candidate-observation recall, span grounding, and
abstention behavior. It does not establish canonical direction, negation,
provenance, learner credit, consolidation, or behavioral influence. Those
remain downstream MNEME decisions. No relationship is admitted solely because
GLiNER emitted it.
