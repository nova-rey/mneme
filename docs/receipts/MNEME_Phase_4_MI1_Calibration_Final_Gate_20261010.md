# Phase 4 MI1 final calibration gate

**Can our local Gemma use a whole neighborhood supplied through side memory rather than its ordinary prompt? Not established.** The native path demonstrated attention-side access during prefill, but the positive behavioral calibration gate failed; the scored A/B/C study did not run.

After the allowed framing correction, the later frozen visible-bank positive controls scored 2/6 (required 5/6); each of the four latent candidates scored 0/6. Negative controls scored 12/12 and both deterministic replay checks passed. The results do not qualify this task/configuration for the main study.

There is useful context: an earlier, separate visible-text check passed 8/8 on four different, simpler calibration fixtures. That shows Gemma can solve some directed-reachability cases; it does not validate these later positive controls or override their predeclared threshold. In C2, the errors included abbreviating a required path to `A -> B -> C -> D`, claiming a node reachable from an inactive source, and inventing a relationship to reach a second candidate. The failures are task-specific answer/reachability errors, not just the C2 output parser rejecting a valid format.

C1 scored 1/6 on the later visible positives. The uploaded specification allowed a bounded repair after visible-text failure, so C2 used the second and final calibration revision: a generic instruction to trace directed reachability and return explicit `ANSWER` and `PATH` lines. Facts, banks, expected answers, seeds, samplers, variants, exposure levels, thresholds, and scoring criteria were unchanged. The scorer was separately corrected to parse that frozen form and accept its literal `PATH: none if unknown` instruction. Rescoring did not change outputs or the gate conclusion.

## What the evidence establishes

| MI1 question | Current evidence and disposition |
|---|---|
| Does the native Gemma path read side-bank content? | **Mechanically, during prefill:** the attached-bank smoke captured finite attention with mean bank mass 0.516 at the final query. It generated no tokens, so this is not behavioral evidence. |
| Do counterfactual bank contents change answers in the predicted direction? | **Unestablished.** C1/C2 latent calibration outputs were exploratory because the visible positive control failed. No scored paired-bank Test A calls ran. |
| Do connected relationships transfer to held-out tasks? | **Unestablished.** Scored Test A and Test B did not run. |
| Does side memory shape ordinary deliberation? | **Unestablished.** No scored neighborhood-use evaluation ran. |
| Can new banks be added/swapped/cleared affordably? | **Not fully measured.** Calibration encoded banks in four forward passes, but no scored update/removal/reuse suite ran and end-to-end per-neighborhood cost is unknown. |

The native attention-path observation comes from the attached-bank prefill-only smoke: 28 bank slots, finite attention rows, and 0.515775 mean bank attention mass at the final query. No generation occurred. This demonstrates numerical access only, not that Gemma used the bank’s meaning in a response.

## Calibration and accounting

The C2 matrix has 44 complete outcomes. Across the task, 97 generations are charged: 8 earlier visible-text calls, 1 preserved failed parser call, 44 C1 calls, and 44 C2 calls. This remains below the 120-call calibration ceiling and the 800-call campaign ceiling. No scored A/B/C coordinate or untouched confirmation coordinate was run. The same-server and unmodified base-server replays matched reasoning, final answer, and finish reason byte-for-byte.

C2 produced two correct visible answers: a complete Aster-to-Deyu path and a complete Moro-to-Jori path. The incorrect answers described above were genuine failures against the frozen reachability rules. Every latent candidate scored 0/6, but those results cannot establish a side-memory semantic failure because the visible positive-control gate did not qualify.

## Disposition

**Calibration gate failed; MI1 associative efficacy is not established.** This is not evidence that Memory Inception is ineffective in general, nor a complete behavioral qualification of this Gemma implementation. The safe next step is one specifically bounded task/calibration redesign followed by a fresh gate; the current plan has exhausted its two revisions, so no further model calls are authorized by this run. No SAA, learner, introspection, CompactStore, ON-30, production runtime, or developmental state was changed.

The [machine-readable receipt](MNEME_Phase_4_MI1_Calibration_Final_Gate_20261010.json) contains coordinate scores, hashes, counts, runtime fingerprints, local evidence paths, and these scope dispositions. Full reasoning and raw streams remain outside Git at `/home/nyx/mneme-artifacts/phase4-mi1/calibration-run/`.
