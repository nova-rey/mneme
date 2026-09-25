# MNEME P2.3 Local Matched Readout v3 — Raw Evidence — 2026-09-25

The final fixed local readout schedule used the pinned Gemma 4 E4B Q2 GGUF
on the MSI, llama.cpp CUDA runtime, reasoning off, and a matched 384-token
allowance for both M and C. It executed eight calls: four probe pairs, one M
and one C response per pair. All processes exited successfully and produced
non-empty decoded text. The M responses selected the credited garden →
paint-project route only for the first two probes; C selected no route. The
last two probes are unrelated controls and selected no route for either twin.

The raw sanitized request/result records are preserved in this JSON. The
controller response parser removes only deterministic llama.cpp prompt/banner
material; no output is rewritten for semantic content.
