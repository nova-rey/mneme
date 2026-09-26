# MNEME P2.3 Treatment-Delivery Preflight — 2026-09-26

Status: **PASSED — instrumentation only**

This receipt validates the repaired route-selection and treatment-construction
plumbing against a deterministic synthetic learner state. It is not live
scientific evidence and is not a behavioral result.

## Historical diagnosis

The preserved r6 run remains `INVALID_NO_TREATMENT`. Extraction, local
DeBERTa assessment, canonical admission, and learner state formation all
succeeded. The admitted learned edge was `Drip Irrigation → causes → Slow
Leak`, but route query coverage used `_phrase()`'s exact contiguous token
match. At coordinate `A:2`, the current input contained `drip method`; the
route therefore disappeared at **query-coverage/retrieval**, before route
eligibility selection, note construction, or host application. No historical
receipt was changed.

## Correction

Commit `fb3520bd4681e90ad979d1211aa6abaadc463d57` retains exact phrase
matching as the fast path and adds a bounded lexical reachability rule. A
query must share a non-empty content token with the canonical label; any
query-only tokens must be from the small generic descriptor vocabulary. This
allows ordinary phrasing such as `drip method` to reach `Drip Irrigation`
without creating an alias, changing canonical labels, or permitting
unrestricted fuzzy retrieval. `drip coffee` remains unreachable.

## Preflight trace

The synthetic store contained an admitted two-edge graph and a positive
learner observation. The fixed query was `alpha method omega`; the graph
labels were `alpha`, `bridge`, and `omega`.

| Stage | Result |
|---|---|
| eligible learned state | true; one admitted observation and positive learner values |
| current input/query | `alpha method omega` |
| candidate graph retrieval | three bounded graph routes considered; the two-edge route had coverage 2 |
| eligibility filtering | eligible routes retained |
| learned selection | 2 routes selected, including the two-edge route |
| memory/note construction | non-empty `Memory data:` payload constructed |
| treatment application | `applied == selected`, 2 routes applied to the synthetic treatment host |
| control behavior | not part of this synthetic store; production control remains configured with zero MNEME influence |

The regression suite also checks the exact target case (`drip method`), an
exact label, a generic descriptor (`drip system`), unrelated overlap
(`drip coffee`), and an unrelated query. The rule is retrieval-only: source
grounding, canonical resolution, provenance, learner eligibility, route
permissions, and application remain unchanged.

## Scope and evidence boundary

No provider call was made for this preflight. The r6 DeepInfra and local-host
receipts remain historical evidence. This artifact only proves that a known
eligible state can now reach route selection and produce a non-empty applied
payload before the next prospective A/B run.

