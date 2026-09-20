# MNEME P2.3 Assessor Qualification — Provenance v2 Failure Receipt

Status: **FAILED at Q1; qualification stopped; pilot calls: 0**  
Tested commit: `0abd74ec2b9d856d432b1103ae815e029c87e2e4`  
Run: `qualification-20260920-01`  
Provider: DeepInfra  
Assessor: `Qwen/Qwen3-235B-A22B-Instruct-2507`  
Contract: `p2-assessor-v2` / `p2-assessor-production-v3` / `p2-provenance-v1`

This was the one authorized fixed Q1/Q2/Q3 qualification attempt. Q1 returned
and was persisted before validation. Q1 failed semantic qualification, so Q2
and Q3 were not dispatched. No retry, repair, replacement sample, resampling,
model substitution, or pilot call occurred. Historical qualification receipts
remain unchanged.

## Q1 request

The fixed request supplied these sources:

```text
s0 [external, available]: Pulling the lever released the latch.
s1 [model_output, available]: Pulling the lever released the latch.
```

The monitors were:

```text
latch     : causes, source s0
echo      : causes, source s1
unrelated : causes unrelated, source s0
```

The declared current-input source was `s0`. The semantic assessor was required
to identify supported language, covered absence, and the model-output echo;
MNEME was then to derive provenance deterministically.

## Returned result (sanitized exact structure)

```json
{
  "schema_version": "p2-assessor-v2",
  "assessments": [
    {"monitor_id":"latch","status":"present","relation_support":"supported","expression_status":"expressed","coverage":{"complete":true,"source_slots":["s0"],"reason":null},"evidence":{"source_slot":"s0","quote":"Pulling the lever released the latch."},"corresponding_source_slots":["s0"]},
    {"monitor_id":"echo","status":"absent","relation_support":"unsupported","expression_status":"not_expressed","coverage":{"complete":true,"source_slots":["s1"],"reason":"Required source slot s1 is not available in context."},"evidence":null,"corresponding_source_slots":[]},
    {"monitor_id":"unrelated","status":"present","relation_support":"supported","expression_status":"expressed","coverage":{"complete":true,"source_slots":["s0"],"reason":null},"evidence":{"source_slot":"s0","quote":"Pulling the lever released the latch."},"corresponding_source_slots":["s0"]}
  ]
}
```

## Validation and disposition

The result was valid JSON and used the corrected schema, but strict semantic
qualification rejected it with:

```text
Q1 monitor echo has wrong status: expected 'present', got 'absent'
```

The latch row was semantically correct. The echo row incorrectly treated the
available model-output source as unavailable and absent. The unrelated row
incorrectly treated the latch quotation as support for an unrelated target.
Because Q1 failed, deterministic provenance resolution was not admitted for
this case and Q2/Q3 were not sent.

DeepInfra and the credential were functional: Q1 returned normally and was
durably recorded with **781 input**, **331 output**, and **1,112 total tokens**.
Provider cost was not supplied. The assessor fingerprint and host binding were
recorded without credentials. The pilot reservation count is zero.

This receipt records a semantic assessor failure under the corrected
responsibility split. It does not reclassify any historical attempt and does
not authorize a retry. Further qualification requires a reviewed in-scope
correction or architectural review.
