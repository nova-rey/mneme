# MNEME P2 assessor role-separation offline receipt

**Amendment:** `P2-ASSESSOR-SEPARATION-01`  
**Starting main:** `f8c72277a0915d2af14f1d37819e4e8fe251f03f`  
**Status:** OFFLINE GATE PASS — NO PROVIDER CALL

This receipt records the bounded correction before the newly authorized
qualification. The developing conversational host remains DeepInfra
`google/gemma-4-E4B-it`. Semantic assessment now accepts an explicit assessor
host binding through the existing `Host` protocol; the qualification executor
uses that same binding and retains the same request builder, schema, validator,
source masks, and frozen Q1/Q2/Q3 cases.

## Role and fingerprint correction

The designated assessor is DeepInfra standard-tier
`Qwen/Qwen3-235B-A22B-Instruct-2507` at the existing OpenAI-compatible
`/v1/openai/chat/completions` endpoint. The provider catalog observed on
2026-09-20 reports standard pricing of USD 0.09 per million input tokens and
USD 0.55 per million output tokens, fp8 serving, and 262,144 context. The
served revision and tokenizer identity remain unknown. The Qwen fingerprint
contains no Gemma family, Gemma tokenizer, or Gemma canonical revision.

`DeepInfraGemmaHost` remains the existing developing binding. The new
`DeepInfraQwenAssessorHost` shares only the transport implementation and has
separate model-family, upstream, tokenizer, quantization, context, and
fingerprint metadata. No model call was made to verify availability.

## Durable role binding

Mixed-role pilot/qualification envelopes require both `developing` and
`assessor` bindings. The binding stores the role, complete host fingerprint,
fingerprint digest, provider, and model ID. Qualification fails before dispatch
when the assessor binding is missing or the supplied host fingerprint differs.
Each dispatched assessor reservation records its expected host fingerprint;
the returned result records the actual fingerprint and is rejected if they
differ. Qualification artifacts retain the binding and sanitized result
provenance. Existing single-host test fixtures remain explicitly legacy and
are not used as mixed-role acceptance evidence.

Known qualification failures stop immediately after the failed returned case;
there are no automatic retries or replacement calls. Results are persisted
before structural or semantic validation. A failed or incomplete qualification
cannot release pilot execution.

The secret scrubber was narrowed so fields such as `tokenizer_id` remain
truthful provenance while actual secret fields continue to be redacted.

## Offline evidence

- Complete pytest: **275 passed**.
- Focused host/pilot/qualification tests: **24 passed** before the final
  request-contract regression; the complete run includes that regression.
- Ruff: **PASS**.
- Strict mypy (`src/mneme`, 47 files): **PASS**.
- Wheel build: **PASS** (`pip wheel . --no-deps`).
- Provider calls: **0**.
- Historical receipts and the existing P2.3 `WAITING` state were preserved.

The new tests cover truthful Qwen fingerprint metadata, complete frozen
qualification proposition/source-role serialization, role mismatch and missing
assessor rejection, expected-versus-actual returned host binding, immediate
stop after a failed case, durable result-before-validation, and legacy
single-host compatibility. This receipt does not claim assessor qualification,
pilot adequacy, or Phase Two completion.
