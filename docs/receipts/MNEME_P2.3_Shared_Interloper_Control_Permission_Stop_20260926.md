# MNEME P2.3 Shared-Interloper Control Permission Stop

Date: 2026-09-26  
Status: **INVALID — IMPLEMENTATION DEFECT**  
Run: `p23-shared-interloper-ab-20260926-r4`

The first prospective run using the qualified local NLI assessor stopped at
`development-C-A-t1`. The control twin was created with
`provider_reuse=false`, but its ordinary two-turn chat history includes its own
prior assistant response. The continuity boundary therefore correctly denied
the request before dispatch. No behavioral comparison or scientific result was
assigned.

The persisted run contains the preflight, local assessor qualification, the
first shared Qwen continuation, both t0 Gemma responses, M t1 response,
extractions, and assessment artifacts. The sanitized artifact manifest digest
is recorded in the accompanying JSON receipt. No historical run was modified.

The correction is narrow: both twins receive `provider_reuse=true` solely so
ordinary conversation history can be serialized. The control retains
`interpret=false`, `recall=false`, and `learn=false`; it receives no MNEME
state or influence. A focused regression now asserts this boundary. The failed
run is preserved unchanged and a fresh run ID is required.
