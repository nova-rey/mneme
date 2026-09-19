# MNEME Phase One collision-fixed live run receipt

Date: 2026-09-20
Tested code: `8465d4e065176bfff7ca6dadf4e7fb8f556194c8`
Provider/model: DeepInfra / `google/gemma-4-E4B-it`
Run workspace: `/home/nyx/.local/share/mneme/phase-one-live/20260920-collision-fixed-8465d4e/`

Status: **P1.1 passed; P1.2 stopped after its permitted extraction repair**

## Call accounting

| Ordinals | Gate | Roles | Calls | Input | Output | Total |
|---:|---|---|---:|---:|---:|---:|
| 1–4 | P1.1 | responses, extraction | 4 | 1,256 | 846 | 2,102 |
| 5–8 | P1.2 | naming, response, extraction, repair | 4 | 1,843 | 1,558 | 3,401 |
| **Total** |  |  | **8** | **3,099** | **2,404** | **5,503** |

Known provider cost metadata totals `$0.00024084` for the four extraction
attempts. Response and naming cost metadata was unavailable, so total cost is
partially unknown. No P1.3 calls were dispatched.

## P1.1

P1.1 passed. The two natural developmental examples published two directed
edges despite both residues using local key `e1`; collision-safe publication
retained both as `e1` and `e1~26c3984d45ec3eec`. Deterministic route discovery
formed the two-edge route:

```text
weather_check → rain_jacket → shower
```

Route provenance contains evidence from both interpretations. Restart retry
left accepted generation counts unchanged.

## P1.2 failure

Naming returned and was durably recorded. The relevant developmental response
was accepted and route influence was traced. Its initial extraction and one
permitted repair both returned provider results, but strict exact-quotation
validation rejected unsupported evidence quotations from the model-output
source:

```text
initial: residue.core_concepts[6].evidence[0]: evidence quotation does not occur verbatim in source
repair:  residue.core_concepts[3].evidence[0]: evidence quotation does not occur verbatim in source
```

No P1.2 interpretation was published after the repair failure. P1.3 was not
attempted. This is a model-output/provenance-validation failure, not a
provider or credential failure. The next offline correction will keep the
host response durably recorded while preventing it from being treated as
independent developmental evidence for live extraction.

## Private artifacts

| Artifact | SHA-256 |
|---|---|
| `live_summary.json` | `d4173bcda9f34fac20239e94a114cab6e5cc6cb839420c50a1202d2b73c99eaa` |
| `lineage.sqlite3` | `e21193e9b9bfcc4180bc511ce4142b9bc737fdf117e25ea593f6a1cfea17d831` |

No credentials, authorization headers, or unrelated private conversation data
are included. This receipt preserves the run and does not retroactively alter
its P1.1/P1.2 dispositions.
