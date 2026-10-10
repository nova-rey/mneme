# MI1 C5 diagnostic result

C5 did not qualify MI1 efficacy. All five conditions scored 0/8 on visible final answers: no-bank, no-bank with a generic memory cue, visible bank, sparse latent bank without cue, and sparse latent bank with cue. Forty of forty request/result pairs are durable; all 16 attached-bank fingerprints match their frozen variants.

The failure is explained by the diagnostic server configuration. It was launched with `--ctx-size 512`. For 39/40 calls, llama.cpp recorded `prompt_n + predicted_n == 512`; each of those ended with `finish_reason: length`. The remaining call stopped normally below the limit. This is direct evidence that prompt plus reasoning exhausted the context window before the final answer. C5's zero visible score therefore cannot be interpreted as a side-memory efficacy result.

C5 reused C2's full directed-reachability contract and C3's simple chains. The long contract prompted extensive self-checking, but the decisive instrumentation is the exact 512-token boundary, not a subjective reading of the reasoning. The proper next test is a byte-matched replay with only server context capacity increased. C5 remains immutable and diagnostic; it does not replace or waive the frozen Test A/B/C suite.

The [C5 freeze](MNEME_Phase_4_MI1_C5_Calibration_Freeze_20261010.json) and [compact machine receipt](MNEME_Phase_4_MI1_C5_Result_20261010.json) contain per-coordinate hashes, token counts, and outcomes. Full streamed reasoning and model output remain local under `/home/nyx/mneme-artifacts/phase4-mi1/calibration-C5/evidence/`.
