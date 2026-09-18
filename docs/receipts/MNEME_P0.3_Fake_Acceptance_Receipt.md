# MNEME P0.3 FakeHost acceptance receipt

Date: 2026-09-18
Baseline: P0.3 implementation on `main`

The network-free acceptance demonstration completed in an isolated temporary store.
The full execution runner was not invoked.

- Scientific experiment identity: `shared-input-control / revision 3`.
- Contract SHA-256: `b3146664e6e3ccbd8bff879d1d8055c18a6135270581291c917465768bd75d90`.
- Lineage A: `81a27a75-d27d-4071-b78e-7d2ed49a236d`.
- Lineage B: `4854b2f8-699b-4832-bb15-3d81bc5ecc4f`, forked from A's checkpoint.
- Lineage D: `5ff0698c-c29b-4e58-8b93-27d1a3940433`, independent sibling from the same checkpoint.
- Checkpoint: `79eb5b2c-c57b-47e2-a116-9cd05d37c6f8`.
- Resolved budget: 2 development calls, 4 evaluation calls, 2 isolation calls, 8 total.

The demonstration proved that B and D begin at child revision zero, B can advance
independently to revision one, and D remains at revision zero. Two paired FakeHost
evaluation checks produced `RESULT` records; retrying one with a failing host returned
the existing receipt without another generation. Checkpoint file and logical state
digests were unchanged before and after evaluation, and identical administrative
metadata produced identical FakeHost output.

The following deliberate failures were observed: the same dataset file assigned to both
roles, development/evaluation duplicate content, cross-split scenario family,
unsupported seed capability, model-call budget overflow, and changed run intent.
Restarted run inspection verified the immutable prepared artifacts. The receipt contains
no prompts, model outputs, credentials, or provider headers.

This receipt proves the P0.3 laboratory-control invariants only. It is not evidence of
developmental learning, behavioral individuality, personality, or a completed P0.4 study.
