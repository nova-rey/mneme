# MNEME P2.3 Local Matched Readout — Reasoning-On Stop — 2026-09-25

The first eight local MSI readout calls used the frozen M/C request coordinates,
exact Gemma 4 E4B Q2 checkpoint, and 96-token generation allowance. The
llama.cpp chat template spent the entire allowance in visible reasoning output
and returned no usable final participant answer for any pair. All eight
processes exited successfully, but the decoded content was incomplete
reasoning/truncation rather than a valid readout response. No DeepInfra call
was made and no MNEME developmental state was written.

This is preserved as a local runtime configuration failure. The model and
checkpoint are not being treated as unsuitable from this sample. The bounded
correction sets llama.cpp reasoning explicitly to `off` and records that
setting in the local host fingerprint before rerunning the same frozen M/C
coordinates.

Raw sanitized request/result records: [JSON](MNEME_P2.3_Local_AB_Reasoning_On_Stop_20260925.json).
