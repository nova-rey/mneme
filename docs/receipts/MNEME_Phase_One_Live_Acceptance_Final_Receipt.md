# MNEME Phase One live acceptance — final receipt

Date: 2026-09-20  
Experiment: `phase-one-graph-wrapper-preview` (contract revision 1)  
Provider/model: DeepInfra / `google/gemma-4-E4B-it`  
Tested software revision: `68bebde87f22ffed06e3d07676274546a2477a45`  
Live workspace: isolated private run `20260920-name-normalized-68bebde`

This receipt closes the bounded live acceptance run only after its persisted
artifacts, state invariants, and offline validation were audited. It does not
claim personality, individuality, behavioral equivalence, or causal
developmental differentiation.

## Call accounting

The authorized ceiling was 27 calls. The run reserved and returned 23 calls;
there were no transport retries, repair calls, uncertain calls, or favorable
output resampling.

| Gate | Role | Calls | Input tokens | Output tokens | Total tokens |
| --- | --- | ---: | ---: | ---: | ---: |
| P1.1 | developmental response | 2 | 45 | 382 | 427 |
| P1.1 | extraction | 2 | 1,211 | 458 | 1,669 |
| P1.2 | naming | 1 | 71 | 8 | 79 |
| P1.2 | developmental response | 2 | 378 | 306 | 684 |
| P1.2 | extraction | 2 | 1,204 | 106 | 1,310 |
| P1.2 | frozen probe | 2 | 161 | 197 | 358 |
| P1.3 | evaluation | 12 | 676 | 1,626 | 2,302 |
| **Total** |  | **23** | **3,746** | **3,083** | **6,829** |

DeepInfra returned usage for every recorded call. Provider cost was not supplied
by the run and is therefore **unknown**, not estimated or invented. Sampling
was provider-managed (`seed: null`); the hosted weight revision was unknown.

## P1.1 — residue, graph, and route

The two developmental inputs were distinct natural experiences:

1. “Checking the weather before our hike reminded us to pack a rain jacket.”
2. “A rain jacket keeps a sudden shower from ending the hike early.”

Both model responses were durably recorded. Both extraction results passed the
strict source/evidence contract. The accepted edges were:

* `weather_check` **causes** `rain_jacket`, supported by source slot `s0`,
  code-point span `[0, 71)` in the first experience.
* `rain_jacket` **enables** `shower`, supported by source slot `s0`, code-point
  span `[0, 63)` in the second experience.

No extraction emitted a route candidate. Deterministic bounded graph search
derived `weather_check → rain_jacket → shower` with route key
`derived:c808ff5ddd7c4476`. Route provenance retains evidence from both
originating interpretations. The gate passed.

## P1.2 — response influence, identity, correction, and isolation

The deliberate naming call was durably persisted with its request, result,
provider/model identity, host fingerprint, finish reason, and usage. It adopted
the administrative self-view label `Gemma4`.

The relevant route was selected and applied in a traced response. A correction
directive suppressed that route under the declared correction context. The two
developmental interpretation records were valid empty residues because the
live-run extraction boundary used immutable external evidence only; host
responses remained recorded testimony and were not silently treated as fresh
independent developmental evidence.

The frozen cold-start probe returned `Gemma 4`, accepted by the deterministic
display-spacing normalization as the same adopted name. The unrelated probe
returned no selected routes. Both frozen probes left the checkpoint unchanged.
The gate passed.

## P1.3 — frozen comparison and evaluation isolation

The frozen checkpoint was read through the read-only evaluation boundary for 4
probes × 3 treatments × 1 repetition = 12 evaluation calls. The checkpoint
SHA-256 was
`5c918f39414bbb1e4eb3dff48ca3b2577da912ef8c5dd1c74b47bc05fbdf7c79`.

All 12 records carry the same checkpoint hash and identical before/after
developmental state digest
`f3c368aa6041e272c28ed436296766a45cee1ba9a01379effbd80cd8eef11778`.
Evaluation artifacts were written to the separate comparison workspace; the
developmental SQLite store has no checkpoint rows and was unchanged by the
comparison. Completed re-entry was host-free and did not repeat calls. The
fixed treatments were `no_memory`, `lexical`, and `graph`.

| Pair | Exact-match rate | Normalized-text match rate |
| --- | ---: | ---: |
| lexical vs graph | 0.0 | 0.0 |
| no-memory vs graph | 0.5 | 0.5 |
| no-memory vs lexical | 0.0 | 0.0 |

These are frozen readout measurements only. They are a Phase One preview, not
an individuality or personality metric.

## Restart, exact-once, and state audit

The final private working store contains 4 accepted episodes, 4 generation
records, 4 interpretation attempts, 1 durable naming generation record, 1
identity event, 2 response traces, and current lineage revision 10. Operation
IDs and generation records are unique. The restart/resume audit reopened the
store, preserved 4 accepted episodes and 4 interpretations, and confirmed that
accepted retry generation count was unchanged. No call was automatically
regenerated after an uncertain result because no uncertain result existed.

Private artifact hashes retained for audit:

* `lineage.sqlite3`: `c6b474c5c391b642d11900ffaf2a4e9851b4b6d3351fc1870fb39cd14b44979f`
* `p1.2.checkpoint.sqlite3`: `5c918f39414bbb1e4eb3dff48ca3b2577da912ef8c5dd1c74b47bc05fbdf7c79`
* `live_summary.json`: `4168b7cdc06155b2b1d48a4c4c188a423150f91926a8dbab9521436bf8fbde6b`
* `p1.3-comparison/comparison.json`: `73d5e0032eab5f3cc6ace6ebb59f7313e154bc4f821a0122558dbf31595de3b5`

The actual host fingerprint recorded DeepInfra, model
`google/gemma-4-E4B-it`, text generation and token-usage capabilities, and
`hosted_model_revision: unknown`. Exact hosted/local weight identity is not
established. No credential or authorization header is present in the
repository receipt, run artifacts, or logs.

## Validation and disposition

* complete pytest: **222 passed**;
* Ruff: **passed**;
* strict mypy: **passed**, 41 source files;
* installed-package CLI smoke: **passed**;
* persisted-artifact audit: **passed**;
* evaluation-isolation/state-invariance audit: **passed**;
* deterministic FakeHost integrated control: **passed** (23-call schedule,
  exact-once re-entry);
* real DeepInfra live acceptance: **P1.1 PASS, P1.2 PASS, P1.3 PASS**.

Phase One is accepted as the graph-wrapper preview under the approved bounded
criteria. Phase Two has not started. The observed hosted output variation is
ordinary provider-managed no-learning variation under these execution
conditions; it is not evidence of individuality or personality.
