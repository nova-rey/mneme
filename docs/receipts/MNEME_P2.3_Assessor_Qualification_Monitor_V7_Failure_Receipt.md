# MNEME P2.3 Assessor Qualification — Self-Contained Monitor v7 Failure Receipt

**Status:** LIVE QUALIFICATION STOP — Q1/Q2 passed, Q3 failed; pilot calls: 0  
**Run:** `qualification-v7`  
**Validated main:** `ce68af411d9530f1e8d32d4b4febef28dab50fd2`  
**Monitor correction:** `037736e`  
**Contract:** `p2-assessor-v4` / `p2-assessor-production-v6` / `p2-provenance-v1`  
**Assessor:** DeepInfra `Qwen/Qwen3-235B-A22B-Instruct-2507`

This is the one fixed Q1/Q2/Q3 campaign after the self-contained-monitor correction. The provider returned all three results and each was durably retained before local validation. No retry, repair, replacement sample, resampling, model substitution, or pilot call occurred. Historical receipts remain unchanged.

## Accounting

| Case | Provider result | Validation | Usage (input/output/total) | Disposition |
|---|---|---|---:|---|
| Q1 | returned | passed | 1,107 / 355 / 1,462 | accepted qualification case |
| Q2 | returned | passed | 1,092 / 233 / 1,325 | accepted qualification case |
| Q3 | returned | failed | 991 / 231 / 1,222 | stop: semantic expectation mismatch |
| **Total** | **3 returned** | **Q1/Q2 pass; Q3 fail** | **3,190 / 819 / 4,009** | **qualification failed; pilot 0** |

Provider cost was not supplied. The DeepInfra credential and transport were functional; all three calls returned and host fingerprints matched the prepared assessor binding.

## Q1 and Q2

Q1 and Q2 passed the unchanged semantic cases and deterministic provenance path. Q1 resolved the external latch occurrence as `external_supported` and the model-output echo as `current_input_echo`. Q2 resolved the memory-backed shade output as `exposure_linked`. The serialized requests contain complete monitor propositions for every monitor.

## Q3 stop

The fixed Q3 request contains the complete proposition `dial → stops → ticking` and the source text:

> Turning the dial did not stop the ticking; the sound continued.

The qualification expectation intentionally requires the proposition to be **present/expressed but unsupported** because the source explicitly discusses the proposition under negation, and requires the unavailable output monitor to be `unknown`.

Qwen returned the following relevant rows:

```json
[
  {
    "monitor_id": "dial",
    "status": "absent",
    "relation_support": "unsupported",
    "expression_status": "not_expressed",
    "coverage": {
      "complete": true,
      "source_slots": [
        "s0"
      ],
      "reason": "The event described in the monitor relation 'dial stops ticking' is not supported by the source; the text states that turning the dial did not stop the ticking."
    },
    "evidence": null,
    "corresponding_source_slots": []
  },
  {
    "monitor_id": "unavailable_output",
    "status": "unknown",
    "relation_support": "unknown",
    "expression_status": "unknown",
    "coverage": {
      "complete": false,
      "source_slots": [],
      "reason": "The required source slot 's1' is unavailable, preventing assessment."
    },
    "evidence": null,
    "corresponding_source_slots": []
  }
]
```

The unavailable-output row is correct. The `dial` row is semantically rejected because it returned `status: absent` and `expression_status: not_expressed`; the frozen expectation is `status: present`, `relation_support: unsupported`, `expression_status: expressed`. The failure is therefore a semantic assessor qualification failure, not a monitor serialization, transport, credential, persistence, or provenance-resolution failure.

## Exact evidence and disposition

The complete sanitized serialized requests and provider results for all three calls are preserved in the accompanying JSON receipt. The request contains no authorization headers or secret material. The run stopped at Q3 under the approved first-failure rule. P2.3 remains `WAITING` on assessor qualification; the pilot remains at zero calls. Under the standing stop rule, this repeated Q3 semantic failure is evidence for assessor-suitability review; no further prompt engineering or resampling is performed automatically.
