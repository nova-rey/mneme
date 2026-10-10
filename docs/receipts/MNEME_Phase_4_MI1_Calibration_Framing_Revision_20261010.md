# MI1 calibration framing revision 2

This is the second and final permitted calibration revision under the uploaded MI1 specification. Revision C1's visible-bank positive control scored 1/6, so its latent-condition outcomes are exploratory and do not establish failure of the attention-side memory mechanism. The task specification explicitly requires repairing ordinary visible comprehension before interpreting latent-bank results.

Revision C2 changes only the generic system instruction. It explains directed reachability from active starting labels and requires a two-line final answer containing both the reachable label and complete path. The recipient prompts, visible and latent bank text, expected answers/paths, seeds, sampler, output limit, prompt-cache policy, bank encodings, site selectors, gains, scoring rubric, and thresholds remain unchanged. Every call has a fresh `C2-` ID; C1 remains immutable.

The 44 requests were frozen before C2 inference in [the machine-readable plan](MNEME_Phase_4_MI1_Calibration_Framing_Revision_20261010.json). It shares the already-built bank variants from the original frozen plan because the bank sources and configurations are unchanged. The added matrix brings calibration accounting to 97 calls (8 prior + 1 failed mechanical call + 44 C1 + 44 C2), below the 120 calibration cap. If C2 passes the gate, the remaining frozen study plus confirmation reserve projects to 413 total calls, below the 800 cap.

The pass criteria are unchanged: visible-bank at least 5/6; negative controls at least 11/12; exact same-server and base-server replay; and at least one latent candidate at 5/6 with no more than one negative false positive. Scored Test A/B/C must remain unlaunched unless all required gates pass.
