# MNEME Phase Two C/R/F0 preflight

Status: `FROZEN_FOR_PROSPECTIVE_EXECUTION`

This preflight freezes the new prospective experiment `p23-f0-shared-
interloper-20260926`. It does not modify r6, r7, or any prior Phase Two
receipt. Development uses the existing shared Qwen3-30B Interloper, local
Gemma 4 E4B, GLiNER2.5 extraction, and pinned local DeBERTa NLI assessment.

The developmental trajectory has three fresh threads (balcony maintenance,
trip planning, and remote workshop design) with three turns per thread. M is
the writable MNEME subject and C is the no-MNEME control. The same shared
Interloper message and paired local-Gemma seed are used at each coordinate.
Readout freezes M after development and compares C, R, and F0 over two neutral
probes and two predetermined repetitions. C uses no memory, R uses
`selection_policy="learned-v1"`, and F0 uses `selection_policy="field-v0"`.

F0 configuration is frozen as `f0-graph-pressure-v1`: maximum depth 2,
attenuation 600000 fixed-point units per hop, minimum pressure 20000, total
budget 1000000, four contributors, 900 rendered characters, and exploration
off. The F0 audit remains in the controller trace and is separate from the
compact host-visible payload. R delivery is reported independently because a
neutral probe may have no eligible discrete route; that case cannot be called
a route-mediated effect.

The runner is `tools/run_p23_f0_shared_interloper.py`. It has no historical
run ID or output directory in common with prior experiments, persists requests
and responses before interpretation, rejects empty participant/model output,
uses frozen read-only evaluation checkpoints, and publishes raw readouts plus
deterministically blinded C/R/F0 pairings. The prospective run is authorized by
the active Phase Two steer; no provider calls are made by this preflight.
