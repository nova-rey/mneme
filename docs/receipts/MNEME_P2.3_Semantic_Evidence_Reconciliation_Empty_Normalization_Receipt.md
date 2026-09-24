# MNEME P2.3 Empty-Evidence Normalization Receipt

- Date: 2026-09-24
- Scope: narrow contract normalization after the preserved reviewer Q3 stop
- Provider calls: 0
- Historical evidence: unchanged

## Correction

The reviewer contract continues to require one exact, uniquely resolvable source
quotation when `grounded=true`. For `grounded=false` or `grounded=unknown`, the
validator now accepts omitted evidence and logically empty placeholders (`null`,
`""`, `{}`, or `[]`) and canonicalizes each to the internal value `quote=None`.
Any non-empty string, object, list, or other value remains fail-closed. This does
not change semantic grounding, provenance, or learner admission.

## Validation

Focused reviewer-contract tests cover the historical Q3 shape and all supported
empty forms for false and unknown judgments, plus non-empty rejection and strict
positive grounding. Full pytest, Ruff, strict mypy, package smoke, and CI are
required before the fixed qualification is dispatched.
