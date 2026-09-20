# P2.3 Source-Role v6 Qualification — Append-Only Audit Correction

This addendum corrects a statement in
`MNEME_P2.3_Assessor_Qualification_Source_Role_V6_Failure_Receipt.md`.
The original receipt is preserved unchanged as historical evidence.

The original receipt said that Q3’s dial row was correct. Inspection of the
persisted raw result shows that it was not. Qwen returned:

```json
{
  "monitor_id": "dial",
  "status": "present",
  "relation_support": "supported",
  "expression_status": "expressed",
  "evidence": {
    "source_slot": "s0",
    "quote": "Turning the dial did not stop the ticking; the sound continued."
  }
}
```

The quotation supports that the negated statement was expressed, but it does
not support the positive proposition `dial → stops → ticking`. The required
classification is `present`, `unsupported`, `expressed`.

Q3 also returned `absent` for `unavailable_output`, although source `s1` was
declared unavailable. The required result is `unknown`; strict validation
correctly rejected this first surfaced error:

`monitor unavailable_output absent requires complete available-source coverage`

Therefore Q3 contains two model semantic failures: negation handling and
epistemic handling of unavailable coverage. The provider returned normally,
the request was self-contained, persistence was durable, and the validator
failed closed. No code or acceptance criterion is changed by this correction.
The qualification remains failed and the pilot remains at zero calls.
