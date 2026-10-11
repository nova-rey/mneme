# MNEME Phase 4 MI1 C16 calibration readout

C16 tested whether representing the same one-hop codeword fact as a completed Gemma assistant turn would make a selected side-memory bank retrievable. It did not. The complete 48-call calibration finished, but neither latent polarity reached a single correct answer. The held-out matrix was therefore not run.

| Condition | Correct | Rate |
|---|---:|---:|
| No bank, answer unknown | 8/8 | 100% |
| Cue only, answer unknown | 8/8 | 100% |
| Visible fact, polarity A | 7/8 | 87.5% |
| Visible fact, polarity B | 8/8 | 100% |
| Assistant-turn side bank, polarity A | 0/8 | 0% |
| Assistant-turn side bank, polarity B | 0/8 | 0% |

All 48 scheduled coordinates have complete durable receipts; none are missing or uncertain. Thus the negative result is not a server interruption or scoring denominator issue. The unchanged no-bank/cue and visible controls establish that Gemma could answer this task when the fact was visible and correctly abstain without it. The assistant-turn banks were loaded with the execution-bound native bank fingerprints, but the model still answered `unknown` for both hidden values. In a representative reasoning trace, Gemma explicitly says that it has no specific hidden note available and should answer unknown. This shows that bank presence and numeric attention do not establish semantic access to its contents.

The C16 freeze kept fixture family, wording of the fact, question, selected sites, 4x bank prior, model, seeds, sampler, reasoning mode, and one-slot server configuration fixed. The changed factor from C15B was bank encoding: the fact was tokenized as a completed assistant turn. The identical 0/8 latent result means that this role encoding did not repair hidden factual retrieval. The earlier C15 multi-slot crash remains a separate apparatus failure; C15B and C16 both used one slot and completed.

This result is limited to atomic retrieval on the exact-Q2 Gemma host and this selected-site implementation. It does not alone decide whether process-prior/association banks can influence open-ended reasoning. It does rule out treating the 4x assistant-turn bank as a qualified retrieval mechanism. No C16 confirmation calls were authorized by the frozen gate, and none were made.

## Evidence and reproducibility

The frozen plan SHA-256 is `ed1ed7028f6187b0eab33a09413e588814432b0fe3c83af306467c2796369a20`; the execution binding SHA-256 is `e11d1f9666034a1b7e8cbaa668155258ca55a0de7f6a1594b99541c165c9c61a`. The evidence index SHA-256 is `ecd63e75f37338e969948ec69afa79745b88fa29cf1a90302fdb0632b3a85e6a`, and the scored calibration SHA-256 is `01e926308f4e27409d0e4b91b681dfeff3074e1506a133e943a33dbcabe7096c`.

Complete requests, reasoning traces, final answers, and per-attempt receipts remain outside Git under `/home/nyx/mneme-artifacts/phase4-mi1/c16-assistant/`. The machine-readable summary is [MNEME_Phase_4_MI1_C16_Calibration_Readout_20261011.json](MNEME_Phase_4_MI1_C16_Calibration_Readout_20261011.json).
