# MNEME P2.3 Pilot — Live Extraction/Assessment Stop

**Status:** FAIL_STOP — pilot stopped at the first fixed developmental coordinate
**Run:** `p2-pilot-live-20260920`
**Prepared commit:** `34743a30ed5ad04db2c1422aa87b6b3c75535adf`
**Qualification:** preserved `MNEME_P2.3_Assessor_Qualification_Polarity_V8_Pass_Receipt`; no qualification calls were dispatched for this run

The fresh bounded pilot dispatched exactly three new provider calls at the first
fixed coordinate (`subject 0 / episode 0`): one Gemma development response and
the initial extraction plus its one permitted repair. All three returned and
were durably recorded before validation. No assessor or evaluation call was
made. The pilot stopped before the Qwen assessor because the repaired residue
contained no relationship edge for the production assessment adapter.

## Call accounting

| Call | Role | Result | Usage | Disposition |
|---|---|---|---:|---|
| `development-s0-e0` | Gemma development response | returned | 26 input / 66 output / 92 total | accepted developmental episode |
| `extraction-s0-e0` | Gemma extraction | returned | 719 input / 581 output / 1,300 total | rejected by strict residue validation; one repair allocated |
| `extraction-s0-e0-repair` | Gemma extraction repair | returned | 743 input / 183 output / 926 total | structurally valid residue, but no `edge_candidates`; pilot stop |
| **total** |  | **3 returned** | **1,488 / 830 / 2,318** | **FAIL_STOP** |

Provider cost was not retained in the sanitized pilot reservation payload, so
cost is unknown. No Qwen assessor or evaluation result exists for this run.

## Evidence

The development input was the fixed parts-family sentence:

> I sorted socket wrenches into labeled bins, so finding a repair size takes less time.

Gemma replied with a natural-language response that included a Markdown
emphasis span around “speed up your workflow and reduce frustration.” The
initial extractor emitted concepts and edges, but its evidence for the model
output omitted the exact Markdown markers. The immutable-source validator
therefore rejected the initial result. This consumed the one permitted repair.

The repair returned valid source-bound concepts, including `tool organization`,
`time saving`, and `workflow improvement`, but returned no `edge_candidates`.
Because the production assessment contract requires a source-supported
proposition to assess and publish, the adapter failed closed with:

> `PilotStudyError: extraction has no assessable relationship: extraction-s0-e0`

The repair was not regenerated and the pilot was not restarted. The complete
sanitized request/result/source artifacts are preserved in
`MNEME_P2.3_Pilot_Live_Extraction_Stop_20260920_Bundle.json`; the original
prepared run remains under the external laboratory root. This receipt contains
no credential, authorization header, or unrelated private data.

## Disposition

This is not a credential, transport, assessor, or evaluation-isolation
failure. The Gemma calls returned successfully and the prepared host binding
matched. The first extraction was a model-output/provenance validation failure;
the permitted repair passed structural residue validation but did not supply a
relationship for the required assessor/publication stage. Pilot adequacy,
readouts, and research outcome are unassessed. Historical pilot and
qualification receipts remain unchanged.
