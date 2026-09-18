# MNEME append-only engineering log

## 2026-09-17

- Initialized the MNEME repository and ingested the supplied project documents.
- Established P0.1 scope: host contracts, FakeHost, Gemma boundary, qualification, and repository hygiene.

## 2026-09-17

- Added the P0.1 work-queue package and moved it through candidate and validation review.
- Verified the cheap validation path: 7 tests, Ruff, and strict mypy pass.
- Completed the P0.1 queue package after recording all declared validation receipts; live Gemma remains credential-gated.

## 2026-09-17 remediation

- Separated generation-affecting request material from administrative run metadata.
- Removed unverified native structured-output claims, added representative schema checks, honest fallback rendering metadata, and offline provider failure coverage.
- Added mypy to CI. P0.1 implementation is substantially complete but remains WAITING on external live Gemma qualification.

## 2026-09-17 P0.1 remediation

- Proved FakeHost generation ignores administrative metadata while retaining visible-input and seed effects.
- Tightened structured qualification to separate JSON parsing from three representative schema validations.
- Exercised FakeHost failure reporting and added offline HTTP, timeout, malformed-response, provider-error, and response-shape coverage for Gemma.
- Marked Gemma rendering as the explicit MNEME fallback transcript and removed its unverified native structured-output capability claim.

## 2026-09-17 DeepInfra preparation

- Resolved `google/gemma-4-E4B-it` revision `ee0ef6023621cff504d758262d4e04895a5af4a2` as the downloadable local reference and recorded the model checksum.
- Added the credential-free DeepInfra OpenAI-compatible backend, offline provider-boundary tests, setup instructions, and live qualification command.
- Selected DeepInfra as the inexpensive live P0.1 backend; hosted exact-weight equivalence remains unknown and P0.1 stays WAITING on credentialed qualification.

## 2026-09-18 live P0.1 qualification

- Ran the bounded DeepInfra qualification with the user-provided credential; the credential was process-only and did not enter artifacts.
- Basic generation, multi-turn chat transport, and all three structured JSON schema cases passed; seed control remained correctly unsupported.
- Tightened structured prompts to require JSON-only output and deterministic temperature before the successful live run.
