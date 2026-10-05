# MNEME Phase 3.9 — Relational Readout: Prepared-First Vast.ai Experiment

**Could our small reader recognize relationships in Gemma on new subjects and new wording, rather than just spotting familiar words?** **APPARATUS FAILURE / INCOMPLETE.** No valid frozen-host feature corpus was captured, so no reader was trained and this run says nothing about whether Gemma does or does not represent the five relations.

## What happened

The prepared experiment passed all controller-side checks: a frozen corpus of 2,400 primary matched synthetic scenes plus 240 controls, held-out domains (`waterworks`, `radio`), a held-out surface-template family, group isolation, lexical audit, mock feature serialization/restart, lifecycle mock, controller storage check, Vast authentication, direct SSH, and a live RTX 3090/CUDA host check.

The required live representation-capture smoke then exercised eight inputs at physical layers 6, 13, 20, 27, 34, and 41 on the pinned HF/BF16 surrogate (`google/gemma-4-E4B-it`, revision `ee0ef6023621cff504d758262d4e04895a5af4a2`; 42 layers, hidden size 2560; Torch 2.6.0+cu124; CUDA 12.4; Transformers 5.19.0.dev0). Hooks fired at the intended module paths, values were finite, and capture took 0.390 seconds for eight inputs.

The repeatability check failed before any full-corpus capture. The original `0.02` absolute tolerance was too tight for exported BF16/float16 values, so the one allowed bounded apparatus correction recorded the measured difference and set a documented `0.5` tolerance. The corrected repeat still produced a maximum absolute difference of **1.0**, exceeding that tolerance. The smoke record was atomically written before it failed; its SHA-256 is `84c18b46e39c470e5c9f7a637d8652bf6e24cdc95e471f2f7d583486c13c7ab5`.

The difference is specifically between a representation captured in a padded two-item batch and a repeated singleton capture. It may be a batching/numerical property of this HF/BF16 host or a capture-path issue. This run did not establish which, and the experiment contract allowed one bounded live correction only. No full feature shards, reader predictions, probes, held-out metrics, or semantic conclusions were produced.

## Frozen intended analysis, not executed analysis

Had capture passed, the controller would have fit only regularized linear binary readers for `CAUSES`, `ENABLES`, `INHIBITS`, `SUPPORTS`, and `DEPENDS_ON`; unknown labels would have remained masked. Validation alone would select layer, feature view, regularization, and threshold. Final evaluation would compare held-out domains, role reversals, entity renaming, same-words/different-structure controls, prevalence, length/position/entity, word/character n-grams, input embeddings, and grouped shuffled labels. This follows the control-task warning from Hewitt and Liang, [*Designing and Interpreting Probes with Control Tasks*](https://aclanthology.org/D19-1275/): raw probe accuracy is not evidence of an abstract readout when a probe can exploit input shortcuts.

The committed prediction CSV contains the eight smoke-coordinate IDs with blank predictions and the explicit reason `apparatus_failure_before_probe`; it is not a substitute for a readout result.

## Evidence, cost, and cleanup

The canonical partial artifact is retained outside Git at `/home/nyx/mneme_artifacts/phase39-relational-readout-20261004-r1`. Its directly readable external manifest is committed as [MNEME_Phase_3_9_Relational_Readout_Vast_External_Artifact_Manifest_20261004.json](MNEME_Phase_3_9_Relational_Readout_Vast_External_Artifact_Manifest_20261004.json), including hashes for the corpus, source, smoke, logs, input-transfer verification, and lifecycle receipt. Model weights/cache, account credentials, and account-private metadata were not copied into Git.

One labeled Vast instance was created: ID `54227145`, an RTX 3090 with 24,576 MiB advertised VRAM. Its stated storage-adjusted rate was $0.2731076389/hour. It existed for 477.55 seconds; the estimated charge is **$0.0363**. An immediate invoice query did not provide a parseable attributable line item, so the estimate is not represented as an observed bill.

The partial smoke was transferred and parsed on the controller before teardown. The instance destroy request succeeded on the first attempt, and a fresh account listing confirmed that ID absent. **OWNED VAST RESOURCES DESTROYED AND VERIFIED.** This follows Vast’s distinction between stopped instances, which retain billable storage, and destroyed instances, which delete the resource ([instance lifecycle documentation](https://docs.vast.ai/guides/instances/manage-instances), [billing documentation](https://docs.vast.ai/guides/reference/billing)).

## Boundary

No MNEME instance, ON-30, CompactStore, SAA, introspection, developmental history, production Q2 runtime, model weights, vector, intervention, writer, or base model was modified. The HF/BF16 host remains a research surrogate and was never claimed equivalent to the local Q2 GGUF host.

A future retry would need a separately authorized, evidence-backed change to the repeatability/capture protocol; it must not silently treat this smoke as a successful full capture or reuse absent features.
