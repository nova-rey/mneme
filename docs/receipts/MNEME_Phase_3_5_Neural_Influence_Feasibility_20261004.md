# MNEME Phase 3.5 Neural Influence Feasibility Bench

**Disposition: BLOCKED before model-dependent stages by an external host/capability condition.**

This is a standalone feasibility bench. It did not load or modify MNEME state, CompactStore, SAA, learner, introspection, developmental evidence, or production inference behavior.

## Executive result

The pinned llama.cpp source and model-free mechanics are auditable and pass their checks. The neural stages could not run: the resident MSI is Tailscale-reachable, but the configured Gemma service ports 64170 and 64173 refused connections; SSH authentication is unavailable. The resident server design also loads control vectors at process startup and exposes no per-request control-vector field. Therefore the exact Gemma process needed for vector-enabled completions was unavailable. No alternate model/provider was used.

The prior isolated A/B/C prompt-strength receipt is preserved as an external anchor. It is evidence about prompt framing, not evidence that a hidden-state vector affected Gemma.

## Source and mechanical audit

- Repository HEAD: `a59eb11ad98941f005e44c6daacd440e07c43842`.
- Pinned llama.cpp: `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`.
- CPU-only build: `/tmp/mneme-p35-llama-build`; `llama-cvector-generator` SHA-256 `274ff77e43d970c94a80140c8822d8f827fee1cca9baf595fb69eb3ee183f289`; `llama-completion` SHA-256 `f134f5d777d1c77accdd74269ca0407ca6335f5f9eaca7a63789cacea8b0a188`.
- Gemma 4 calls `build_cvec(cur, il)` before each `l_out` callback. The adapter allocates no layer-0 tensor, maps `direction.N` to the layer-N slot, and accepts an inclusive layer range.
- The generator captures F32 `l_out` tensors, differences positive/negative prompt pairs, and emits normalized `direction.N` tensors. The pinned mean reducer divides by the norm without a zero-norm guard; zero vectors must be rejected by the harness.
- `llama-server` supports startup flags `--control-vector` and `--control-vector-layer-range`. Its `/v1/chat/completions/control` route is a reasoning-control route accepting `reasoning_end`, not hidden-state vector injection.

Model-free synthetic checks from `tools/phase35_model_free_checks.py` passed (receipt mirror: `/tmp/p35-model-free-checks.json`): normalization, layer indexing/range, layer-0 no-op, gain scaling, disable/no-op, dimension validation, and F32 serialization. The pinned zero-norm behavior is recorded as a caller-side safety requirement.

## Existing live-model anchor

The earlier isolated Gemma receipt was copied to `/home/nyx/mneme_artifacts/phase35-neural-feasibility-20261004/anchor/` and hash-recorded. It used `google/gemma-4-E4B-it`, the pinned GGUF, seed `930300`, CUDA, `cache_prompt=false`, and the three A/B/C prompt framings. Its duplicate preflight passed. A/B/C are retained as contextual prompt-strength evidence only; no neural vector was applied.

## Stage disposition against the specification

| Stage | Status | Evidence |
|---|---|---|
| A. source audit and isolated build | PASS | Pinned source, API, Gemma hook, adapter mapping, loader, generator, and server route audited; CPU build completed. |
| B. eight mechanical completions | BLOCKED | Required exact local Gemma process unavailable. |
| C. neural/non-neural semantic matrix | BLOCKED | Requires the exact GGUF plus a vector-capable dedicated process; resident HTTP server cannot accept cvec per request. |
| D. frozen gain/site selection | NOT RUN | Must occur before evaluation outputs and after C can produce real vectors. |
| E. integrated readiness | NOT RUN | No neural bench results to integrate; production integration was intentionally untouched. |
| F. safety/rollback/replay | NOT RUN | No vector-enabled process was available to exercise it. |


## Requirement-level audit

| Requirement | Status | Evidence boundary |
|---|---|---|
| Exact Gemma can apply/scale/disable/restore an intervention | **UNRESOLVED** | Source and arithmetic pass; exact-model hook/logit smoke requires the MSI process. |
| Synthetic vector produces identifiable behavior | **BLOCKED** | Requires real Stage B/C completions. |
| Pinned source and project brief inspected | **PASS** | Source commit and brief hash are in the JSON companion. |
| Actual current model/runtime/GPU inspection | **PARTIAL, HISTORICAL ONLY** | Prior determinism receipt records the calibration values; the current process was unreachable. |
| Stage A mechanics and model-free dry run | **PASS** | Separate CPU build and arithmetic checks pass. |
| Stage B mechanical Gemma smoke | **BLOCKED** | No vector-capable exact-model process. |
| Stage C construction and semantic matrix | **BLOCKED** | No exact-model activation capture or vector process. |
| Durable neural evidence and safety replay | **NOT RUN** | No neural calls occurred. |

The prior A/B/C prompt-strength experiment is retained as contextual evidence only. It does not satisfy Stage B, Stage C, or the neural comparison matrix.

## Smallest future bridge proposal

The bridge remains a proposal, not an implementation:

```text
SAA FieldResult
  -> portable active-neighborhood descriptor
  -> host-specific compiler
  -> qualified control-vector GGUF
  -> isolated application/reset
  -> frozen host response
```

SAA must remain the selector. The missing descriptor must preserve the selected neighborhood’s conceptual direction without replacing it with a convenient cached topic. The compiled artifact must bind to the GGUF, tokenizer/template, llama.cpp build, extraction/application site, layer range, and normalization. The current resident HTTP server cannot supply per-request vectors, so the first safe path is a dedicated process or isolated C API context with explicit reset, removal, quarantine, and incompatible-artifact handling. PSR and HyperSteer remain separate future options; neither is needed for this bench.

## Exact external blocker

At audit time Tailscale reported `brokeass-msi` online at `100.115.208.48`, but both configured inference ports refused connections. TCP/22 accepted connections, but the available local SSH identities were rejected for the tested accounts; no service restart or remote mutation was attempted. The model file and CUDA runtime are not present on this machine, so the exact local Gemma calls cannot be reproduced here. The proper next step is to restore the configured resident service or provide authorized access to launch a dedicated vector-enabled `llama-completion`/`llama-server` process using the pinned GGUF. Substituting another model/provider would violate the specification.

## Integrity and scope

- No MNEME state, CompactStore, SAA, learner, introspection, developmental history, or production runtime was loaded or modified.
- No model-dependent completions were made by this bench after the preserved A/B/C anchor.
- Raw future neural evidence must be written externally with complete request/response bytes, vectors, configurations, and hashes; only compact derived receipts belong in Git.
- This report does not claim neural feasibility, semantic effect, or integration readiness. Those remain unresolved pending the exact host capability.

Machine-readable companion: `MNEME_Phase_3_5_Neural_Influence_Feasibility_20261004.json`.

