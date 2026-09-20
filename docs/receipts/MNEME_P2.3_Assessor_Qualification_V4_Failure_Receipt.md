# MNEME P2.3 assessor qualification v4 failure receipt

**Status:** STOPPED — QUALIFICATION FAILED  
**Date:** 2026-09-20  
**Run:** `qualification-20260920-v4`  
**Implementation:** `3386d94561e15f877e5b621013f2d3365d7fe4ea`  
**Interface:** `p2-assessor-production-v2` / `p2-assessor-v1`

This was the explicitly authorized fresh attempt against the frozen Q1, Q2,
and Q3 coordinates. All three DeepInfra calls returned and were durably
persisted before validation. There were no retries, repairs, replacement
samples, or pilot calls. The complete sanitized run inventory remains under
the ignored local artifact root:
`artifacts/p2-qualification-v4/experiments/p2-developmental-pilot/revisions/1/runs/qualification-20260920-v4/`.

| Call | Provider result | Required semantic result | Exact validation failure | Usage |
|---|---|---|---|---:|
| Q1 | Returned JSON marked `unrelated` as `present`/`supported`, quoting `Pulling the lever released the latch.` | `unrelated` must be `absent`/`unsupported` with complete coverage. | `Q1 monitor unrelated has wrong status: expected 'absent', got 'present'` | 974 input / 297 output / 1,271 total |
| Q2 | Returned JSON marked `jacket_direction` as `present`/`supported`, quoting `The rain jacket kept my shoulders dry.`; marked `shade` `replay_linked`. | Rain-jacket direction must be absent/unsupported; shade must satisfy the required exposure classification. | `Q2 monitor jacket_direction has wrong status: expected 'absent', got 'present'` | 1,011 input / 208 output / 1,219 total |
| Q3 | Returned JSON marked the negated `dial` relation `present`/`supported`, quoting `Turning the dial did not stop the ticking; the sound continued.`; marked unavailable output `absent`. | Negated dial relation must be unsupported; unavailable source coverage must be `unknown`, never absent. | `monitor unavailable_output absent requires complete available-source coverage` | 881 input / 201 output / 1,082 total |

Total usage was **2,866 input**, **706 output**, and **3,572 total** tokens;
provider cost was not supplied. The credential and DeepInfra transport were
functional. This is a semantic qualification failure, not a provider-
availability failure. P2.3 remains stopped and the pilot remains at zero
calls. Further prompt engineering or resampling requires separate
architectural review and authorization.

