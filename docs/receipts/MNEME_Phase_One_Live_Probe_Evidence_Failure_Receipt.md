# MNEME Phase One probe-evidence live failure receipt

Date: 2026-09-20
Tested code: `8be338e6cbf4a89c1d6c89fe7ea94bfa441a1b8d`
Provider/model: DeepInfra / `google/gemma-4-E4B-it`
Run workspace: `/home/nyx/.local/share/mneme/phase-one-live/20260920-probe-evidence-8be338e/`

Status: **P1.1 passed; P1.2 stopped at name comparison**

This run was authorized to preserve the previously missing frozen-probe
output. It dispatched ten calls; all returned. No retry or replacement sample
was made.

## Call accounting

| Gate | Calls | Input | Output | Total |
|---|---:|---:|---:|---:|
| P1.1 | 4 | 1,256 | 842 | 2,098 |
| P1.2 | 6 | 1,738 | 380 | 2,118 |
| **Total** | **10** | **2,994** | **1,222** | **4,216** |

Known provider cost metadata totals `$0.00010560` for persisted extraction
attempts. Other call costs were unavailable, so total cost is partially
unknown. P1.3 received zero calls.

## P1.1

P1.1 passed with two accepted source-backed edges and a deterministic route:

```text
weather_check → rain_jacket → shower
```

## P1.2

Naming durably adopted `Gemma4`. The relevant response was accepted and route
influence was traced. Both external-evidence-only interpretation calls were
valid empty residues. Correction suppression and checkpoint immutability were
verified up to the cold-start probe.

The frozen probe returned the exact text `Gemma 4`. The runner compared it to
the stored spelling `Gemma4` using a strict substring check and rejected the
probe. This is a deterministic formatting mismatch in the acceptance
implementation; the model recovered the adopted name semantically. The
remediation accepts case-insensitive token adjacency across display spacing or
punctuation while still rejecting distinct names such as `Gemma 40`.

## Private artifacts

| Artifact | SHA-256 |
|---|---|
| `live_summary.json` | `64bc9a0b9039d32663c0b180fdacb859d45dad0eb12d36e508cbd773f5897133` |
| `lineage.sqlite3` | `8fee362f14f06190440bab2b0966e4b67cef7c5bbfd62aabca2d9e2713d30e63` |

No credentials, authorization headers, or unrelated private conversation data
are included. P1.1 remains accepted for this run; P1.2 and P1.3 remain
unaccepted until rerun against the deterministic comparison correction.
