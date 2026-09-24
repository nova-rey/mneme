# MNEME P2.3 Semantic Evidence Review Qualification v2 — PASS

- **Date:** 2026-09-24
- **Contract:** `semantic-evidence-reconciliation-v2`
- **Model:** `Qwen/Qwen2.5-7B-Instruct`
- **Provider:** DeepInfra
- **Calls:** 4 returned; no retries, repairs, or resampling
- **Usage:** 776 input tokens, 718 output tokens, 1,494 total tokens; provider cost unavailable
- **Pilot calls:** 0
- **Status:** QUALIFIED

## Qualification cases

1. **Markdown formatting omission — PASS.** Source `- **rain jacket** kept my shoulders dry during the walk.`; the reviewer returned `grounded=true` with that exact unique quotation.
2. **Source-grounded paraphrase — PASS.** Source `The rain jacket kept my shoulders dry during the walk.`; the reviewer returned `grounded=true` with the exact source sentence rather than the proposed paraphrase.
3. **Unsupported extraction — PASS CLOSED.** Source `The toolbox stayed dry on the shelf.`; the reviewer returned `grounded=false` with an empty placeholder, canonicalized to no quotation. No evidence was admitted.
4. **Negated source — PASS CLOSED.** Source `The rain jacket did not keep my shoulders dry during the walk.`; the reviewer returned `grounded=false` with no quotation. Contradiction was not converted to positive grounding.

Every request/result was reserved, dispatched, persisted, and validated through
the bounded reviewer path. Host fingerprints identify the configured
non-developing reviewer role. The audit verified four returned terminal
reservations, zero uncertain/failed calls, exact-quote uniqueness for positive
cases, no replacement quote for negative cases, and no pilot state or
lineage-development writes. Historical failed qualification evidence and the
120 prior campaign calls remain unchanged. Cumulative Phase Two campaign usage
is 127 returned provider calls; the standing 399-call contingency cap remains
unexceeded.
