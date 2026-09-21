# MNEME P2.3 assessor qualification — coverage/polarity v9 pass

**Status:** LIVE QUALIFICATION PASS — Q1/Q2/Q3 passed; pilot boundary remains separate  \
**Run:** `qualification-v9b`  \
**Validated commit:** `41bd31f3633c5ab97c8b9074250e94ba48834ee9`  \
**Contract:** `p2-assessor-v6` / `p2-assessor-production-v8` / `p2-provenance-v1`  \
**Assessor:** DeepInfra `Qwen/Qwen3-235B-A22B-Instruct-2507`

This was one fixed three-call campaign after the offline coverage/polarity correction.
Each provider result was durably persisted before validation. No retry, repair,
replacement sample, resampling, or model substitution occurred. The previous
v5/v7 receipts remain historical and unchanged.

## Accounting

| Case | Result | Usage (input/output/total) | Disposition |
|---|---|---:|---|
| Q1 | passed | 1,305 / 336 / 1,641 | latch and current-input echo resolved correctly |
| Q2 | passed | 1,290 / 247 / 1,537 | memory-linked output resolved correctly |
| Q3 | passed | 1,189 / 218 / 1,407 | explicit negation and unavailable coverage resolved correctly |
| **Total** | **3 passed** | **3,784 / 801 / 4,585** | **qualification passed; pilot calls 0** |

Provider cost was not supplied. DeepInfra and the designated Qwen host binding were functional.

## Gate assertions

- Q1: latch `present/supported/affirmed`; echo `present/supported/affirmed` with `current_input_echo`; unrelated `absent/unsupported/not_expressed`.
- Q2: jacket direction `absent/unsupported/not_expressed`; shade `present/supported/affirmed` with deterministic `exposure_linked` provenance.
- Q3: dial `present/contradicted/negated` with exact quote `did not stop the ticking`; unavailable output `unknown/unknown/unknown`.
- All monitor propositions were complete and required source coverage rules passed.
- Host fingerprints matched the prepared assessor binding.
- Artifact integrity, exact-once call accounting, and qualification state were audited after completion.

The complete sanitized serialized requests, provider results, validated semantic
observations, and deterministic provenance records are preserved in the
accompanying JSON receipt. No pilot call was made by this qualification.
