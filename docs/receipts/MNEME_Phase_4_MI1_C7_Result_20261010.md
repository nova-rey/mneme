# MI1 C7 diagnostic result

C7 replayed the 40 C5 coordinates with the same underlying questions, seeds, bank data, and sampler, raising `max_tokens` to 4096 and server context to 8192. All calls completed normally. The no-bank and generic-cue/no-bank controls each scored 8/8; visible-bank comprehension scored 7/8. Both sparse latent conditions still scored 0/8, with and without the generic cue. All 16 attached bank fingerprints matched.

The request allowance fixed C6's two truncations but did not resolve the task-format problem: for the simplest four-edge fixture, one seed selected the intermediate node `Moru` instead of the asked-for terminal `Runi`, while the matched second seed returned the correct terminal path. The other three visible fixtures were 6/6 correct. This confirms the C2 two-candidate prompt can induce inconsistent target selection even with enough context and output budget.

The latent outputs completed normally and said `unknown`; their reasoning repeatedly stated that no relationships were present in the prompt. Thus the tested sparse bank did not produce detectable retrieval in this prompt family. C7 is still diagnostic rather than MI1's final disposition: the visible task form is not clean enough, and broad/strong configurations have not yet been retested with corrected capacity.

The [C7 freeze](MNEME_Phase_4_MI1_C7_Calibration_Freeze_20261010.json) and [per-coordinate receipt](MNEME_Phase_4_MI1_C7_Result_20261010.json) include token counts and hashes. Full streamed reasoning and outputs remain local under `/home/nyx/mneme-artifacts/phase4-mi1/calibration-C7/evidence/`.
