# MNEME P2.3 Assessor Prompt Semantics Remediation Receipt

Status: **OFFLINE GATE PASS — NO PROVIDER CALL**  
Base evidence: Q1 failure at `0abd74e` / evidence commit `f3129f1`  
New prompt version: `p2-assessor-production-v4`  
Schema: `p2-assessor-v2`  
Provenance: `p2-provenance-v1`

The latest Q1 failure was audited against the persisted request/result. The
semantic assessor prompt left two rules implicit:

1. `available: true` means the source is inspectable regardless of whether its
   role is `external`, `model_output`, or `memory`; `current_input_source_slots`
   identifies current external input and does not make another available source
   unavailable.
2. A monitor relation is combined with the top-level candidate: fields present
   in the monitor override candidate fields and omitted fields inherit them.
   Support requires the complete resulting proposition, including participants,
   direction, relation, polarity, and target.

The prompt now states both rules explicitly. No fixture, expected outcome,
schema, assessor model, generation setting, provenance rule, learner value, or
acceptance criterion changed. The historical Q1 failure remains preserved.

Validation:

- `pytest -q`: **280 passed**
- Ruff: **PASS**
- strict mypy across `src/mneme`: **PASS**
- wheel build and fresh-install `mneme --help` smoke: **PASS**

The next live action is one newly fixed Q1/Q2/Q3 qualification under the new
prompt version, with no retries, repairs, replacement samples, or resampling.
The Phase Two pilot remains at zero calls and its 299-call ceiling is unchanged.
