# MNEME P0.3 FakeHost acceptance receipt

Date: 2026-09-18
Baseline: P0.3 implementation on `main`

The network-free acceptance demonstration completed in an isolated temporary store.
The full execution runner was not invoked.

- Scientific experiment identity: `shared-input-control / revision 3`.
- Contract SHA-256: `10742dd4ba3bb16b2f35d9513dc0bdbfa0699c07ee71e61f2202913fe9b92dad`.
- Lineage A: `e1048f01-44ff-426b-8b81-0995d57d3715`.
- Lineage B: `4927680a-f53b-454f-bad3-d85e4c6a2ced`, forked from A's checkpoint.
- Lineage D: `0494020e-0248-446b-acbf-4de2deb890f1`, independent sibling from the same checkpoint.
- Checkpoint: `2ef575d6-08a8-4ba2-b04e-2f7ddda3c05a`.
- Resolved budget: 2 development calls, 4 evaluation calls, 2 isolation calls, 8 total.

The demonstration proved that B and D begin at child revision zero, B can advance
independently to revision one, and D remains at revision zero. A paired FakeHost
evaluation produced a `RESULT`; retrying it with a failing host returned the existing
receipt without another generation. Checkpoint file and logical state digests were
unchanged before and after evaluation.

The following deliberate failures were observed: development/evaluation duplicate
content, unsupported seed capability, and model-call budget overflow. Restarted run
inspection verified the immutable prepared artifacts. The receipt contains no prompts,
model outputs, credentials, or provider headers.

This receipt proves the P0.3 laboratory-control invariants only. It is not evidence of
developmental learning, behavioral individuality, personality, or a completed P0.4 study.
