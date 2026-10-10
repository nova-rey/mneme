# Phase 4 MI1 calibration outcome

**Disposition: calibration gate failed; scored Test A/B/C was not run.** The predeclared gate required at least 5/6 correct visible-bank checks, at least 11/12 correct negative checks, byte-identical same-server and base-server replays, and a passing latent candidate. The observed results were 1/6, 12/12, both replay checks passing, and 0/6 for every latent candidate. The fail-closed rule therefore stopped the experiment before the 268 scored coordinates.

The model/runtime was operational and deterministic under the frozen settings. The failure was behavioral qualification: Gemma did not reliably return the required complete reachability answer even when the relevant fictional relationships were supplied visibly. Sparse latent-bank conditions did not recover the positive checks. Broad-bank conditions sometimes produced long repetitive or incomplete final answers. These results do not support proceeding to the MI1 A/B/C study under the frozen acceptance criteria.

## What ran

The corrected, frozen 44-coordinate calibration matrix completed: three fictional directed-reachability tasks, two seeds, visible/no-bank/irrelevant controls, and four latent exposure configurations, plus two no-bank replay coordinates. The earlier eight visible-text calibration calls remain part of the historical record. One earlier base-server attempt failed mechanically because the SSE parser mishandled an initial null content delta; it is retained as failed, not scored or retried under its original identifier. The corrected 44-call matrix used new IDs and the parser fix.

The durable journal verifies 44 complete corrected outcomes and one preserved failed attempt. Calibration accounting is 8 prior + 1 failed + 44 corrected = 53 calls, below the 120 calibration ceiling. No scored A/B/C generation ran; the 48-call confirmation reserve remains untouched. The authorized 800-call hard ceiling was not approached.

## Gate results

| Check | Result | Frozen threshold |
|---|---:|---:|
| Visible-bank complete answers | 1/6 | at least 5/6 |
| No-bank and irrelevant-bank controls | 12/12 correctly answered `unknown` | at least 11/12 |
| Sparse latent candidates | 0/6 for low, moderate, and strong | at least 5/6 for a candidate |
| Broad latent candidate | 0/6 | at least 5/6 |
| Same-server duplicate | byte-identical | required |
| Base-server duplicate | byte-identical | required |

One visible-bank example illustrates the scoring boundary: for the frozen path `Aster → Beryl → Corda → Deyu`, the final answer was only `Deyu`; the reasoning contained the path, but the frozen final-answer rubric requires the answer and full path in the visible response. This is counted as incorrect under the pre-generation rule. Other visible-bank outputs omitted a path or asserted an unreachable label. No rubric was changed after seeing outputs.

The `unknown` negative controls all passed, so the result is not a general inability to use the task format. It is specifically a failure to demonstrate reliable positive reachability from the supplied bank under the frozen output contract. The latent candidates produced no qualifying positive answers; broad exposure also showed repetitive/incomplete final-answer behavior. We make no claim about performance on the unrun A/B/C tasks.

## Reproducibility and evidence

The pinned Gemma Q2 GGUF, llama.cpp commit/build, reasoning-ON configuration, sampler, prompt-cache-disabled requests, and exact coordinate manifests are recorded in the machine-readable result. The corrected same-server and clean base-server duplicate each matched the primary replay in reasoning text, final answer, and finish reason. The calibration scorer was corrected to read replay identifiers from the committed correction amendment; rescoring confirms determinism passes. The amendment does not change prompts, banks, seeds, thresholds, or outcomes.

Compact coordinate-level scores and response hashes are in [the JSON outcome](MNEME_Phase_4_MI1_Memory_Inception_Calibration_Outcome_20261010.json). Full request/result streams and complete reasoning remain in the local canonical evidence directory at `/home/nyx/mneme-artifacts/phase4-mi1/calibration-run/`; the JSON records the index, plan, and score hashes. No MNEME instance, developmental state, SAA, or learner state was loaded or modified.

The MI1 calibration gate is complete with a negative result. The larger scored study is not complete and must not be represented as having run. Any change to the task or acceptance criteria would require a separately authorized prospective calibration; this result is preserved as-is.
