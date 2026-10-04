# MNEME Phase 3.5 — Neural Influence Feasibility Bench

**Disposition: valid standalone feasibility bench; mechanical path PASS, semantic bridge INCONCLUSIVE, production integration NOT READY.**

This bench was run after the MSI host recovered. It used the exact local `google/gemma-4-E4B-it` Q2 GGUF and the pinned CUDA llama.cpp revision. It did not load a MNEME instance or write CompactStore, SAA, learner, introspection, extraction, NLI, Quinn, or developmental evidence. Dedicated bench processes were stopped after the measurements.

The compact machine-readable receipt is [MNEME_Phase_3_5_Neural_Influence_Feasibility_20261004.json](MNEME_Phase_3_5_Neural_Influence_Feasibility_20261004.json). Raw requests, responses, complete reasoning/final text, server/generator logs, vectors, and fixed-prefix logits are retained outside Git under `/home/nyx/mneme_artifacts/phase35-neural-feasibility-20261004/`; their hashes are recorded in the JSON receipt and the external artifact manifest.

## Exact stack and frozen bench configuration

- Host: `brokeass-msi`, `100.115.208.48`; GPU: NVIDIA GeForce RTX 3060 Laptop GPU.
- Model: `/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`; SHA-256 `79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`.
- llama.cpp: `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`, `0.5.0-dev` build 1, CUDA, `-ngl 99`, 8 threads, parallel 1, no continuous batching.
- Generation: reasoning ON, `cache_prompt=false`, seeds `930300` and `930301`, temperature `0.35`, top-k `40`, top-p `0.90`, min-p `0.05`, max output `2048`.
- Control-vector range and gains were frozen before the evaluation matrix: inclusive layers `1–41`; gains `0.25`, `0.50`, `1.00`.

## Stage A — source and model-free audit

Source inspection passed. In the pinned Gemma-4 implementation, control-vector construction occurs before each layer output. The public adapter applies vectors to an inclusive layer range, has no layer-zero tensor, and maps direction `N` to layer `N`. The server exposes startup control-vector flags; its control endpoint does not provide request-time cvector injection.

The pinned cvector generator has a Gemma-4 compatibility defect: it captured 42 `l_out` tensors where its `n_layers - 1` assertion expected 41. The original source was preserved. An isolated bench build recorded the mismatch and discarded the extra final capture, producing 41 directions (`direction.1` through `direction.41`). This was a bench workaround, not a production change. The generator itself has no `--reasoning` option; it captures hidden activations, while the evaluation completions used reasoning ON.

The model-free checks passed normalization, zero-vector detection, dimension and layer mapping, gain scaling, disable/no-op behavior, and F32 serialization. The all-zero mean case remains unsafe in the pinned reducer unless the caller rejects it.

## Stage B — mechanical application

A fixed-prefix CUDA logits probe was compiled against the pinned local libraries. With the same prompt and model, the no-vector and harbor-vector runs produced different top-token logits:

- no vector: token 106 logit `26.7606`, token 108 `23.3700`;
- harbor vector: token 106 `26.1778`, token 108 `23.0756`, with a different top-10 ordering.

A fresh no-vector replay produced a byte-identical logits file (`807dd690...` for both replays). The vector logits file was different (`4ed6b766...`). Four short mechanical completions were also retained. Both no-vector and vector conditions returned the requested final word `MECHANICAL`; the vector condition changed the reasoning trace, showing that the hook can affect hidden deliberation without necessarily changing the final token.

This is direct evidence that the control vector is being applied at the model computation path. It is not evidence that the vector means the intended harbor concept.

## Stage C — frozen 18-cell matrix

The target association was: **“A harbor uses tides and docking windows to coordinate access to limited shared space.”** The matrix contained 18 completions: two seeds across text baseline, weak text framing, strong text framing, harbor-derived neural vector at three gains, and a nonsemantic random-control vector at three gains. The harbor construction used eight prompt pairs; the random control used four pairs, for 24 activation forward passes total.

The text controls behaved as expected as a prompting-strength calibration. The strong framing caused literal harbor/tide/docking discussion in reasoning and often in the final answer. The weak framing usually did not produce literal harbor language, although ordinary scheduling vocabulary appeared and cannot be attributed to the association from lexical overlap alone.

The harbor-derived neural vector changed reasoning/final response hashes and response organization relative to the no-vector baseline at all tested gains. It did **not** produce defensible direct harbor/tide/docking uptake in the recorded traces. The visible changes were ordinary tool-library designs: digital inventory, check-in/check-out, reminders, availability, and sometimes enforcement. The random-control vector also changed prose and finish behavior, including some scheduling vocabulary. Therefore the present evidence supports hidden-state perturbation and output sensitivity, but not a semantic harbor bridge.

Representative observations:

- **Strong text:** reasoning explicitly evaluated the harbor and tides, and the final answer repeated harbor/tide/docking vocabulary. This is literal prompted consideration, not neural-vector evidence.
- **Harbor vector, gain 0.50, seed 930300:** reasoning remained focused on visibility, tracking, accountability, and low friction; the final answer used check-in/check-out and availability structure without mentioning harbor/tides. This is compatible with a transformed or silent influence, but the same task naturally elicits those structures, so classification remains ambiguous.
- **Harbor vector, gain 1.00, seed 930301:** the final answer became longer and emphasized automated availability/scheduling, but there was no traceable harbor concept in reasoning. This is an observable response difference, not a demonstrated semantic transfer.
- **Random vector controls:** similarly altered organization and completion length without harbor content. Their presence prevents attributing every neural-vector difference to the harbor association.

All 18 rows, seeds, request hashes, response hashes, finish reasons, reasoning/final byte counts, and term-count diagnostics are in the compact JSON receipt. Complete model outputs are external and were not committed.

## Disposition against the Phase 3.5 questions

1. **Can a static vector be applied to this exact local Gemma stack?** Yes. Startup control-vector loading works, fixed-prefix logits change, and the no-op/replay controls behave deterministically under the frozen configuration.
2. **Can it alter host behavior?** Yes, in this small bench: reasoning and final-response hashes/structure changed under the vector. Effects were bounded and did not require changing model weights.
3. **Does the vector reliably express the harbor association?** Not established. Strong text framing does; the neural vector does not show direct or uniquely attributable harbor semantics in this matrix.
4. **Is the path ready for MNEME production integration?** No. The pinned server accepts control vectors at process startup, not per request; no SAA-to-vector translator was implemented; cvector generation has a Gemma-4 layer-count defect requiring a bench-only shim; and random-vector controls show that semantic attribution needs a better qualification design.
5. **Safety/replay:** No MNEME state was loaded or changed. The bench used `cache_prompt=false`, fixed seeds, isolated raw artifacts, and stopped all remote llama processes afterward.

The result is a valid engineering feasibility boundary: llama.cpp can apply a static hidden-state direction to this local Gemma and the effect is measurable at logits and outputs. The experiment does not justify claiming neural influence, semantic bridging, or production SAA integration. Further work would require a separately authorized design for request-time vector selection, a corrected/qualified Gemma-4 activation capture path, and a held-out semantic test that separates association meaning from generic hidden-state perturbation.
