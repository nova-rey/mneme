# MNEME P2.3 Matched-Twin Local Readout Schedule v2 — 2026-09-25

This fixed schedule preserves the four probe pairs, exact local Gemma
checkpoint/runtime, M/C memory boundary, temperature, and probe order from the
route-view correction. Both twins use the same 256-token output allowance.
The only change from the preserved reasoning-off attempt is the shared output
limit, raised from 96 after four responses were visibly truncated.

This schedule is an engineering correction to obtain complete readout text,
not favorable-sample selection. Its machine-readable frozen request set is
[here](MNEME_P2.3_Matched_Twin_AB_Schedule_v2_20260925.json).
