# MNEME Phase One bridged live run failure receipt

Date: 2026-09-19
Tested code: `44e9d75ddd16eebe757f0c7975a07636c0f9b318`
Provider/model: DeepInfra / `google/gemma-4-E4B-it`
Run workspace: `/home/nyx/.local/share/mneme/phase-one-live/20260919-bridged-v1-44e9d75/`

Status: **BLOCKED at P1.2 after the permitted extraction repair**

This was the one bounded run authorized from the corrected deterministic-route
driver. DeepInfra returned all eight dispatched calls. No transport retry or
replacement study was attempted. The earlier 18-call history and later
four-call duplicated-fixture failure remain unchanged historical evidence.

## Call accounting

| Ordinal | Gate | Role | Result | Input | Output | Total | Finish |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | P1.1 | developmental response | returned | 23 | 192 | 215 | length |
| 2 | P1.1 | developmental response | returned | 22 | 192 | 214 | length |
| 3 | P1.1 | extraction initial | returned | 763 | 375 | 1,138 | stop |
| 4 | P1.1 | extraction initial | returned | 760 | 286 | 1,046 | stop |
| 5 | P1.2 | naming | returned | 71 | 8 | 79 | stop |
| 6 | P1.2 | developmental response | returned | 190 | 93 | 283 | stop |
| 7 | P1.2 | extraction initial | returned | 636 | 334 | 970 | stop |
| 8 | P1.2 | extraction repair | returned | 664 | 381 | 1,045 | stop |
| **Total** |  |  | **8** | **3,129** | **1,861** | **4,990** |  |

The provider and credential therefore worked. Cost was not reported by the
provider. No P1.3 call was dispatched.

## P1.1 evidence and disposition

The two reviewed developmental inputs were:

1. `Checking the weather before our hike reminded us to pack a rain jacket.`
2. `A rain jacket keeps a sudden shower from ending the hike early.`

Both responses were accepted exactly once. Both initial extractions passed
strict quotation validation and published one source-supported edge each. The
model emitted no explicit route candidates; publication deterministically
derived the following route from the accepted edges:

```text
weather_check --causes--> rain_jacket --enables--> hike
```

The persisted derived route is
`derived:a1367dc56418ba96`, with edge provenance from both developmental
interpretations. P1.1 therefore passed the route criterion. Its accepted-state
counters were lineage revision 4, accepted episodes 2, graph revision 2, and
self-view version 0.

## P1.2 failure

The naming call durably adopted the neutral name `Gemma4` and recorded the
provider/model, fingerprint, finish reason, and usage in the identity
generation ledger.

The relevant response input was:

> Explain why the rain jacket matters on a hike.

The response was accepted and the selected graph payload was recorded in the
turn trace. The initial extraction then returned an edge whose evidence was:

> `a weather check can cause or enable the need for a rain jacket`

That phrase does not occur verbatim in the immutable source bundle. MNEME
rejected it with:

```text
residue.edge_candidates[0].evidence[0]: evidence quotation does not occur verbatim in source
```

The one permitted repair returned a second paraphrase:

> `a weather check can cause or enable the need for a rain jacket during a hike`

It failed the same deterministic quotation check. The interpretation remained
failed, no graph write occurred for that turn, and execution stopped. This is a
model-output/provenance-validation failure, not a provider or credential
failure. P1.2 is not accepted because its required interpreted correction path
did not complete. P1.3 was not attempted.

## Private artifacts and integrity

The private run artifacts are preserved outside Git:

| Artifact | SHA-256 |
|---|---|
| `live_summary.json` | `eb70b31db3a4a90a5bc0a6bc187b6e9d283aee38a90294b4a250230b0341522c` |
| `lineage.sqlite3` | `d7fd0a9f0536626939563acd80ec841a400d581abaaaae4a649891ff7ab0c96e` |

The machine-readable companion is
`MNEME_Phase_One_Live_Bridged_Run_Failure_Receipt.json`. No credential,
authorization header, or unrelated private conversation content is included.

The current live package returns to `WAITING`. The unused portion of this
27-call authorization is not spent automatically after the required P1.2
failure; any repair or new live run requires explicit authorization. No Phase
One release tag was created and Phase Two was not started.
