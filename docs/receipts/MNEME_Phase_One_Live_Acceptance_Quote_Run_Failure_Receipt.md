# MNEME Phase One live acceptance — corrected quotation-contract run

Date: 2026-09-19  
Tested code: `ede9d3f2f639fbac5be7d85aa48edd2dc1816b45`  
Status: **P1.1 BLOCKED — PRESERVED FAILURE**

This receipt records the first bounded live run after the extractor quotation
remediation. It is new evidence and does not alter the historical 18-call or
four-call failure receipts.

DeepInfra successfully returned all four dispatched results for
`google/gemma-4-E4B-it`. The credential and transport were functional. The
run stopped at P1.1 before any P1.2 or P1.3 call, as required, because the
required route demonstration was not satisfied.

## Call accounting

| Ordinal | Gate | Role | Result | Structural/source validation | Usage |
|---:|---|---|---|---|---:|
| 1 | P1.1 | response | returned | accepted as episode | 16 in / 192 out / 208 total |
| 2 | P1.1 | response | returned | accepted as episode | 17 in / 192 out / 209 total |
| 3 | P1.1 | extraction initial | returned | valid quotation-backed residue | 709 in / 181 out / 890 total |
| 4 | P1.1 | extraction initial | returned | valid quotation-backed residue | 710 in / 176 out / 886 total |

No repair call was dispatched. No transport failure occurred. The run consumed
4 of the 27-call ceiling and stopped without sampling again for a preferred
result.

## Gate decision

Both extraction results contained source-valid concepts and a supported
`constrains` relationship. Neither result contained a `route_candidates`
record, so the materialized graph contained three edges and zero routes. The
approved P1.1 criterion requires at least one reviewed supported relationship
and route among the source/residue examples. P1.1 therefore remains failed;
P1.2 and P1.3 were not attempted.

The follow-up offline correction makes the model-facing prompt explicitly say
that a supported edge must be accompanied by a route candidate. It does not
weaken validation or acceptance criteria. No additional live call was made
after this failure.

Private audit artifacts are retained outside Git. Sanitized digests are:

- working lineage SQLite: `95e32477722cb6a78362d1dd8e1baef18d4c34c7892bd47e9446c85ff92478aa`
- live summary: `defc75a345881b4581cb767822906423d79df9dce873460e1b6cc67a0d239d5a`

The remaining live allowance is 23 calls from this authorization, but the
approved stop rule requires new authorization before another live attempt after
a failed required result. Phase One is not complete and no release tag was
created.

