# Phase 4 MI1 final calibration gate

**The final calibration gate failed, so scored Test A/B/C did not run.** After the allowed framing correction, the visible-bank positive controls scored 2/6 (required 5/6); each of the four latent candidates scored 0/6. Negative controls scored 12/12 and both deterministic replay checks passed. The results do not qualify the host/task for the main study.

The C1 calibration matrix had failed visible comprehension at 1/6. The uploaded specification explicitly allowed a bounded repair when visible-text comprehension fails, so C2 used the second and final calibration revision: a generic instruction to trace directed reachability and return an explicit `ANSWER` and `PATH`. Tasks, facts, bank sources, answers, seeds, samplers, bank variants, exposure levels, thresholds, and scoring criteria were not changed. All C1 outcomes remain preserved.

The scorer was updated to parse the C2 answer format and accept `PATH: none if unknown`, which follows the literal frozen prompt wording. Rescoring did not alter the gate conclusion. C2 produced two correct visible answers: one complete Aster-to-Deyu path and one complete Moro-to-Jori path. Errors included abbreviating the Aster path to `A -> B -> C -> D`, claiming Keme was reachable from an inactive Tazu, and inventing a Garo-to-Rudo edge to reach Tena. These are failures of the visible positive control, so the latent results cannot support a conclusion about MI1 efficacy. The latent candidates had 0/6 fully correct outputs each. We do not interpret this as proof that attention-side memory cannot work.

## Accounting and apparatus

The C2 matrix has 44 complete outcomes. Across the task, 97 generations are charged: 8 prior visible-text calls, 1 preserved failed parser call, 44 C1 calls, and 44 C2 calls. This remains below the 120 calibration ceiling and the 800-call campaign ceiling. No scored A/B/C coordinate or untouched confirmation coordinate was run. The native Gemma server and SSH tunnel have been stopped.

The same-server replay and the unmodified base-server replay matched the primary no-bank response byte-for-byte in reasoning, final answer, and finish reason. Thus determinism and the native no-op replay passed; these checks do not repair the failed visible-comprehension gate.

## Conclusion and evidence

The apparatus was able to encode and attach latent banks, but the frozen positive-control task did not reach its required visible-text reliability after the two authorized revisions. The experiment therefore cannot distinguish a side-memory semantic limitation from insufficient task/model comprehension. The defensible disposition is **calibration gate failed; MI1 associative efficacy not established**. A further attempt would require an owner-authorized new calibration design; do not extend this run or relax its threshold.

The [machine-readable final-gate receipt](MNEME_Phase_4_MI1_Calibration_Final_Gate_20261010.json) contains all 44 C2 coordinate scores, request/result hashes, concise output excerpts, counts, and local evidence references. Full reasoning and raw streams remain outside Git at `/home/nyx/mneme-artifacts/phase4-mi1/calibration-run/`.
