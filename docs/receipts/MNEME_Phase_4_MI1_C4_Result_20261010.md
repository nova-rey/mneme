# MI1 C4 diagnostic result

C4 is diagnostic, not scored Test A/B/C. Its 56/56 requests completed and are durably journaled. All 32 attached-bank coordinates returned the expected parsed-bank fingerprint.

The explicit two-line contract did not stabilize this prompt family: visible positives were 5/8, no-bank unknown controls 2/8, and generic-cue/no-bank controls 1/8. Six of eight no-cue baselines and seven of eight cue baselines reached the output limit while reasoning without a final. Every latent condition scored 0/8. Sparse conditions frequently answered unknown or failed to finish; broad conditions produced code fences, repetitive labels, and short-token loops.

This is a calibration/control failure, not evidence that latent memory has no effect. It also shows C2's successful negative controls do not transfer just by copying its answer schema: its surrounding task framing matters. C3/C4 collectively isolate prompt framing and exposure, but neither qualifies reliable behavioral uptake.

## Next frozen diagnostic

C5 reuses C2's complete directed-reachability system contract and two-candidate question structure, which previously yielded reliable unknown controls, while retaining C3's simple rule chains. It crosses no-bank/visible/sparse-latent with and without a generic memory cue. The no-bank and latent prompts are identical within each cue stratum. C5 is frozen before generation and remains diagnostic; it does not change any success threshold or count as Test A/B/C.

The [C4 freeze](MNEME_Phase_4_MI1_C4_Calibration_Freeze_20261010.json) and [machine-readable result](MNEME_Phase_4_MI1_C4_Result_20261010.json) preserve hashes and coordinate outcomes. Full reasoning and response streams remain local under `/home/nyx/mneme-artifacts/phase4-mi1/calibration-C4/evidence/`.
