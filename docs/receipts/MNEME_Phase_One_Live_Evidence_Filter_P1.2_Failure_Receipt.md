# MNEME Phase One evidence-filtered live run receipt

Date: 2026-09-20
Tested code: `7732449a6cc213c00fce6ba2366b66cd6972e008`
Provider/model: DeepInfra / `google/gemma-4-E4B-it`
Run workspace: `/home/nyx/.local/share/mneme/phase-one-live/20260920-evidence-filter-7732449/`

Status: **P1.1 passed; P1.2 stopped at cold-start identity recovery**

## Call accounting

| Gate | Calls | Input | Output | Total |
|---|---:|---:|---:|---:|
| P1.1 | 4 | 1,256 | 842 | 2,098 |
| P1.2 | 6 | 1,737 | 420 | 2,157 |
| **Total** | **10** | **2,993** | **1,262** | **4,255** |

Known provider cost metadata totals `$0.00010470` for persisted extraction
attempts. Response, naming, and frozen-probe cost metadata was unavailable, so
total cost is partially unknown. P1.3 received zero calls.

## P1.1 evidence

P1.1 passed. The two source-backed relationships were retained even though the
model used local key `e1` for both. Collision-safe publication produced a
lineage-safe second key and deterministic route discovery formed:

```text
weather_check → rain_jacket → shower
```

The route contained provenance from both developmental interpretations, and the
accepted retry/reopen check left generation counts unchanged.

## P1.2 disposition

The naming call durably adopted `Gemma4`. The relevant response was accepted,
its route payload was traced, correction suppression was observed, and both
external-evidence-only interpretations completed as valid empty residues. The
run then created a frozen checkpoint and dispatched a cold-start name probe.
The probe result did not contain the adopted name, so the required P1.2
criterion failed and execution stopped before the unrelated-abstention check
and P1.3.

The prior runner persisted the probe hash and checkpoint invariance evidence but
did not persist the probe text in the partial failure report. That is an
instrumentation defect, not evidence that the provider was unavailable. The
remediation in the next code commit records partial P1.2 progress and the
sanitized cold-start output before applying the assertion, so future failures
remain directly reviewable. No retry or replacement sampling was made from
this run.

## Private artifacts

| Artifact | SHA-256 |
|---|---|
| `live_summary.json` | `91b7ad9fe6d67edecb5186f9c06eeb050f67159af610bf0991066988eec96161` |
| `lineage.sqlite3` | `3b317d90304bc911816a0c6fcb722ff8e74788b0844e07b80a366b6ffb32a9ba` |

No credentials, authorization headers, or unrelated private conversation data
are included. P1.1 is accepted for this run; P1.2 and P1.3 remain unaccepted.
