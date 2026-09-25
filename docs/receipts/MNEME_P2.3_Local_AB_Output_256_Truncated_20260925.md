# MNEME P2.3 Local Matched Readout — 256-Token Stop — 2026-09-25

The v2 frozen M/C schedule used reasoning-off local Gemma with a shared
256-token allowance. All eight calls exited successfully. Seven responses are
usable after deterministic removal of llama.cpp's echoed `(truncated)` prompt
prefix. M0 still reached the output bound and ended with an unfinished
meta-level tail (`Given the memory data`). No hosted call or MNEME write
occurred.

This remains preserved as a bounded output-budget failure. The final fixed
schedule raises the same shared allowance to 384 tokens; no probe, model,
condition, sampling setting, or route binding changes.

Raw sanitized records: [JSON](MNEME_P2.3_Local_AB_Output_256_Truncated_20260925.json).
