# MNEME P2.3 Assessor Monitor Proposition Remediation Receipt

Status: **OFFLINE GATE PASS — NO PROVIDER CALL**  
Base: `ad58878`  
New assessor schema: `p2-assessor-v3`  
New prompt: `p2-assessor-production-v5`  
Provenance: `p2-provenance-v1`

The Q1 prompt-v4 failure exposed that monitors serialized partial relations and
implicitly relied on the assessor to join omitted fields with the candidate.
The request contract now requires every candidate and every monitor relation to
be a complete self-contained `{from, to, relation}` proposition. Partial
propositions fail closed before provider dispatch. The normalized proposition
is defensively copied at construction so later caller mutation cannot produce a
partial provider payload.

All current qualification monitors were updated without changing source text,
semantic difficulty, expected classifications, provenance rules, or acceptance
criteria:

- Q1 latch and echo: `lever → causes → latch_release`;
- Q1 unrelated: `lever → causes → unrelated`;
- Q2 jacket: `rain_jacket → raises → shade`;
- Q2 shade: `handle → raises → shade`;
- Q3 dial and unavailable output: `dial → stops → ticking`.

`assessor_generation_request()` remains the sole provider request builder used
by qualification and the pilot boundary. Static audit found no other
`AssessorMonitor` construction path.

Validation:

- focused assessment/qualification tests: **20 passed** before the final
  immutability regression;
- complete pytest suite: **283 passed**;
- Ruff: **PASS**;
- strict mypy across `src/mneme`: **PASS**;
- wheel build and fresh-install `mneme --help` smoke: **PASS**.

Historical qualification outputs and receipts remain unchanged. The next step
is one fixed Q1/Q2/Q3 live qualification under the new prospective contract,
with no retries, repairs, or resampling.
