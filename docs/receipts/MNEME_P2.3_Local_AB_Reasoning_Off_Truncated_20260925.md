# MNEME P2.3 Local Matched Readout — Reasoning-Off Truncation — 2026-09-25

The second fixed-coordinate MSI readout used llama.cpp `--reasoning off`.
All eight local Gemma processes returned ordinary final text, but four
responses (M0, C0, M1, and C2) reached the 96-token output limit and ended
mid-answer. The other four were complete. This is preserved as a bounded
runtime/output-budget failure; no hosted call or MNEME write occurred.

The next same-coordinate schedule keeps both twins matched and raises only
the shared local output allowance to 256 tokens. The probe bank, model
checkpoint, temperature, route bindings, and M/C treatment boundary remain
unchanged.

Raw sanitized records: [JSON](MNEME_P2.3_Local_AB_Reasoning_Off_Truncated_20260925.json).
