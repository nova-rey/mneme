# MNEME P2.3 Cross-Thread Continuity v6 — Final Receipt

Date: 2026-09-25  
Historical run: `cross-thread-v6`  
Correction commit: [`0009575`](https://github.com/nova-rey/mneme/commit/0009575)

## Disposition

`INCONCLUSIVE` for the cross-thread MNEME-influence question.

The three-thread conversation executed with the corrected role-perspective harness, local Gemma, and the pinned GLiNER2.5 specialist. Twin M accumulated nine accepted developmental episodes and the specialist admitted six supported observations into the derived graph. However, the authoritative Qwen assessment/provenance path classified those observations as current-input echo or otherwise non-independent. The learner therefore ended with ten edge records but zero positive support/accessibility and zero eligible routes. No consolidation transition occurred.

The original v6 graph readout exposed graph edges despite that zero-eligibility learner state. That was a readout-boundary defect, not developmental influence. The original readout artifacts remain unchanged under `MNEME_P2.3_Cross_Thread_v6_Evidence/evaluation/paired-readouts.json`. After commit `0009575`, the same frozen local readout coordinates were rerun for Twin M with the learner-eligibility filter; all 18 corrected M outputs carried no memory notes. The 18 original control outputs were reused unchanged. This corrected pair therefore does not establish a treatment/control test: Twin M had no eligible MNEME influence to compare.

The blinded evaluator was rerun over the corrected pairs. It marked several pairs as possible/clear differences, but the two Gemma readouts were independent unseeded local draws and both treatments were effectively no-memory. Those differences are sampling variation, not evidence of cross-thread MNEME continuity. Stage-2 alignment output is preserved but is not used to claim developmental influence.

## Frozen protocol and evidence

- Thread A: balcony/container gardening under heat and absence.
- Thread B: constrained trip planning with uncertain timing and limited luggage.
- Thread C: remote workshop design with limited equipment.
- B cue: `You have spoken with this person before. In an earlier conversation, you talked about gardening.`
- C cue: `You have spoken with this person before. In earlier conversations, you talked about gardening and planning a trip.`
- Each thread began with a fresh context; no prior transcript was supplied.
- Twin M used local `google/gemma-4-E4B-it` (`UD-Q2_K_XL`, llama.cpp, reasoning off) and GLiNER2.5 `fastino/gliner2.5-base-v1`.
- Twin C used the same local Gemma configuration with no MNEME influence.
- Qwen remained provider-managed through DeepInfra; no seed control was advertised.
- All 36 corrected readouts were non-empty and state digests were unchanged before/after each frozen readout.

The complete sanitized v6 run, including exact readable transcripts, development responses, specialist requests/results, semantic assessments, learner publications, original readouts, corrected readouts, and blinded-evaluation requests/results is in [MNEME_P2.3_Cross_Thread_v6_Evidence](MNEME_P2.3_Cross_Thread_v6_Evidence/).

## Developmental measurement

The v6 developmental ledger reached lineage revision 18, graph revision 5, and nine accepted episodes. Specialist extraction produced variable raw observations; five episodes required Qwen semantic assessment and six supported observations were admitted. The latest learner snapshot contains ten edge states, all with `support=0` and `accessibility=0`, and `routes={}`. Consequently:

- separated independent support: not established;
- consolidation: not executed;
- eligible learned readout routes: none;
- learner credit from the readout correction: none.

This is a measurement result from the corrected pipeline, not a claim that the conversation contained no relationship-bearing language.

## Call accounting

The original v6 execution returned 82 calls: 3 qualification, 9 Qwen participant, 18 local Gemma development, 9 GLiNER extraction, 5 Qwen semantic assessment, 36 local frozen readouts, and 2 Qwen blinded evaluation calls. There were no failed or uncertain calls in that run.

The eligibility-boundary correction used 18 additional local Gemma readout calls and reused the 18 original control outputs. It then used two persisted Qwen evaluation calls. A first attempt to persist the first evaluation result returned successfully but hit a local `TokenUsage` serialization error before writing its receipt; no developmental state changed, the result was not recoverable after process exit, and the fixed evaluation was rerun once. This instrumentation defect is recorded in `evaluation/corrected-blinded-evaluation.json`.

Provider usage for the persisted corrected evaluation was 6,180 total tokens for Stage 1 and 6,313 for Stage 2. Local Gemma and GLiNER token usage was not exposed by their runtimes. No credentials are present in this receipt or evidence tree.

## Historical preservation and scope

The original P2.3 `COMPLETED_INADEQUATE` disposition, all previous supplements, all historical transcripts, and the original v6 readout artifacts remain unchanged. No historical conversation was regenerated. Phase Three did not begin. The work queue remains waiting on the existing Phase Two scientific-review dependency; this exploratory run does not close that dependency.

