# MNEME P2.3 assessor qualification v3 failure receipt

**Status:** STOPPED — QUALIFICATION FAILED  
**Date:** 2026-09-20  
**Run:** `qualification-20260920-v3`  
**Interface:** `p2-assessor-production-v2` / `p2-assessor-v1`  
**Main:** `905622f4c439a44f4be951ea157f599a8a34ecdf`

This was the explicitly authorized fresh fixed qualification using the frozen Q1/Q2/Q3 coordinates. All three DeepInfra calls returned and were durably persisted before validation. No retry, repair, replacement sample, or pilot call was made.

| Case | Sanitized returned evidence | Required result | Failure |
|---|---|---|---|
| Q1 | `unrelated`: `present`, `supported`, quotation `Pulling the lever released the latch.` | `unrelated` must be `absent`/`unsupported` with complete coverage. | Model falsely generalized the latch statement to the unrelated monitor. |
| Q2 | `jacket_direction`: `present`, `supported`, quotation `The rain jacket kept my shoulders dry.` | Rain-jacket source must be `absent`/`unsupported` for the `rain_jacket → shade` candidate. | Model treated an unrelated rain-jacket fact as support for the candidate relation. `shade` was returned as `replay_linked`; the case requires `exposure_linked`. |
| Q3 | `dial`: `present`, `supported` despite quotation `Turning the dial did not stop the ticking; the sound continued.`; `unavailable_output`: `absent` with complete coverage. | Negated dial relation must be unsupported; unavailable source must be `unknown`. | Model misclassified negation and unavailable coverage. Validator correctly rejected the false absence. |

Usage was 2,866 input, 706 output, and 3,572 total tokens. Provider cost was not supplied. The credential and provider were functional. The proposed 299-call pilot remains at zero calls and is not started.

This result is preserved as new evidence; earlier qualification receipts remain unchanged. The repeated semantic failures indicate that the selected host has not demonstrated suitability for this assessor role. Further prompt engineering or resampling is not automatic and requires architectural review/new authorization.
