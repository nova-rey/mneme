# MNEME P2.3 Semantic Evidence Reconciliation — Offline Correction Receipt

- **Date:** 2026-09-24
- **Status:** OFFLINE PASS; bounded reviewer qualification pending
- **Scope:** additive P2.3 acquisition-stage correction
- **Provider calls:** 0
- **Historical evidence:** unchanged, including the 120 returned pilot/continuation calls and all failed extraction operations

## Correction

Exact immutable-source quotation validation remains the normal fast path. When an
otherwise structurally valid extraction fails only because a proposed quotation
is missing or ambiguous in its bound source, the pilot may invoke the temporary
`experimental semantic evidence reconciliation` role. The reviewer receives the
immutable source, source role, extracted proposition, and proposed quotation.
It may return only `{grounded: true, evidence: "..."}`, `{grounded: false}`, or
`{grounded: "unknown"}`. It does not calculate offsets, provenance, learner
credit, or developmental consequences.

MNEME accepts a positive review only when the returned quotation is nonempty,
verbatim, and unique in the immutable source. Python then computes and validates
the canonical Unicode span. False, unknown, malformed, missing, and duplicate
quotations fail closed. The original failed extraction operation remains
immutable; a separate versioned recovery operation records the reconciled
payload and is passed through the existing validation/publication boundary.

The selected bounded verification candidate is `Qwen/Qwen2.5-7B-Instruct`
through DeepInfra, recorded as a non-developing evidence-reviewer binding. It
has not been called by this correction.

## Offline evidence

- Focused reconciliation and provenance-preservation tests: 17 passed.
- Complete pytest suite: 333 passed.
- Ruff: passed.
- Strict mypy: passed (`51 source files`).
- Wheel/fresh-install smoke: passed (`mneme --help` from the built wheel).
- Historical extraction, assessor, pilot, and budget receipts were not rewritten.

## Boundary

This is temporary research scaffolding, not a new developmental component or
semantic learner. Only exact-quote failures can enter it; no fuzzy matching,
normalization, edit distance, Markdown parser, embeddings, recursive repair, or
new learner rule is introduced. A four-case fixed qualification (formatting
omission, source-grounded paraphrase, unsupported extraction, and negation) is
required before resuming the preserved P2.3 coordinate.
