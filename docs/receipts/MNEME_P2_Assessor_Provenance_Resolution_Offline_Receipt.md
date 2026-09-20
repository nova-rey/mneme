# MNEME P2 assessor/provenance resolution offline receipt

**Amendment:** `P2-ASSESSOR-PROVENANCE-RESOLUTION-01`  
**Base:** `fe31d6b0fda2f1069250f57cde769528b2fa2a1d`  
**Status:** OFFLINE GATE PASS — NO PROVIDER CALL

This receipt records the additive correction after the separated Qwen Q1
qualification stop. The historical Qwen result remains unchanged. The
semantic assessor no longer supplies developmental dependence labels;
deterministic MNEME software resolves provenance from source roles and runtime
records.

## Contract and implementation

- Assessor schema: `p2-assessor-v2`
- Assessor prompt: `p2-assessor-production-v3`
- Provenance schema: `p2-provenance-v1`
- Shared path: semantic validation → `resolve_provenance()`
  (`validate_and_resolve_assessor_result()`)
- Raw provider result, semantic observations, and provenance resolution are
  retained as separate qualification artifact fields.
- The learner retains all provenance group keys and applies the minimum
  remaining lifetime/induced cap across multiple roots.

The fixed cases now exercise semantic judgments plus deterministic resolution:

- Q1: external latch → `external_supported`; model echo →
  `current_input_echo`; unrelated relation absent/unsupported.
- Q2: rain-jacket direction unsupported; model-output shade corresponds to
  memory source and resolves `exposure_linked`, retaining replay ancestry.
- Q3: negated dial relation unsupported; unavailable output is `unknown`.

## Offline evidence

- Complete pytest: **280 passed**.
- Ruff: **PASS**.
- Strict mypy: **PASS** across 47 source files.
- Focused assessment/qualification/learner regressions: **31 passed**.
- Wheel build, fresh-install CLI smoke: **PASS**.
- CI is required before publication of the commit.
- Provider calls: **0**.
- Historical Gemma/Qwen receipts and the separated assessor binding were not
  rewritten.

This receipt does not claim a live assessor qualification, pilot adequacy,
engineering acceptance, or Phase Two completion. A fresh three-call
qualification authorization is still required.
