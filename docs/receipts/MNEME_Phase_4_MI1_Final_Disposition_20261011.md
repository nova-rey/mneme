# MNEME Phase 4 MI1 final disposition

**Memory Inception on our Gemma does not work well enough to advance.** Across the completed retrieval, process-prior, lifecycle, and all-head tests, the bank was repeatedly present in the runtime and sometimes affected computation, but structured bank content did not produce reliable, attributable behavior. No MNEME integration is recommended.

This is a negative result for the tested Gemma 4 E4B-it Q2/llama.cpp MI1 implementation and these bank constructions. It is not a claim that every Memory Inception implementation or host must fail.

## What the evidence establishes

The earlier 8/8 result was a **visible-text positive control** on short fixtures. It established that Gemma could follow the rules when the facts appeared in its ordinary prompt. It was not an 8/8 hidden-bank result. Across the investigations, visible controls generally worked while hidden-bank controls failed; no-bank controls correctly returned `unknown`. That pattern localizes the practical failure to using the bank as semantic memory, rather than to a generally unusable task or model.

The clearest controlled retrieval results are:

| Test | Hidden-bank result | Controls and implication |
|---|---:|---|
| C14, selected-site atomic recall | 0/32 across both polarities and 2x/4x bank strength | no-bank and cue-only 8/8 `unknown`; visible facts 8/8 each. Selected query heads assigned substantial prefill attention to the bank, but reasoning still said no internal record was available. |
| C16, assistant-turn bank | 0/16 (0/8 per polarity) | no-bank/cue 8/8; visible A/B 7/8 and 8/8. The latent reasoning explicitly treated the note as unavailable. |
| Test A, frozen 24-fixture retrieval | latent A 0/24; latent B 0/24 | no-bank and irrelevant-bank 23/24 unknown; visible A 19/24 and B 15/24. |
| C17, all-head/all-layer diagnostic | latent A 1/8; latent B 0/8 | no-bank 8/8; visible A 7/8 and B 8/8. The sole latent exact label had no reasoning trace; the other latent outputs were malformed, unrelated, or incomplete. The unchanged gate failed, so its 40 held-out calls did not run. |

C17 directly tested whether sparse routing alone explained the failures: the same assistant-turn banks were exposed across all 42 query layers and 8 heads, with all 24 KV source layers and the previously tested 4x prior. That did not recover meaningful access. Reasoning text was absent for all 16 latent outputs; one A output happened to equal the expected label, but without reasoning and amid outputs such as “The stored in the canvas.” and repeated “S-filter” fragments, this is not evidence of semantic retrieval. Broad exposure was disruptive.

Test B applied relation/process packs to nine open-ended tasks, with 108 complete outputs across no-bank, visible-pack, text-C, latent-correct, latent-irrelevant, and altered-topology conditions. It did not establish a repeatable hidden-bank effect distinguishable from task-native advice. For example, a latent resilience answer used “defense-in-depth,” but the matched no-bank reasoning already developed backups, redundancy, and standard procedures; the latent trace did not identify or evaluate a hidden association. In other tasks, ordinary scheduling or staged-change advice was already invited by the task. Visible packs made the intended principles explicit. These are ambiguous output differences, not proof that latent packs transferred their structure.

## A/B/C and removal/reuse

The frozen Test A/B/C suite completed all 268 coordinates: 144 A, 108 B, and 16 C. Every coordinate has a durable request/result record. Test A's exact answer scores are above. Test B remains descriptive rather than a validated semantic score. In Test C, all 16 outputs were `unknown` across fresh bank A, replacement bank B, disabled, restored A, ongoing-turn, and new-bank coordinates. The server did attach, replace, disable, and restore banks with the expected fingerprints/revisions; however, because no bank condition first produced a behavioral retrieval effect, removal and restoration could not demonstrate removal and return of that effect. Physical replacement works; scored behavioral reuse does not.

The earlier 8/8 visible positive controls and later visible A/B results show Gemma can use the material when it is in the prompt. They do not show that the side bank made it available. Held-out confirmation was not run for C14, C16, or C17 because each frozen calibration gate failed. That was the specified fail-closed design, not missing evidence.

## What failed technically

**Observed:** bank files and fingerprints matched the intended sources; attach/replace/clear operations changed server state as requested; prefill attention reached appended bank slots; earlier instrumentation observed downstream hidden-state changes. C14 measured mean bank attention mass of 0.498 over selected heads at its final prefill query (range 0.055–0.970), versus 0.0237 averaged over all heads. Thus “the bank never reached computation” is not supported.

**Observed:** this computational access did not yield dependable semantic readout. Exact facts were not recovered in C14/C16/Test A, and open-ended Test B did not separate hidden-bank influence from advice already implied by the task. Making access global in C17 suppressed all latent reasoning traces and damaged answer formation.

**Unresolved:** the evidence does not isolate whether the readout gap comes from Gemma-specific K/V and attention semantics, sliding-window/shared-KV behavior, the custom llama.cpp port, Q2 quantization, the bank representation, or Gemma's learned inability to treat appended K/V as usable memory. The implementation uses an augmented attention path rather than Gemma's ordinary rolling KV cache; it maps shared-KV query layers to their source layers and masks the bank for final prefill/decode queries. That is an implementation description, not proof that every semantic detail matches the paper's intended behavior. Attention probability and hidden-state change alone cannot establish successful memory use.

The broad all-head result argues against further strength/routing expansion as a sensible calibration path: it trades absent/weak semantic access for malformed, reasoning-free outputs. The present evidence supports rejecting this exact MI1 path for MNEME, while leaving a different Gemma-aware implementation as a separately justified research question rather than an implied next step.

## Cost, resources, and evidence

On the RTX 3060 Laptop GPU (6 GiB), the 268-call Test A/B/C suite accumulated 5,217.55 seconds of request latency (median 14.93 s, p90 34.83 s, maximum 42.91 s). C17 added 40 calibration calls. Its SSE timing fields sum to 5.1 s prompt processing and 142.3 s generation across calls; those sums are server token timings, not end-to-end wall time. The 40-call C17 calibration and its complete request/result/stream records are durable outside Git.

For 38 recorded Test A/B/C bank-source builds, K/V encoding averaged 1.457 s per source (55.38 s summed); pack/configure averaged 0.031 s per source (1.19 s summed). A typical selected-site variant was about 9.23 MB; the 16 C17 all-head variants totaled 31.09 MB. The exact source/capture/variant hashes and the bank-build metrics are retained outside Git. This construction cost is manageable; the blocking issue is behavioral reliability, not storage or build time. A separate attach-time benchmark was not recorded, so no numerical claim is made for attach latency.

The latest recorded MSI thermal check during C17 was 59 °C with no sustained GPU load after a batch; the resident server health endpoint remains OK. I cleared the final active bank and verified `/mi1/bank` reports `enabled=false`, empty fingerprint, revision 171. No MNEME instance, developmental state, SAA state, or learner was loaded or changed.

Compact evidence and canonical external evidence:

- Frozen C17 plan: [C17 calibration freeze](MNEME_Phase_4_MI1_C17_All_Head_Calibration_Freeze_20261011.json), SHA-256 `3b8140de20b055d986d08e87837de185ce6c11360feda9319d6ef0f0b95c88bb`.
- C17 execution binding: [C17 execution freeze](MNEME_Phase_4_MI1_C17_Execution_Freeze_20261011.json), SHA-256 `34eff55abb99bc78352be4dd70d4cce8ce245452b0998223f855fd8e488a6ef0`.
- C14 and C16 compact readouts: [C14](MNEME_Phase_4_MI1_C14_Calibration_Readout_20261011.md) and [C16](MNEME_Phase_4_MI1_C16_Calibration_Readout_20261011.md).
- Test A/B/C schedule: [frozen Test A/B/C plan](MNEME_Phase_4_MI1_Test_ABC_Freeze_20261010.json), with 268/268 complete receipts indexed at `/home/nyx/mneme-artifacts/phase4-mi1/test-abc/evidence/index.json` (SHA-256 `bf2968b9bd8ae26b533a32c4c1feb5c49f21898ab6866ea6ded93f289beb33db`).
- Canonical C17 score: `/home/nyx/mneme-artifacts/phase4-mi1/c17-allhead/score-calibration.json` (SHA-256 `6c3b325485c072b8cc0c3e6f237195cf973989c3a1b870b1f3b80c006de99697`); complete evidence index SHA-256 `3d2acd955402319042fb73780f2aa1a34a8bd90ee3fce179956cd546e1c19037`.
- Test A v3 score: `/home/nyx/mneme-artifacts/phase4-mi1/test-abc/test-a-score-v3.json` (SHA-256 `96a933b27dfe8e74906b6a6fe1c6d23a2df3676589683516408ca0fd81232da1`).

## Recommendation

Do not integrate this Memory Inception implementation into MNEME. The tested mechanism can route and perturb computation, but it has not shown that structured associative content is reliably available to Gemma or produces attributable behavioral effects. A different attention/KV implementation would need a fresh, frozen qualification and held-out confirmation before reconsideration; this result does not authorize such integration or claim that the general research idea is impossible.
