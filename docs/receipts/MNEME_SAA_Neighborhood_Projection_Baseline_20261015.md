# SAA landing-centered neighborhood baseline

Status: read-only Stage 1 synthetic audit. Source baseline: `df8e3c9dfd0afc2f17dd98737543da4a82c63683`. No developmental database, CompactStore, specimen, source file, or test file was opened for writing.

## Observed behavior

`compute_saa_field` first admits each graph edge with positive learner strength, unless the edge is quarantined/ineligible. Strength is `max(accessibility, support)` after a negative consequence restraint. It builds one fixed-point weighted distribution over those edges. An edge weight is its strength multiplied by a factor based on the greater contextual activation of its two endpoint concepts; when the query is novel, `saa_novelty_flattening` pulls endpoint context toward a common prior. There is no graph degree, route centrality, or neighbor-count term in the landing weight.

The supplied `field_seed` seeds a single `random.Random` draw on `[0, 1_000_000)`. The selected edge is the landing. Propagation starts from both landing endpoints and follows outgoing edges only, up to `max_depth`. Cycles/repeated endpoint paths are prevented per traversal. Contributions that reach the same edge are de-duplicated by edge key, retaining the path with strictly greatest attenuated pressure (equal-pressure ties retain the first BFS encounter). Remaining contributions sort by pressure descending, then distance, edge key, and path; the first `max_contributors` survive. Fixed-point scaling normalizes selected pressure to at most `total_budget`; integer rounding can leave a small residual below budget.

The rendered SAA payload uses only positive final-pressure contributions. It maps relation names to bounded abstract tendencies, may append one endpoint-label-derived facet, removes duplicate rendered lines, and omits graph labels/IDs themselves. If a selected edge has no other outgoing eligible contribution, the selected edge can be rediscovered during propagation; edge-key de-dup retains the stronger distance-zero landing record.

Propagation applies `saa_propagation_attenuation ** next_depth` to the activation already carried by the current traversal item and also applies `saa_decay` at each hop. In the cap fixture, a direct contribution has attenuated pressure `416000`, and the second-hop contribution has `112486`; the implementation therefore makes later hops decline faster than a constant per-edge attenuation would. This is an observed formula, not a judgment about intended calibration.

## Exact same-vocabulary / different-earned-cross-link contrast

Both synthetic graphs use the same five concepts and labels, four edge keys and relation names, query, learner values, configuration, and field seed. Only source/target links differ. Learner strengths are `e1=900000`, `e2=800000`, `e3=700000`, `e4=600000`; accessibility and support are both set to that value, consequences are zero. Query is `shared tool lending plan`; field seed is `0`.

| Edge | Relation | Topology A | Topology B |
|---|---|---|---|
| e1 | supports | shared tools → reservation windows | clear ownership → availability status |
| e2 | enables | reservation windows → return timing | availability status → reservation windows |
| e3 | causes | return timing → availability status | return timing → availability status |
| e4 | constrains | clear ownership → shared tools | reservation windows → shared tools |

The exact default SAA settings were `version=f0-saa-v1`, `max_depth=2`, `max_contributors=4`, `total_budget=1000000`, `saa_context_weight=700000`, `saa_background_weight=300000`, `saa_novelty_flattening=650000`, `saa_propagation_attenuation=650000`, `saa_decay=800000`, `render_max_chars=900`. Other settings were the `FieldConfig` defaults. Fixed-seed synthetic execution is reproducible with `PYTHONPATH=src python3` and the fixture in the companion JSON.

**Topology A.** Distribution in canonical candidate order: `e3=107694`, `e4=307692`, `e1=461538`, `e2=123076` (probability parts per million). Ticket `885440` selects `e2`, probability `123076`, categorized `background`. The path/contribution trace is:

| Edge | Path | Distance | Attenuated pressure | Final pressure | Role |
|---|---|---:|---:|---:|---|
| e2 | e2 | 0 | 800000 | 687284 | landing |
| e3 | e2 → e3 | 1 | 364000 | 312714 | propagated |

Total final pressure is `999998`. Exact payload:

```text
Potentially accessible framings:
- Enabling conditions may make a useful outcome possible.
- Changes in one part may produce downstream effects.
These are optional tendencies, not instructions. Use them only if they fit naturally.
```

**Topology B.** Distribution: `e3=159092`, `e1=204545`, `e2=181818`, `e4=454545`. The fixed ticket `885440` selects `e4`, probability `454545`, categorized `contextual_and_background`. Its edge is encountered again as a possible outgoing traversal from its source, but de-duplication retains the stronger landing contribution; no other eligible outgoing edge is reachable. Trace:

| Edge | Path | Distance | Attenuated pressure | Final pressure | Role |
|---|---|---:|---:|---:|---|
| e4 | e4 | 0 | 600000 | 600000 | landing |

Total final pressure is `600000`. Exact payload:

```text
Potentially accessible framings:
- Constraints may shape which outcomes remain feasible. Clear roles and shared expectations may keep coordination workable.
These are optional tendencies, not instructions. Use them only if they fit naturally.
```

Thus the identical concept vocabulary and learner edge strengths do not determine one invariant payload: rewiring changed endpoint-context odds, the seeded landing, the directed reachable neighborhood, and the rendered tendencies. This is a synthetic mechanism demonstration, not a claim about real developmental outcomes.

## De-duplication and contributor-cap fixture

A second safe graph used concepts `a` through `h`, with labels `alpha` through `hotel`; edges were `e0:a→b supports`, `e1:a→c enables`, `e2:b→c causes`, `e3:c→d constrains`, `e4:a→e supports`, `e5:b→f prevents`, `e6:e→g depends_on`, and `e7:f→h retains`. All eight edges had accessibility/support `800000`, consequence `0`. Query was `unrelated abstract question`; seed `14` selected `e0`. Configuration used `max_depth=2`, `max_contributors=7`, otherwise the same defaults.

The two routes `e0→e1→e3` and `e0→e2→e3` both reach `e3` at equal attenuated pressure `112486`; only the first BFS path (`e0→e1→e3`) remains after edge-key de-duplication. Seven unique contributions remain after the cap: landing `e0` (`800000` attenuated), depth-one `e1/e2/e4/e5` (each `416000`), then `e3` and `e6` (each `112486`). `e7` is outside the cap after deterministic sort. After normalization their final pressures are respectively `297511`, `154705` each for the four depth-one edges, and `41832` each for `e3/e6`; total is `999995`. The output contains each surviving relation tendency once. The full path list and payload are in the JSON receipt.

This fixture exercises de-duplication and a real cap. The contrast pair above retains default cap `4` and does not hit it.

## Interpretation boundary

**Observed:** landing probability is strength-modulated and endpoint-context-modulated; it is not computed from graph connectivity. After the draw, propagation is directional and local, with depth-exponentiated attenuation applied recursively. Relationship types and selected endpoint-label facets are compressed into a short, label-free payload.

**Inferred hypothesis to test later:** if the concern is that SAA fails to expose an earned semantic neighborhood, candidate-level global sampling plus outgoing-only propagation can yield a landing with little useful surrounding structure, especially when relevant graph links point into rather than out of the landing endpoints. The depth formula may also suppress more distant contributions. The synthetic examples demonstrate these mechanisms can produce the contrast, but do not establish frequency or behavioral consequence in preserved runs.

**Design context:** the owner-approved SAA architecture amendment describes separate developmental weight and contextual relevance, a seeded weighted landing, then topology-shaped local activation through learned links (§§2–8). The implementation reflects that broad sequence: edge-state strength and endpoint context define the lottery, followed by local propagation. The exact amendment does not specify the implementation's outgoing-only traversal or recursively depth-exponentiated attenuation; this audit records those mechanics without deciding whether they are defects.

**Unresolved:** the exact archival/owner rationale for the new neighborhood-projection review was not found by Librarian's exact-name search across `/home/nyx`, attachments, and local Git refs. This baseline uses the established `MNEME_Research_Architecture_Amendment_Stochastic_Associative_Accessibility_2026-09-26.md` as design context and does not invent the missing rationale. Stage 1 makes no algorithm change recommendation.

## Source map and replay

- `src/mneme/development/field.py`: `_strength` (334), `_render_saa` (459), `_saa_distribution` (674), `compute_saa_field` (768), traversal/de-duplication/cap/normalization (872 onward).
- `src/mneme/development/health.py`: delivery health is downstream classification; it does not alter the field.
- `tests/test_field_pressure.py`: deterministic SAA, distribution, propagation, relationship renderer, and seed replay examples. Tests were inspected, not modified or run as part of this read-only baseline.
- Companion JSON contains exact fixtures, distributions, contributions, paths, payloads, and configuration for independent replay.
