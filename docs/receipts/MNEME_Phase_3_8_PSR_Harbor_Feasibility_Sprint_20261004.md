# MNEME Phase 3.8 — PSR Harbor Prompt-Replacement Feasibility Sprint

## Could we reproduce the known harbor prompt’s influence inside Gemma without showing Gemma the harbor prompt?

**NOT RUNNABLE LOCALLY — implementation/host blocker.** No PSR training or inference was launched. The exact host is the pinned Q2 GGUF running through llama.cpp; Nokia Bell Labs’ published `Focused` PSR requires a differentiable Hugging Face/PyTorch transformer host with residual-stream hooks. Replacing it with a static control vector, or training on a different HF representation and applying the result to Q2, would not answer the requested exact-host question.

This is neither a negative result for PSR nor a semantic result. It is a concrete incompatibility between the published intervention ABI and the qualified exact host.

## What was audited

- Published implementation: [`Nokia-Bell-Labs/steer-like-the-llm`](https://github.com/Nokia-Bell-Labs/steer-like-the-llm), commit `3d916c618d146c5d657f055e432a432b0fa493c6` (BSD-3-Clause), inspected at `/tmp/steer-like-the-llm-phase38`.
- Published paper: [Heyman et al., *Steer Like an LLM*](https://proceedings.mlr.press/v306/heyman26a.html), PMLR 306 (2026).
- Exact host checked at 2026-10-04T22:50:22Z: `brokeass-msi`; NVIDIA RTX 3060 Laptop GPU with 6144 MiB VRAM; 61 GiB RAM; 53 GiB free disk.
- Exact model/runtime: `google/gemma-4-E4B-it`, `/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`, SHA-256 `79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`, pinned CUDA llama.cpp `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`.
- The local Python environment has PyTorch 2.14.1+cu130 and Transformers 4.57.6, but inspection found no HF Gemma weights—only the Q2 GGUF.

The existing Phase 3.5 calibration remains untouched. It established that forced textual harbor consideration can visibly engage harbor/tide/docking structure, while the static Q2 harbor vector did not establish semantic transfer. This sprint did not repeat that calibration or make any model call.

## Why the exact host cannot run Published Focused / PSR

`FocusedSteeringModule` is not a constant vector. For each selected layer it learns both an H→1 direction projection and an H→1 token-location projection. At generation time it computes a location-dependent coefficient for every token and adds the resulting direction through PyTorch tensors.

The upstream `IntervenedModel` expects a Hugging Face `PreTrainedModel`: it resolves modules with `model.get_submodule`, installs `register_forward_hook`s, calls `model.forward`, retains each residual stream, and invokes `model.generate`. Its `psi` objective runs the harbor-prompted reference forward pass under `torch.no_grad()`, runs the unprompted/intervened pass differentiably, and minimizes MSE over aligned residual activations. The training loop then calls `loss.backward()` and optimizes the intervention parameters.

The resident llama.cpp Q2 path has none of those interfaces. Phase 3.5 established that its control vector is a static, startup-loaded direction; the server exposes no request-time cvector field. It does not expose a PyTorch module graph, residual tensors for `psi`, autograd, or Focused’s dynamic token-location function. A static cvector substitution would be ordinary constant steering—the mechanism Phase 3.8 explicitly forbids calling PSR.

## Resource finding

Even if native HF weights had existed locally, the 6 GiB RTX 3060 could not hold a faithful BF16 4B host: weights alone are roughly 8 GB before residual capture, two training paths, and autograd activation storage. The upstream code uses one `model.device` and direct hooks; it does not implement an Accelerate device-map/offload path.

The smallest credible separate prototype is a **24 GiB GPU**, short context, batch size 1, frozen host weights, disabled cache, explicit gradient handling, and checkpointing as needed. That would be a **Hugging Face Gemma surrogate**, not proof on the exact Q2 llama.cpp host. A 16 GiB/offload attempt might be technically improvisable, but it is not a reliable one-day faithful path and would require a port of upstream assumptions. No amount of additional VRAM alone makes the Q2 llama.cpp ABI execute the published method.

## Consequence and next owner choice

No prompt corpus, training checkpoint, evaluation prompt, PSR parameter, generation, or random control was created. There is therefore no semantic outcome to compare with the A/B/C harbor calibration.

A later effort must choose one distinct research direction:

1. **Exact-Q2 PSR port:** design and qualify a differentiable Q2 capture/training backend plus a dynamic per-token Focused runtime ABI in llama.cpp. This is substantial implementation research, not a one-target sprint.
2. **HF-surrogate qualification:** explicitly use native Hugging Face Gemma on at least a 24 GiB GPU, first establish host-space and behavioral comparability to the Q2 host, then run PSR. Its conclusions must be labeled HF-surrogate rather than exact-Q2.

Neither direction is started here. No MNEME state, SAA, ON-30, CompactStore, learner, developmental evidence, resident inference service, or production behavior was modified.

The companion [JSON receipt](MNEME_Phase_3_8_PSR_Harbor_Feasibility_Sprint_20261004.json) contains the source, resource, and boundary evidence in machine-readable form.
