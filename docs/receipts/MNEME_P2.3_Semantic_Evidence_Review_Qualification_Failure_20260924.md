# MNEME P2.3 Semantic Evidence Review Qualification — Failure

- **Date:** 2026-09-24
- **Contract:** `semantic-evidence-reconciliation-v1`
- **Model:** `Qwen/Qwen2.5-7B-Instruct`
- **Provider:** DeepInfra
- **Calls:** 3 returned; no retry, fourth case, pilot, or resampling
- **Usage:** 531 input tokens, 673 output tokens, 1,204 total tokens; provider cost unavailable
- **Status:** FAIL; P2.3 pilot did not resume

All three dispatched requests reached DeepInfra and were durably reserved and
returned before local validation. The host fingerprint recorded in each result
is the configured non-developing evidence-reviewer binding. Historical campaign
calls and receipts remain unchanged.

## Fixed cases

### Q1 — Markdown formatting omitted by extractor

Source: `- **rain jacket** kept my shoulders dry during the walk.`

The reviewer returned:

```json
{
  "grounded": true,
  "evidence": "- **rain jacket** kept my shoulders dry during the walk."
}
```

The quotation was exact and unique. Q1 passed.

### Q2 — Source-grounded paraphrase

Source: `The rain jacket kept my shoulders dry during the walk.`

The proposed quotation was a paraphrase: `A waterproof jacket protected me from
getting wet.` The reviewer returned:

```json
{
  "grounded": true,
  "evidence": "The rain jacket kept my shoulders dry during the walk."
}
```

The quotation was exact and unique. Q2 passed.

### Q3 — Unsupported extraction

Source: `The toolbox stayed dry on the shelf.`

The proposition asked whether a rain jacket kept shoulders dry. The reviewer
returned:

```json
{
  "grounded": false,
  "evidence": ""
}
```

The semantic judgment was the required rejection, but the strict contract
requires no `evidence` field when `grounded` is false. The empty field is still
a malformed result, so validation failed closed. Q3 therefore failed
qualification and no fourth negation check or pilot call was dispatched.

## Disposition

This is a bounded reviewer output-contract failure, not a credential or
transport failure and not evidence that the source-grounding judgment itself
was unreliable. The offline validator intentionally rejects extra fields and
never turns the malformed response into accepted evidence. The qualification
run is durably marked `FAILED`; the private run directory retains the complete
sanitized requests, provider results, reservations, host fingerprints, and
failure state.
