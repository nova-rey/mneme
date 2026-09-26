# MNEME P2.3 Shared-Interloper r7 — Invalid No-Treatment Receipt

Status: **INVALID_NO_TREATMENT**

Run: `p23-shared-interloper-ab-20260926-r7`

Implementation: `a183cbca73d066201b533b7824e6f3fd094b9f5c`

## Disposition

The route-selection correction was validated offline before this run. r7
completed its qualification and all three conversational threads, but the
MNEME arm never received a selected or applied route. The run is therefore
invalid for behavioral interpretation. It is preserved as a new prospective
invalid attempt; r6 and all earlier receipts remain unchanged.

The run consumed 100 scheduled role calls: 3 local assessor qualification
calls and 97 pilot role calls. It made no evaluation/readout comparison after
the treatment gate failed.

## What the evidence shows

At A0, Gemma's developmental response and specialist extraction admitted a
supported `Drip Irrigation → causes → Slow Leak` relationship. The learner
state was nonzero and eligible at later coordinates. The repaired controller
was capable of semantic descriptor reachability, as proved by the separate
instrumentation preflight.

This trajectory did not, however, provide a later external query that reached
that association. The later Qwen messages were:

* A1: `I like the wicking idea ... a small bucket with a hole in the bottom`
* A2: `... old buckets ... worried about the soil drying out too fast ...`
* B0–B2: trip planning with limited luggage and uncertain timing
* C0–C2: remote workshop/solar station planning

The A2 route view considered only a current-episode `hole/system` route and
selected nothing. C2 considered two current-episode `hole/system` routes and
selected nothing. The learned `Drip Irrigation` route was absent from the
candidate set because its canonical content was not present in those later
external inputs. No memory payload was constructed for M and control influence
remained zero.

This is not evidence that semantic route matching is still broken. The
preflight and regression test demonstrate that `drip method` reaches
`Drip Irrigation` and produces an applied payload when that query is actually
present. It is evidence that the frozen stochastic conversation does not
guarantee a later relevant opportunity. Re-running the unchanged schedule
until Qwen happens to mention the learned neighborhood would be favorable
sample selection, so no such retry is performed.

## Gate record

```json
{
  "eligible_state": true,
  "selected_influence": false,
  "applied_influence": false,
  "control_influence_zero": true,
  "valid": false,
  "first_applied_coordinate": null,
  "status": "INVALID_NO_TREATMENT"
}
```

Qualification Q1/Q2/Q3 passed. Local Gemma, GLiNER2.5, and pinned local
DeBERTa completed their assigned work. The shared Interloper remained
`Qwen/Qwen3-30B-A3B`; its transcript and request-role evidence are included in
the committed evidence bundle.

## Complete evidence

The machine-readable run bundle, including all sanitized requests/results,
transcripts, extractions, assessments, learner traces, reservations, model
fingerprints, and manifests is in
[the r7 evidence bundle](MNEME_P2.3_Shared_Interloper_R7_Invalid_No_Treatment_Evidence/).
It contains no API credentials or authorization headers. The bundle is the
authoritative exact evidence for this invalid run.

## Required decision boundary

The general route plumbing defect is corrected and independently preflighted.
The remaining blocker is experimental-condition construction: a valid A/B
requires a prespecified later relevant opportunity, but the current frozen
stochastic schedule does not guarantee one. Creating that opportunity would
require changing the schedule/condition or authorizing a new non-fishing
design; it cannot be solved by another unchanged run.

