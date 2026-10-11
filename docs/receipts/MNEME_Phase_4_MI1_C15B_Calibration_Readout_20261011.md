# MI1 C15B single-slot bank-encoding calibration

C15B completed all **80/80** frozen coordinates under the corrected single-slot server configuration. The frozen calibration gate failed, so **no held-out C15B confirmation was run**.

| Condition | Correct |
|---|---:|
| No bank → `unknown` | 8/8 |
| Cue only → `unknown` | 8/8 |
| Visible A | 8/8 |
| Visible B | 8/8 |
| Latent raw bank A / B | 0/8 each |
| Latent system-turn bank A / B | 0/8 each |
| Latent user-turn bank A / B | 0/8 each |

This identifies the result as a semantic-readout failure rather than a failed generation task or indiscriminate answer bias: the same prompts are answered correctly when the facts are visible and rejected as unavailable when placed in any of the three tested side-bank encodings. Every expected bank attachment was recorded with its matching fingerprint and selected-site configuration.

The C15 multi-slot crash and C15B single-slot rerun remain separate: the former is an apparatus failure preserved with an empty request stream; the latter reran the entire frozen calibration matrix with `--parallel 1`, completing normally. C15B rules out the tested hypothesis that adding Gemma system/user role tokens to the encoded bank solves latent fact retrieval. It does not test an assistant-role memory encoding and does not establish the final MI1 disposition.

Exact requests, complete reasoning/final outputs, and per-attempt attachment receipts remain outside Git under `/home/nyx/mneme-artifacts/phase4-mi1/c15b-encoding/evidence/`. Their index SHA-256 and the compact score/freeze hashes are recorded in the [machine-readable readout](MNEME_Phase_4_MI1_C15B_Calibration_Readout_20261011.json).
