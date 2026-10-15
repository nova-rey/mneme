# LCN-02: fixed-landing topology comparison

## Result

**Yes. Holding the selected landing at `e0`, different earned surrounding links produce different directed projected neighborhoods.** In the controlled pair, the distribution is identical by edge key, the seed and ticket are identical, and the actual `compute_saa_field` result selects `e0` for both graphs. Only non-landing edge endpoints `e2` and `e4` change. The projection preserves those changed paths. The legacy rendered payload does not distinguish the two graphs: it is byte-identical in both.

This is a synthetic, model-free mechanism test. It does not show that a host uses the projection or that any developmental specimen has this topology.

## Provenance and fixed conditions

- Package: `SAA-LCN02-FIXED-LANDING`.
- Source base: `45e251f368f5d1986d6027c484cdf61e7344b61c`.
- SAA: `f0-saa-v1`; query `unfamiliar abstract question`; `FieldConfig(max_depth=3, max_contributors=12)` with other values at defaults; learner values and complete graph are in the machine-readable trace.
- Both histories have the same 10 concept keys/labels, six edge keys and relationship names, learner values, query, and field seed. `e0`, `e1`, and `e3` are identical. Only `e2` and `e4` are rewired.
- A bounded exploratory seed scan tested seeds 0–5. The two graphs selected the same edge under each of the six seeds because their edge-keyed distributions match. Seed 1 was selected as the first scanned seed where both actually landed on the required `e0`; seeds 3 and 4 also landed on `e0`. This selection conditioning is disclosed. The scan is not evidence of landing frequency beyond these six synthetic draws.
- `e0` is `shared tools --supports--> reservation windows` in both histories.

The matching distribution (probability parts per million, keyed by candidate) is:

| Candidate | e0 | e1 | e2 | e3 | e4 | remote |
|---|---:|---:|---:|---:|---:|---:|
| Probability | 272,728 | 212,121 | 181,818 | 151,515 | 121,212 | 60,606 |

For seed 1, the actual RNG ticket is `140891`, and both `FieldResult` objects select `e0` at 272,728 ppm. The distribution is exactly the same by key in A and B. This isolates neighborhood topology from both a changed distribution and a changed landing.

## Fixed landing, different earned ropes

| Edge | History A | History B | Changed? |
|---|---|---|---|
| e0 | shared tools →supports→ reservation windows | same | No; selected landing |
| e1 | reservation windows →enables→ return timing | same | No; shared local link |
| e2 | return timing →causes→ availability status | return timing →causes→ maintenance | Yes |
| e3 | reservation windows →constrains→ clear ownership | same | No; shared local link |
| e4 | clear ownership →supports→ maintenance | clear ownership →supports→ availability status | Yes |
| remote | garden planning →associated_with→ seasonal planting | same | No; disconnected control edge |

Actual returned contributions, before normalization / after normalization, are the same numerically in each history because relation names, strengths, depth, and local path lengths match. The endpoints differ where the rewiring occurs.

| Contribution | History A path and directed edge | History B path and directed edge | Attenuated pressure | Final pressure |
|---|---|---|---:|---:|
| e0 | e0: shared tools →supports→ reservation windows | same | 900,000 | 551,142 |
| e1 | e0→e1: reservation windows →enables→ return timing | same | 364,000 | 222,906 |
| e3 | e0→e3: reservation windows →constrains→ clear ownership | same | 260,000 | 159,218 |
| e2 | e0→e1→e2: return timing →causes→ availability status | return timing →causes→ maintenance | 73,819 | 45,205 |
| e4 | e0→e3→e4: clear ownership →supports→ maintenance | clear ownership →supports→ availability status | 35,152 | 21,526 |

The projection therefore contains the same edge keys and route shape but different reached nodes and different edge endpoints for `e2` and `e4`. The opt-in synthetic descriptor records those actual directed relations. The projection does not invent a bridge or search beyond the contributions in the `FieldResult`.

The legacy payload is exactly the same in both histories:

```text
Potentially accessible framings:
- Supporting structures may keep important functions available. Clear roles and shared expectations may keep coordination workable.
- Enabling conditions may make a useful outcome possible.
- Constraints may shape which outcomes remain feasible.
- Changes in one part may produce downstream effects.
- Supporting structures may keep important functions available.
These are optional tendencies, not instructions. Use them only if they fit naturally.
```

Thus in this fixture, topology survives in the audit projection and synthetic descriptor, but not in the default renderer's text. The default renderer still exposes relation tendencies and one label-derived facet; it loses the exact endpoint and path identity that separates A from B.

## Disconnected-edge control

The control compares History A with a graph where only the remote edge target changes from `y` (seasonal planting) to `z` (community workshop). That edge remains disconnected from both `e0` endpoints and all reached local nodes. The query, seed, edge key, relation, learner strength, and concept inventory stay fixed.

Observed results: the edge-keyed distribution is unchanged, the landing remains `e0`, and the complete projection audit is identical. The remote edge remains an eligible lottery candidate but does not enter the selected local neighborhood. This distinguishes global candidate eligibility from local reachability.

## Caps, raw paths, and what this API exposes

The contrast fixture has no contributor-cap loss. For the cap/de-dup check, this report reuses the LCN-01 synthetic fixture and re-runs it against the current source. Candidate `e7` has a nonzero distribution probability (125,000 ppm), but it is absent from the returned contribution set after the `max_contributors=7` cap; it is also absent from the projection. The projection is a view of supplied contributions and does not recover `e7`.

LCN-01's preserved trace records two equal-pressure pre-dedup routes to `e3`: `e0→e1→e3` and `e0→e2→e3`. Existing SAA de-duplicates by edge key and preserves the first BFS path, so the current `FieldResult` exposes only `e0→e1→e3`; the projection preserves that one path and cannot reconstruct the other. The `FieldResult` API does not expose the raw pre-dedup propagation list; the two-path witness is attributed to the earlier LCN-01 receipt, not presented as a newly visible field trace.

With the existing recursive depth exponent, the cap fixture's pressure is 416,000 at depth one and 112,486 at depth two, before budget normalization. This is the observed implementation formula and its result, not a conclusion that the formula is defective.

## Conclusion and limits

1. **Fixed landing:** yes. The actual landed edge is `e0` in both; only earned surrounding topology changes; the projected directed endpoints differ.
2. **Default renderer:** it collapses the distinction in this fixture: A and B produce byte-identical text even though their projections have different endpoint relations.
3. **Other losses:** outgoing-only traversal can make an incoming eligible edge unreachable; de-dup removes alternate routes to the same edge; recursive attenuation lowers later-hop pressure; the contributor cap can remove a candidate path before projection. These are separate stages.
4. **Possible later question, not a change here:** whether some explicitly chosen association relations may permit reverse *access* while retaining original source→target semantics. This evidence does not authorize a relation policy or a production behavior change.
5. **Unproven:** prevalence in developmental graphs, any effect on Gemma/host behavior, and whether retaining path structure improves cognition.

The original 2026-10-15 landing-centered archival amendment was unavailable in the supplied environment. It was not copied, reconstructed, or paraphrased. This receipt records only the uploaded LCN-02 brief, the existing September SAA amendments, and direct code/test behavior.

## Reproduction

From the repository root:

```bash
PYTHONPATH=src python3 tools/saa_lcn02_counterfactuals.py \
  --output docs/receipts/saa_lcn02_fixed_landing_traces_20261015.json
```

The JSON retains graph and learner values, configuration, actual serialized field results, projection views, seed scan, and provenance notes. No model, host, persisted specimen, or CompactStore was used.
