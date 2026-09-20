# MNEME P2.3 Assessor Qualification — Prompt v4 Failure Receipt

Status: **FAILED at Q1; qualification stopped; pilot calls: 0**  
Tested commit: `916b0e9b8c536c2583d810d08f45170faea14a1e`  
Run: `qualification-20260920-v4`  
Provider: DeepInfra  
Assessor: `Qwen/Qwen3-235B-A22B-Instruct-2507`  
Contract: `p2-assessor-v2` / `p2-assessor-production-v4` / `p2-provenance-v1`

This was the one fixed qualification run after the prompt-only remediation.
Q1 returned and was persisted before validation. Q1 failed, so Q2 and Q3 were
not dispatched. No retry, repair, replacement sample, resampling, model
substitution, or pilot call occurred. Historical qualification evidence remains
unchanged.

## Q1 disposition

Qwen correctly returned the latch relationship as present and supported, and it
correctly rejected the unrelated target as absent and unsupported. It still
returned the required model-output echo as absent:

```text
monitor echo absent requires complete available-source coverage
```

The returned echo row claimed that source `s1` was unavailable in the current
context even though the request declared `s1` as an available `model_output`
source. Its exact returned semantic fields were:

```json
{
  "monitor_id": "echo",
  "status": "absent",
  "relation_support": "unsupported",
  "expression_status": "not_expressed",
  "coverage": {
    "complete": true,
    "source_slots": [],
    "reason": "Required source slot 's1' is not available in the current context and no supporting content was found in available sources."
  },
  "evidence": null,
  "corresponding_source_slots": []
}
```

## Accounting and conclusion

DeepInfra and the credential were functional. Q1 returned normally with **877
input**, **343 output**, and **1,220 total tokens**; provider cost was not
supplied. The assessor binding and result were durably recorded without any
credential material. Q2/Q3 and the pilot have zero calls.

The v4 prompt correction addressed the earlier proposition-composition error:
the unrelated monitor is now correctly rejected. The remaining echo failure is
semantic assessor behavior after that correction, not a transport, persistence,
validator, or deterministic-provenance defect. Further prompt engineering or
resampling is not performed automatically. P2.3 remains stopped for assessor
suitability review.
