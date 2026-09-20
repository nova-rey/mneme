# MNEME P2.3 Assessor Source-Role Contract Remediation Receipt

Status: **OFFLINE GATE PASS — NO PROVIDER CALL**  
Base: `4c6e8f0`  
New assessor schema: `p2-assessor-v4`  
New prompt: `p2-assessor-production-v6`  
Provenance: `p2-provenance-v1`

The previous fixed qualification stopped at Q2 because the assessor quoted the
memory antecedent for a memory-to-output monitor. The deterministic resolver
correctly rejected that quote as evidence for an output occurrence, but the
request did not distinguish occurrence evidence from antecedent correspondence.

The monitor contract now serializes three explicit source roles:

- `required_source_slots`: sources the monitor may inspect;
- `evidence_source_slots`: sources from which a supporting occurrence quotation
  may be returned;
- `correspondence_source_slots`: sources whose material an output expression may
  semantically match.

Q1 echo now inspects `s0` and `s1`, quotes only model output `s1`, and names the
external antecedent `s0` as correspondence. Q2 shade inspects `s1` and `s2`,
quotes model output `s2`, and names memory `s1` as correspondence. The
deterministic provenance resolver and all qualification expectations are
unchanged. Partial or undeclared source-role assignments fail closed before
provider dispatch.

The provider prompt explicitly describes these fields and forbids quoting the
memory antecedent as the occurrence in a memory-to-output monitor. Qualification
and pilot continue to share `assessor_generation_request()`.

Validation:

- focused assessment/qualification tests: **22 passed**;
- complete pytest suite: **284 passed**;
- Ruff: **PASS**;
- strict mypy over `src/mneme`: **PASS**;
- wheel build and fresh-install `mneme --help` smoke: **PASS**;
- provider calls during remediation: **0**.

Historical qualification results and receipts remain unchanged. The next action
is one fixed Q1/Q2/Q3 qualification under the v4/v6 request contract, stopping
at the first failed case with no retry or resampling.
