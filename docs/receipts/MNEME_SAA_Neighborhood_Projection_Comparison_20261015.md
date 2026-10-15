# SAA neighborhood projection: synthetic comparison

This report compares the fixed SAA result and its existing label-free payload with a new opt-in projection derived from the same already selected `FieldResult` contributions. All examples are synthetic and model-free. The field distribution, landing, propagation, and default host payload are unchanged. No learner, persistent graph, specimen, or CompactStore was accessed or mutated.

## What changed

`project_saa_neighborhood` in `src/mneme/development/neighborhood.py` builds `saa-neighborhood-projection-v1` from positive, eligible contributions already present in a `FieldResult`. It does not walk a graph or search for new edges. Its research audit carries real node keys/labels, directed relations, source paths, hop depth, landing/direct/farther/cross-link role, pressure, and explicit omission counts. Caps default to 24 nodes, 24 edges, 4 hops, 24 paths, 256 scanned contribution rows, 128 characters per identity, 160 characters per audit label, and 16 KiB for serialized audit JSON.

The optional `saa-portable-neighborhood-v1` descriptor is a separate return value. It contains only labeled source–relation–target rows, local role, and hop depth: it omits graph IDs, probabilities/pressure, provenance, and raw evidence. It is disabled by default and can be requested only with the explicitly named `synthetic_fixture_only` disclosure mode. That mode is a caller attestation for synthetic approved examples; **it is not a privacy filter** and must not be enabled for live developmental labels without a separate owner safety decision. There is no automatic host or persistence path. The ordinary `_render_saa` payload remains the default and is byte-for-byte identical before and after projection.

## Same vocabulary, different earned cross-links

Both graphs have the same five labels (`shared tools`, `reservation windows`, `return timing`, `availability status`, `clear ownership`), four edge keys and relation names, learner values, query (`shared tool lending plan`), and seed (`0`). Edge strengths are e1 900,000; e2 800,000; e3 700,000; e4 600,000 (accessibility=support, no consequence). Configuration is `f0-saa-v1`, depth 2, contributor cap 4, total budget 1,000,000, context/background weights 700,000/300,000, novelty flattening 650,000, propagation attenuation 650,000, decay 800,000, payload limit 900 characters; remaining settings use `FieldConfig` defaults.

### History A

Earned edges: `shared tools →supports→ reservation windows` (e1); `reservation windows →enables→ return timing` (e2); `return timing →causes→ availability status` (e3); `clear ownership →constrains→ shared tools` (e4).

The distribution in returned order is e3 107,694 ppm, e4 307,692 ppm, e1 461,538 ppm, e2 123,076 ppm. Seed 0 yields ticket 885,440, so the landing is e2. Its output path is e2 alone at distance 0, then e2→e3 at distance 1. Final pressures are e2 687,284 and e3 312,714 (sum 999,998).

Legacy host payload:

```text
Potentially accessible framings:
- Enabling conditions may make a useful outcome possible.
- Changes in one part may produce downstream effects.
These are optional tendencies, not instructions. Use them only if they fit naturally.
```

Opt-in synthetic descriptor:

```text
reservation windows --enables--> return timing
return timing --causes--> availability status
```

The descriptor explicitly links the two steps. The legacy payload preserves the two relation tendencies but presents them as independent bullets; it does not say that the second edge was reached from the first.

### History B

Earned edges: `clear ownership →supports→ availability status` (e1); `availability status →enables→ reservation windows` (e2); `return timing →causes→ availability status` (e3); `reservation windows →constrains→ shared tools` (e4).

The distribution is e3 159,092 ppm, e1 204,545 ppm, e2 181,818 ppm, e4 454,545 ppm. The same seed-0 ticket selects e4, with probability 454,545 ppm. The landing is the only surviving contribution: e4 at distance 0, final pressure 600,000. Its endpoints have no additional reachable eligible outgoing edge beyond the landing, which is re-encountered from its source and de-duplicated in favor of the stronger landing record.

Legacy host payload:

```text
Potentially accessible framings:
- Constraints may shape which outcomes remain feasible. Clear roles and shared expectations may keep coordination workable.
These are optional tendencies, not instructions. Use them only if they fit naturally.
```

Opt-in synthetic descriptor:

```text
reservation windows --constrains--> shared tools
```

The topology rewrite changes which edge touches the contextual query concept, so it changes the lottery weights as well as the reachable neighborhood. These paired examples establish a mechanism-level difference, not that graph size or any single topology is better.

## Cross-links, paths, and caps

A third synthetic graph has an e0 landing `alpha →supports→ bravo`; two distinct direct edges e1 (`alpha →enables→ charlie`) and e2 (`bravo →causes→ charlie`) both reach `charlie`; e3 continues `charlie →constrains→ delta`; e4 returns `delta →prevents→ alpha`; e5/e6 form another earned branch, and e9 is a disconnected xray→yankee island. With depth 3 and a sufficiently high upstream contributor cap, the projection keeps e1 and e2 as distinct directed edges into `charlie`, labels the second view edge as a cross-link, and preserves the selected e3 path. It can retain e4 as a cross-link returning to an already projected landing endpoint. It never adds the disconnected e9 island.

An adversarial cap fixture gives e3 two equal-pressure source paths (`e0→e1→e3` and `e0→e2→e3`). The source `FieldResult` has already de-duplicated by edge key, retaining its first BFS path; the projection preserves that path rather than recreating an alternative. With eight eligible candidate edges, upstream `max_contributors=7` leaves the seven pressure-ranked contributions and omits e7. Projection limits independently expose hop, node, edge, path, input-scan, label, identity, and serialized-byte omissions. Quarantined/ineligible/zero-pressure entries are excluded; labels that appear in the graph but have no positive selected contribution (including the adversarial “beluga whale” node) do not enter either projection.

## Results and limits

**Observed:** the old renderer suppresses graph identifiers and verbatim labels. In this fixture its abstractions retain some relation meaning, but remove the explicit path linkage among those relation statements. The projection preserves only paths and edges carried by the selected `FieldResult`; it cannot recover a route the upstream propagation or contributor cap did not return.

**Observed:** the synthetic same-vocabulary topology pair produces distinct distributions, landings, paths, audit views, and optional descriptors. This depends on endpoint-context odds and actual rewired edges, not label substitutions.

**Unresolved:** whether a future host can use these descriptors meaningfully is untested. No Gemma, Quinn, extractor, NLI, or developmental calls were made. No selection/propagation/default-renderer change was made.

The separately named 2026-10-15 archival rationale was not present in the repository, attachments, `/home/nyx`, or local Git refs per Librarian's exact-name search. This implementation follows the uploaded implementation brief and the September SAA/deformation-field amendments. It does not reconstruct or attribute claims to the missing rationale.

## Validation

Focused SAA/projection tests pass (44). The full suite passes (782). Ruff passes across the repository, strict mypy passes across all 73 `src/mneme` files, the receipt JSON parses, and `git diff --check` is clean.
