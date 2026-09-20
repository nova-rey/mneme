# MNEME P2.3 separated-assessor qualification failure receipt

**Status:** STOPPED — QUALIFICATION FAILED  
**Run:** `qualification-20260920-qwen-v1`  
**Main/configuration:** `a3a8ee6025e9ce76deb1d310aad78c55bb9e0bc1`  
**Role configuration:** `p2-assessor-separation-01`  
**Interface:** `p2-assessor-production-v2` / `p2-assessor-v1`

This was the one explicitly authorized replacement qualification using the
designated Qwen assessor. Q1 was dispatched and its request/result were
durably persisted before validation. Qwen returned structurally valid JSON,
but the first semantic case failed, so execution stopped immediately. Q2 and
Q3 were not dispatched. No retry, repair, replacement sample, model switch,
or pilot call occurred.

| Case | Disposition | Sanitized returned classification | Required result | Failure |
|---|---|---|---|---|
| Q1 | returned, rejected | `latch`: `present`/`supported`, exact quote `Pulling the lever released the latch.`, dependence `replay_linked`; `echo`: `current_input_echo`; `unrelated`: `absent`/`unsupported` | `latch` must be `external_supported`; echo and unrelated assertions remain as frozen | `Q1 monitor latch has wrong dependence: expected 'external_supported', got 'replay_linked'` |
| Q2 | not dispatched | — | Frozen Q2 case | Stopped after Q1 failure |
| Q3 | not dispatched | — | Frozen Q3 case | Stopped after Q1 failure |

## Host and accounting evidence

The provider returned successfully, proving the credential, endpoint, and
designated Qwen transport were functional. The assessor fingerprint was:

- Provider: DeepInfra standard tier
- Model: `Qwen/Qwen3-235B-A22B-Instruct-2507`
- Family: Qwen3 235B A22B Instruct 2507
- Catalog observation: fp8, 262,144 context, standard rates observed
  2026-09-20 at USD 0.09/M input and USD 0.55/M output
- Served revision and tokenizer identity: unknown
- Fingerprint digest: `ed86eefcec7b2d512ce93e0551f18e8e95bb9f9e283142b1e107a571c566daa4`

Q1 usage was **848 input**, **371 output**, and **1,219 total** tokens;
provider cost was not supplied. The developing Gemma binding remained
`google/gemma-4-E4B-it` and was not called. The pilot remains at zero calls.

The complete sanitized Q1 request/result, role binding, reservation, and
terminal state remain in the ignored local run inventory under
`artifacts/p2-qualification-qwen-v1/experiments/p2-developmental-pilot/revisions/2/runs/qualification-20260920-qwen-v1/`.

This is a semantic assessor-suitability failure, not a credential or
transport failure. The amendment forbids automatic prompt engineering,
resampling, model substitution, or another qualification campaign. P2.3
therefore remains blocked pending architectural review.

