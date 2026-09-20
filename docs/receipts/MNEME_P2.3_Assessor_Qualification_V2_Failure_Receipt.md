# MNEME P2.3 assessor qualification v2 failure receipt

**Status:** STOPPED — QUALIFICATION FAILED  
**Date:** 2026-09-20  
**Run:** `qualification-20260920-v2`  
**Qualification contract:** `p2-assessor-production-v2` / `p2-assessor-v1`  
**Implementation commit:** `888cb406cbbaa9b94fcefb9edfdc8f7a70d9a82f`

This was the one fresh, fixed three-call qualification attempt authorized after the prompt-contract remediation. DeepInfra and the existing credential were functional: all three calls returned and were persisted before local validation. The corrected raw-JSON structure passed parsing, but all three cases failed semantic qualification. No repair, transport retry, replacement call, or pilot call was made. The proposed pilot remains at zero calls.

| Case | Provider result | Usage (input/output/total) | Semantic disposition |
|---|---|---:|---|
| Q1 | returned, `stop` | 863 / 296 / 1,159 | rejected: `echo` was marked absent with incomplete coverage even though its required model-output source was available; `unrelated` was marked present |
| Q2 | returned, `stop` | 900 / 210 / 1,110 | rejected: `jacket_direction` was marked present although the external source does not support the candidate relation; `shade` was labeled `replay_linked` despite recorded replay/exposure ancestry requiring the dependence classification to reflect that ancestry |
| Q3 | returned, `stop` | 770 / 203 / 973 | rejected: unavailable model output was marked absent instead of unknown |
| **Total** | **3 returned** | **2,533 / 709 / 3,242** | **qualification failed** |

The validator remained fail-closed. These are semantic assessor errors, not malformed JSON or provider unavailability. The exact persisted provider results remain in the private ignored run artifact at `artifacts/p2-qualification-v2/`; this receipt intentionally records only the minimum sanitized evidence needed for audit.

## Gate consequence

P2.3 does not advance to the pilot. The assessor qualification dependency remains unresolved, the work-queue package remains `WAITING`, and no Phase Two package or release tag is marked complete.
