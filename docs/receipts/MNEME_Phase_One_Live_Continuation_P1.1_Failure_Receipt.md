# MNEME Phase One continuation P1.1 live failure receipt

Date: 2026-09-19
Tested code: `09bbf426411f72af7beba6c74bfd16041748f029`
Provider/model: DeepInfra / `google/gemma-4-E4B-it`
Run workspace: `/home/nyx/.local/share/mneme/phase-one-live/20260919-continuation-09bbf42/`

Status: **BLOCKED at P1.1 because the required multi-hop route was not formed**

This was a fresh isolated run after the source-purpose correction. The P1.1
fixture was unchanged. All four dispatched DeepInfra calls returned; no retry,
repair, alias, or replacement run was attempted.

## Call accounting

| Ordinal | Role | Result | Input | Output | Total | Finish |
|---:|---|---|---:|---:|---:|---|
| 1 | developmental response | returned | 23 | 187 | 210 | stop |
| 2 | developmental response | returned | 22 | 192 | 214 | length |
| 3 | extraction initial | returned | 606 | 223 | 829 | stop |
| 4 | extraction initial | returned | 605 | 244 | 849 | stop |
| **Total** |  | **4** | **1,256** | **846** | **2,102** |  |

Known provider cost metadata covers the two extraction calls: `$0.00003442`
and `$0.00003650`. Response-call cost was not persisted, so total cost remains
partially unknown. P1.2 and P1.3 received zero calls.

## Gate disposition

Both developmental responses were accepted exactly once. Both extraction
results passed structural and exact-quotation validation and were published.
The first accepted interpretation supplied the edge
`weather_check --causes--> rain_jacket`. The second supplied supported concepts
including `rain_jacket`, `shower`, and `hike`, but no relationship edge. The
accumulated graph therefore contained only one edge and no directed multi-hop
route. MNEME correctly refused to invent the missing edge or route.

This is a model-output result under the tested fixture, not a provider or
credential failure. The run is preserved as historical evidence and is not a
P1.1 acceptance. No P1.2/P1.3 work was started.

| Artifact | SHA-256 |
|---|---|
| `live_summary.json` | `1ecafed7d4b7a0f2b455b20305a5043e49b219f6ef7b67966665c8b1ac766160` |
| `lineage.sqlite3` | `2825e0a7d838a59754df3775f78d5cd7c615b7ebadc7aec02d0fa6f12313dd70` |

No credentials, authorization headers, or unrelated private conversation data
are included.
