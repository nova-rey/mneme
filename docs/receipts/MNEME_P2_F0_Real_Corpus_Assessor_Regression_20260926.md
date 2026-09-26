# F0 real-corpus assessor regression and qualification

Date: 2026-09-26  
Status: **REAL_CORPUS_SUPPORTED_AND_FALSE_SUPPORT_GATES_PASS**

This receipt preserves all 25 forwarded GLiNER candidates from the immutable F0 run. Each row retains the raw candidate, exact source slot and evidence text, immutable source text, historical local-DeBERTa output, historical downstream disposition, reviewed expectation, and the repaired adapter output. Historical F0 artifacts and dispositions are unchanged.

## Diagnosis and repair

The v1 adapter scanned every covered source slot for uncertainty/intent and selected broad mixed conversation windows. Unrelated `planning`, `would`, or `try` language therefore poisoned clear propositions. Raw GLiNER labels such as `usage* profile` were passed through as malformed hypotheses, relation hypotheses were bare token sequences, and cue coverage did not include ordinary forms such as `holds` and `depends on`.

The v2 adapter keeps the local DeBERTa model and adds deterministic proposition-only Markdown cleanup, natural relation templates, endpoint/relation-focused adjacent source windows with lossless bounded fallback, scoped uncertainty, clean-window preference, expanded relation cues, and a self-relation guard. Immutable evidence and raw labels are unchanged.

## Real-corpus qualification

| gate | result |
|---|---|
| Reviewed supported candidates recognized | 5/5 |
| False supported among 20 non-supported/ambiguous candidates | 0 |
| Ambiguous candidates admitted as supported | 0/8 |
| Forwarded candidates retained | 25/25 |

The five supported cases are drip irrigation causing slow leak, insulation slowing/preventing evaporation, saturated soil retaining moisture, reliable capacity depending on load, and setup success depending on usage profile. Ambiguous cases remain non-supporting/unknown for learner admission.

## Validation

- Focused local assessor tests: 12 passed.
- Covered regressions: real proposition templates, Markdown residue normalization without evidence mutation, adjacent source-window selection, scoped uncertainty, `holds` retention, and co-occurrence-only rejection.
- Historical qualification fixtures remain exercised by the same adapter tests.

The machine-readable row-level corpus is in `MNEME_P2_F0_Real_Corpus_Assessor_Regression_20260926.json`.
