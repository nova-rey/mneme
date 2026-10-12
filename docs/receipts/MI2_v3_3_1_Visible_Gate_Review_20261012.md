# MI2 v3.3.1 visible-guidance gate review

**Disposition: VISIBLE GUIDANCE GATE FAILED. No latent side-memory condition was run.**

The frozen quantum-mechanics process card produced a small, localized signal, but not a repeatable enough improvement to authorize the latent comparison. Across three frozen tasks and two matched seeds, visible guidance improved the process score on one task only: the mean change was **+0.167/3**, versus the frozen pass requirement of **+0.50/3** and positive changes on at least two tasks. There was no scored answer harm, but that does not substitute for the missing process effect.

The paper’s “8/8 visible” MI1 result was a direct short-fact control: Gemma could answer when the fictional facts were present in ordinary text. It was not an 8/8 result for procedural guidance. MI1’s fictional-recall negative remains unchanged.

## Frozen result

The duplicate baseline preflight matched byte-for-byte in both reasoning and final answer. All 12 matrix calls and both preflight calls completed with `finish_reason=stop`; all requests, streamed responses, and complete outputs are preserved in the external run journal. The model, Q2 GGUF, llama.cpp build, reasoning mode, sampler, seeds, and `cache_prompt=false` were frozen. No bank was constructed or attached.

| PHYSICS quantum item | Baseline process | Visible-card process | Delta | Normalized answer score |
|---|---:|---:|---:|---:|
| `quantum/1-1041` | 1.00/3 | 1.00/3 | 0.00 | 0.50 → 0.50 |
| `quantum/3-3025` | 1.00/3 | 1.00/3 | 0.00 | 0.00 → 0.00 |
| `quantum/3-3047` | 1.00/3 | 1.50/3 | +0.50 | 0.00 → 0.167 |
| **Mean** | **1.00/3** | **1.167/3** | **+0.167** | **0.167 → 0.222** |

On `quantum/3-3047`, one visible-guidance seed produced an explicit time-evolved spinor where the matched baseline did not. The response still failed the measurement-probability and transition-time components; the other seed did not provide the state. The other two tasks showed no process-score change, and their main physics errors remained under both conditions. Thus the visible treatment was not wholly inert, but this small one-task/one-seed improvement fails the frozen replication gate.

## Diagnosis and limits

The treatment was the paper’s Appendix E quantum process card, shown visibly in the system context, and the tasks were selected for direct alignment with its distinctions among state/spectrum, operator time evolution, measurement, and approximation. Gemma often named the right general category (for example, Heisenberg evolution) yet failed the required calculation. This supports the inference that its bottleneck on these examples was often execution of the physics, not merely choosing which kind of problem it faced. It does not prove that interpretation for every response.

The gate is deliberately a prerequisite: because visible procedural guidance did not clear it, the latent condition would not distinguish side-memory failure from the model’s inability or unwillingness to use this guidance. Accordingly, there is **no MI2 latent-guidance result** in v3.3.1. The paper’s Qwen3 results do not establish that Gemma 4 E4B Q2 has the same capability.

Prior MI2 process-card calibrations remain immutable: v3.1 atomic guidance had zero process-score delta; v3.2 electromagnetism guidance had mean delta −0.333/3, zero positive task deltas, and answer harm 0.133; v3.3.1 quantum guidance has +0.167/3 and one positive task. Together they show weak and inconsistent visible-card response across three scientific subjects, not a latent-memory failure.

## Evidence and next gate

The compact machine-readable score includes the frozen rubric scores and evidence excerpts plus SHA-256 hashes for every coordinate’s request, stream, full output, reasoning, and final answer. Complete human-readable reasoning and answers remain outside Git at:

`/home/nyx/mneme-artifacts/phase4-mi2/calibration-run-v3.3.1/journal/`

The selected model and runtime are unchanged. The isolated server was stopped after the completed run and its port was verified closed.

The technically justified next step is one prospectively frozen calibration with a different, more directly operational paper card and tasks from its domain, selected from source text and official answer structure before any new output. It must retain the visible-first gate and stop without bank work if the response is again absent or inconsistent. It must not reuse the one improved coordinate as a target for tuning. If a distinct aligned card also fails to produce a repeatable visible effect, the evidence will support stopping MI2 for this Gemma host without claiming the authors’ results or other models are false.
