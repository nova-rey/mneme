# MNEME P2.3 Semantic Evidence Review Qualification V3 Failure

- Date: 2026-09-24
- Contract: `semantic-evidence-reconciliation-v2` with empty-evidence normalization
- Designated reviewer: Qwen/Qwen2.5-7B-Instruct via DeepInfra
- New provider calls: 2
- Pilot calls: 0
- Historical evidence: unchanged
- Result: stopped at Q2; Q3 was not dispatched

## Fixed schedule and disposition

| Case | Result | Disposition |
| --- | --- | --- |
| Q1 Markdown formatting | `grounded=true` with the exact formatted source quotation | passed |
| Q2 grounded paraphrase | provider returned an empty response with `finish_reason=length`; strict JSON validation failed | failed closed |
| Q3 unsupported | not dispatched after Q2 failure | unused |

Q1 consumed 214 input, 290 output, and 504 total tokens. Q2 consumed 212
input, 384 output, and 596 total tokens. Cost was not supplied. The Q2 result
was persisted before validation exactly as returned; no retry, repair, resampling,
or alternate model was used. The empty-evidence normalization was therefore not
reached for Q2, and no pilot call was authorized or made.

The complete request/result records remain in the private qualification artifact
root `/tmp/mneme-p23-semantic-evidence-review-qualification-v3-20260924` and are
referenced by the machine-readable receipt. The provider and credential were
functional for both dispatched calls; Q2 was a model-output/length failure, not a
transport or credential failure.
