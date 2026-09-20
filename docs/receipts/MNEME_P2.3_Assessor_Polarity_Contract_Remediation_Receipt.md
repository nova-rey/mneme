# MNEME P2.3 Assessor Polarity Contract Remediation Receipt

**Status:** OFFLINE GATE PASS — NO PROVIDER CALL  
**Base:** `b8116de`  
**New assessor schema:** `p2-assessor-v5`  
**New prompt:** `p2-assessor-production-v7`  
**Provenance:** `p2-provenance-v1` unchanged

The v7 qualification reached the intended negation case, but the previous
vocabulary conflated proposition coverage with polarity. The prospective
contract now separates:

- `status`: whether the proposition is addressed (`present`, `absent`, `unknown`);
- `relation_support`: what the source says (`supported`, `contradicted`, `unsupported`, `unknown`);
- `expression_status`: how it is expressed (`affirmed`, `negated`, `not_expressed`, `unknown`).

The validator rejects inconsistent combinations. Explicit negation is
`present` / `contradicted` / `negated`, with a uniquely resolved exact quote.
A genuinely absent proposition is `absent` / `unsupported` / `not_expressed`.
Incomplete required coverage is `unknown` / `unknown` / `unknown`.

The learner boundary now carries the semantic disposition in the existing
observation evidence payload and reconstructs it during replay. Contradicted
observations remain auditable, do not become ordinary absence, and receive no
positive learner credit. Conflicting semantic dispositions for one occurrence
fail closed. No contradiction-learning coefficient or other new learner rule
was introduced.

Historical `p2-assessor-v4` results remain unchanged and are readable only
through the explicit archival reader, preserving their original `expressed`
vocabulary. The production validator is v5-only.

## Validation

- focused semantic, learner, publication, replay, and qualification tests: **59 passed**;
- complete pytest suite: **304 passed**;
- Ruff: **PASS**;
- strict mypy across `src/mneme`: **PASS**;
- wheel build and fresh-install `mneme --help` smoke: **PASS**;
- provider calls during remediation: **0**.

The exact serialized v5 Q1/Q2/Q3 requests contain the new vocabulary and
complete source-coverage rule. Qualification and pilot continue to share the
same `assessor_generation_request()` production path. Historical qualification
receipts were not rewritten.

The next live action is one fixed Q1/Q2/Q3 Qwen qualification under the
standing bounded-verification authorization, with no retries, repairs, or
resampling.
