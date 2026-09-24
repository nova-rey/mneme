# MNEME P2 contingent residue capacity admission correction

Date: 2026-09-24

## Scope

The preserved contingent run stopped at interactive turn 3 because a valid 17-concept extractor result was rejected wholesale by the 16-item admission bound, and the single repair then returned length-terminated JSON. This correction changes only the deterministic acquisition boundary. Provider results and the historical stop remain unchanged.

The extractor result remains immutable. MNEME now validates candidates independently, rejects malformed or dependency-invalid items individually, deduplicates canonical duplicates, and applies deterministic capacity admission after validation. Valid excess candidates receive the reason code `not_admitted_capacity`; they do not consume the repair allowance. Candidate ordering is based on approved confidence/salience admission metadata with canonical content tie-breaking. No learner credit is created for rejected or capacity-omitted material.

A returned coordinate can also revalidate an earlier persisted attempt after a later repair failed. This is a no-provider recovery path; it does not rewrite either raw attempt.

## Offline evidence

- 17 valid concepts with a cap of 16: 16 admitted, one `not_admitted_capacity`, no repair.
- Relationship and route capacities are enforced after item validation.
- Malformed candidates, missing dependencies, duplicates, and discontinuous routes are handled item-wise while unrelated valid material survives.
- Selection is deterministic across insertion order and canonical duplicate candidates.
- Completely unparsable output still fails closed.
- A persisted initial result can be revalidated after a failed repair without a provider call.
- Omitted/rejected candidates are absent from the validated residue and therefore cannot reach graph publication or learner credit.

Validation at this boundary: 380 pytest tests, Ruff, strict mypy, wheel build, and `git diff --check`; zero provider calls.

## Continuation rule

The historical interactive turn-3 request, response, extraction attempt 0, and repair attempt 1 remain preserved. The next continuation may process the persisted initial result under this correction and resume the existing coordinate. It must not regenerate the conversation or restart the study.
