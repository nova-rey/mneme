# MNEME P2.3 Assessor Qualification — Source-Role v6 Failure Receipt

Status: **FAILED at Q3; qualification stopped; pilot calls: 0**  
Tested commit: `46593a6f8ada594ac920d5da55dc7a71849fa1a6`  
Run: `qualification-20260920-v6`  
Provider: DeepInfra  
Assessor: `Qwen/Qwen3-235B-A22B-Instruct-2507`  
Contract: `p2-assessor-v4` / `p2-assessor-production-v6` / `p2-provenance-v1`

This was the one fixed Q1/Q2/Q3 qualification after the source-role request
contract correction. All three provider calls returned and were durably
persisted before validation. Q1 and Q2 passed. Q3 failed semantic validation,
so no pilot call was made. There were no retries, repairs, replacement samples,
resampling, or model substitutions. The complete sanitized request/result
artifacts remain outside the repository at:

`/tmp/mneme-p2-qualification-20260920-v6/experiments/p2-developmental-pilot/revisions/1/runs/qualification-20260920-v6/`

## Call accounting

| Case | Result | Input | Output | Total | Disposition |
|---|---|---:|---:|---:|---|
| Q1 | returned | 1,107 | 339 | 1,446 | accepted qualification case |
| Q2 | returned | 1,092 | 228 | 1,320 | accepted qualification case |
| Q3 | returned | 991 | 237 | 1,228 | rejected by strict semantic validation |
| **Total** | 3 returned | **3,190** | **804** | **3,994** | pilot: 0 calls |

Provider cost was not supplied. The DeepInfra credential and Qwen provider were
functional.

## Q1 — passed

The self-contained monitors asked for the complete latch proposition, the same
complete proposition in model output with `s1` as evidence and `s0` as
correspondence, and a distinct unrelated proposition. Qwen returned:

```json
{"latch":"present/supported", "echo":"present/supported", "unrelated":"absent/unsupported"}
```

The exact accepted evidence quotations were `Pulling the lever released the
latch.` from `s0` and `s1`. Deterministic resolution classified the occurrences
as `external_supported` and `current_input_echo` respectively.

## Q2 — passed

The shade monitor declared `s2` as its evidence source and `s1` as its
correspondence source. Qwen returned the output quotation from `s2`:

```json
{
  "monitor_id": "shade",
  "status": "present",
  "relation_support": "supported",
  "expression_status": "expressed",
  "evidence": {"source_slot": "s2", "quote": "Turning the handle raises the shade."},
  "corresponding_source_slots": ["s1"]
}
```

The unrelated rain-jacket direction was absent/unsupported. Deterministic
resolution classified the shade occurrence as `exposure_linked` with both
recorded exposure and replay ancestry retained.

## Q3 — failed

The Q3 request supplied an external source `s0` containing the negated dial
statement and declared model-output source `s1` unavailable. The expected
semantic result was a supported negated statement for `dial` and `unknown` for
the unavailable output monitor. Qwen returned the dial row correctly, but
returned `absent` for the unavailable monitor:

```json
{
  "monitor_id": "unavailable_output",
  "status": "absent",
  "relation_support": "unsupported",
  "expression_status": "not_expressed",
  "coverage": {
    "complete": true,
    "source_slots": ["s1"],
    "reason": "Required source slot s1 is unavailable and cannot be inspected."
  },
  "evidence": null,
  "corresponding_source_slots": []
}
```

The fail-closed validator rejected this as:

`monitor unavailable_output absent requires complete available-source coverage`

This is a model semantic/coverage classification failure: the unavailable
source requires `unknown`, not `absent`. The source-role serialization was
complete, and Q1/Q2 demonstrate that occurrence-versus-correspondence binding
now works. No deterministic provenance or persistence defect was observed.

## Disposition

The bounded campaign consumed exactly three new Qwen calls and stopped after the
first failing qualification case in the fixed order. P2.3 pilot calls remain
zero. Historical qualification failures remain unchanged. This evidence does
not authorize further prompt engineering, resampling, assessor substitution, or
pilot execution; it requires assessor-suitability review under the existing
Phase Two stop rules.
