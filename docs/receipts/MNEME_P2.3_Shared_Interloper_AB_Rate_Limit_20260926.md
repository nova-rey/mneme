# P2.3 shared-Interloper A/B live attempts — provider rate-limit stop

Date: 2026-09-26  
Experiment: `p2.3-valid-three-thread-shared-interloper-ab`  
Disposition: `INVALID_PROVIDER_RATE_LIMIT`  

Two prospective launches were attempted from the pushed shared-Interloper
harness. Both stopped at the first fixed Qwen qualification coordinate. The
provider returned HTTP 429 before a model response was available. The durable
pilot reservations are preserved under the private run workspaces:

- `/tmp/mneme-p23-shared-ab-20260926`, run `p23-shared-interloper-ab-20260926`;
- `/tmp/mneme-p23-shared-ab-20260926-r2`, run `p23-shared-interloper-ab-20260926-r2`.

Each attempt recorded `qualification-0` as `UNCERTAIN` with role
`assessor-qualification`, model `Qwen/Qwen3-235B-A22B-Instruct-2507`, and
provider `DeepInfra`. No provider result content was returned. No Gemma
development call, specialist extraction, learner update, treatment exposure,
readout, or evaluation call was dispatched in either attempt.

The first attempt used the initial runner pacing. The second used the fixed
five-second Qwen pacing correction and failed identically. This distinguishes
the stop from the role-serialization or treatment-gate logic: those stages
were never reached. The two 429 responses are preserved as historical failed
attempt evidence and are not reclassified as qualification successes.

No credential, authorization header, or secret-bearing environment data is
included here.
