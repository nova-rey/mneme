# MI1 C6 context-window replay

C6 reissued all 40 C5 requests with the same request bodies, seeds, sampler settings, bank artifacts, and scoring rubric. The isolated server context alone increased from 512 to 4096; each request still had `max_tokens=2048`.

The larger context fixed the C5 baseline-completion failure: both no-bank conditions scored 8/8. Visible-bank comprehension scored 6/8; the two misses were the longer four-edge fixture and both exhausted the 2,048 generated-token request cap. The other six visible coordinates completed correctly. Both latent conditions scored 0/8, with and without a generic memory cue; these 16 outputs completed normally and answered `unknown`. All attached-bank fingerprints matched. This is evidence against behavioral uptake at the tested sparse selector on these fixtures, not a general failure conclusion for MI1.

The 2,048-token cap is now the remaining task-completion confound for the long visible control. C7 is frozen to replay the same coordinate matrix and bank conditions with only that request allowance raised to 4096 and server context to 8192. C6 stays immutable and diagnostic; neither C5 nor C6 substitutes for scored Test A/B/C.

See the [C6 freeze](MNEME_Phase_4_MI1_C6_Calibration_Freeze_20261010.json) and [per-coordinate JSON receipt](MNEME_Phase_4_MI1_C6_Result_20261010.json). Full raw streams remain local under `/home/nyx/mneme-artifacts/phase4-mi1/calibration-C6/evidence/`.
