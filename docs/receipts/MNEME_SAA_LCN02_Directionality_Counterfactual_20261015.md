# LCN-02: incoming-edge reachability counterfactual

## Result

**Yes. An earned, positive incoming edge can be eligible for the SAA landing distribution yet absent from propagation solely because production propagation follows edges whose `source` is the current node.** The recorded counterfactual shows how a bounded access traversal could encounter that edge from its target while keeping its stored semantic orientation unchanged. It is a reachability list only; it is not an alternate SAA result, pressure calculation, or proposed production policy.

## Production result: association fixture

Synthetic graph, query `unrelated`, seed `1`, `max_depth=2`, `max_contributors=8`:

```text
e0: landing alpha --supports--> landing bravo
incoming: incoming association concept --associated_with--> landing alpha
outgoing: landing bravo --enables--> outgoing consequence
```

All three edges have positive learner accessibility/support (`e0=900,000`; `incoming=500,000`; `outgoing=500,000`). The actual `FieldResult` lands on `e0`. `incoming` appears in the eligible accessibility distribution, but not in the returned contributions. `outgoing` is returned via path `e0→outgoing`.

The implementation constructs `outgoing[edge.source]` and, from each landing endpoint, examines `outgoing[current_node]`. At `landing alpha`, the incoming edge has source `incoming association concept`, so it is not traversed. No ineligible/quarantine or zero-strength reason explains its absence in this fixture.

## Bounded reachability-only counterfactual

The diagnostic simulator takes the graph, the candidate keys from the actual distribution, the actual landed `e0`, and the same maximum depth. It enumerates eligible outgoing access plus an explicitly labeled `incoming_access_only` step. It does not compute pressure and does not create a `FieldResult`.

For the incoming edge it records:

| Field | Value |
|---|---|
| Stored semantic orientation | incoming association concept →associated_with→ landing alpha |
| Access traversal | landing alpha → incoming association concept |
| Traversal type | `incoming_access_only` |
| Inverse proposition asserted | No |

The existing outward `enables` edge remains outward in both the graph and the counterfactual. The JSON includes full paths, edge identity, depth, and explicit `asserts_inverse_semantics: false` flags. The counterfactual is bounded by the production `max_depth`, eligibility keys from the true distribution, per-path visited nodes/edges, and a diagnostic record cap.

## Why traversal direction cannot be universalized

A second graph has the same landing edge and an outward `prevents` edge, plus two positive incoming edges:

```text
cause_in: incoming causal source --causes--> landing alpha
part_in: part concept --part_of--> landing alpha
```

Production propagation includes the outward `prevents` edge and excludes both incoming edges. The diagnostic access view can reach the source concepts in the opposite navigation direction, but preserves the graph claims as `incoming causal source causes landing alpha` and `part concept is part_of landing alpha`. It does **not** claim that landing alpha causes the source or that landing alpha is part of the source.

The example makes the design issue concrete: accessing the source node through an incoming link is not the same operation as asserting an inverse relation. In particular, universal reverse traversal would be unsafe if downstream code interpreted navigation as proposition direction. Which relationship classes, if any, should support reverse access is an owner-level design question; the existing relation vocabulary is not treated here as defining inverse semantics.

## What this establishes and what it does not

**Observed:** current SAA can leave a positive earned incoming association out of the activated contribution set even though that edge remains eligible in the global lottery. The cause in this controlled fixture is the source-keyed outgoing adjacency traversal. A separate diagnostic traversal reaches the same edge in access-only mode without reversing its semantic fields.

**Not established:** how frequently this happens in real developmental graphs; whether incoming associations should be traversable for all, some, or no relation types; whether changing access would improve or harm selection/pressure behavior; or whether any host would make useful use of such a neighborhood.

No production SAA, projection, field, renderer, persistence, or specimen was changed. The full graph, learner, configuration, actual `FieldResult`, projection, and counterfactual records are in [`saa_lcn02_fixed_landing_traces_20261015.json`](saa_lcn02_fixed_landing_traces_20261015.json). The unavailable archival amendment was not reconstructed or attributed.
