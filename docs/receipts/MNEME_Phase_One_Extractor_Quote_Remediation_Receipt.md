# MNEME Phase One extractor quotation remediation receipt

Date: 2026-09-19
Status: OFFLINE_REMEDIATION_VALIDATED

This receipt records the offline correction made after the fresh P1.1 live
attempt showed that requiring Gemma to calculate Unicode offsets was an
unnecessary interface burden. No DeepInfra call was made for this correction.

## Contract

The model-facing extractor contract now requires each graph-bearing record to
provide an `evidence` array. Each array item is exactly:

```json
{"source":"s0","evidence":"short exact quotation copied verbatim from the source"}
```

The prompt includes the complete validator-owned concept-kind and
relationship-kind vocabularies, the allowed top-level fields, the required
record shape, and raw-JSON-only/no-fences/no-prose/no-invented-enums rules.
The prompt explicitly forbids model-supplied `source_spans`, `start`, and
`end` arithmetic.

The validator resolves every quotation against the immutable request-local
source slot using exact Python string matching. It rejects missing slots,
empty or nonexistent quotations, paraphrases, and ambiguous repeated or
overlapping occurrences. It stores only the canonical half-open Unicode
code-point span (`source_slot`, `start`, `end`) in the validated residue.
Distinct quotations are allowed when each resolves uniquely. No fuzzy matching,
normalization, or first-match guessing is used.

At the provider-result boundary, graph-bearing records that provide numeric
`source_spans` without quotation evidence are rejected. Numeric spans remain
available to internal callers that construct or revalidate canonical residues.

Raw provider results remain durably retained in the interpretation attempt for
audit; no database schema change was required.

## Offline evidence

- Added adversarial coverage for ASCII, Unicode, emoji/multicode-point text,
  curly punctuation, source boundaries, missing/empty/paraphrased quotations,
  wrong source slots, ambiguous repetitions, multiple unique quotations,
  deterministic resolution, and one-repair recovery.
- Preserved regression coverage for fenced JSON, pseudo-JSON, unsupported
  `memory_type`, `definition`, `TERM`, and `processed by` outputs.
- The existing internal numeric-span fixtures remain covered as canonical
  representation tests.
- No Phase Two mechanism was introduced.

Validation was run before any new live authorization:

```text
pytest -q: 209 passed
ruff check: passed
mypy --strict: passed
```

Fresh-install/package smoke and CI are recorded with the remediation commit.
The historical live failure receipt remains unchanged. P1.2 and P1.3 were not
started, and no DeepInfra calls were made.
