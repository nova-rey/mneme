# MNEME Phase One corrected P1.1 live failure receipt

Date: 2026-09-19
Tested code: `2cdf3ac10572bf9424220aee50706b01fc9f15ee`
Provider/model: DeepInfra / `google/gemma-4-E4B-it`
Run workspace: `/home/nyx/.local/share/mneme/phase-one-live/20260919-bridged-v2-534183a/`

Status: **BLOCKED at P1.1 because the required multi-hop route was not formed**

This bounded run preserved the current natural two-experience fixture and
stopped after the four predetermined P1.1 calls. DeepInfra returned every
call; no transport retry or replacement study was attempted. The prior live
runs and their receipts remain unchanged.

## Call accounting

| Ordinal | Gate | Role | Result | Input | Output | Total | Finish |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | P1.1 | developmental response | returned | 23 | 184 | 207 | stop |
| 2 | P1.1 | developmental response | returned | 22 | 192 | 214 | length |
| 3 | P1.1 | extraction initial | returned | 818 | 228 | 1,046 | stop |
| 4 | P1.1 | extraction initial | returned | 818 | 339 | 1,157 | stop |
| **Total** |  |  | **4** | **1,681** | **943** | **2,624** |  |

Provider-reported extraction cost metadata was present for calls 3 and 4
(`$0.00003916` and `$0.00005026` respectively). Response-call cost was not
persisted by the provider result, so total cost is partially unknown. No P1.2
or P1.3 call was dispatched.

## P1.1 evidence and disposition

The developmental inputs were distinct and human-plausible:

1. `Checking the weather before our hike reminded us to pack a rain jacket.`
2. `A rain jacket keeps a sudden shower from ending the hike early.`

Both developmental responses were accepted exactly once. Both extraction calls
returned JSON that passed strict source-quotation validation and published
accepted interpretations. The first interpretation supplied supported
concepts but no edge. The second supplied one supported edge,
`rain_jacket --enables--> hike`. Because the first accepted interpretation had
no edge, the accumulated graph contained no two-edge path. No route was
invented and no alias was added to force a pass.

This is a model-output/fixture execution result, not a provider or credential
failure. The run stopped at the required P1.1 criterion. The private artifacts
remain outside Git with these digests:

| Artifact | SHA-256 |
|---|---|
| `live_summary.json` | `df65e0eb6ed8ba8c982f60e73772504dc29ef586c1f61386ff876e8d5649174a` |
| `lineage.sqlite3` | `6b6ce2824f7bf297119642e7f110fbd81da3b6b33827cce650b20f1edf54a74c` |

No credential, authorization header, or unrelated private conversation content
is included. This receipt records the failed run as historical evidence; it
must not be rewritten as a successful P1.1 gate.
