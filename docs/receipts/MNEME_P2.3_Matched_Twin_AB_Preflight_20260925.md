# MNEME P2.3 Matched-Twin A/B Preflight — 2026-09-25

Status: **BLOCKED_READOUT_ROUTE_BOUND**.

The specialist reinterpretation created a derived state with one positive
external-supported canonical learner edge (`garden` → `paint project`) and
several echo/unknown or non-credited edges. The current approved controller
uses the deterministic graph bound `max_routes=8`. Repeated retrospective
interpretations materialized collision-safe variants of earlier local edge
keys; those variants occupy the first eight deterministic route slots. The
positive garden → paint-project edge is therefore absent from the route set
before query coverage is applied.

The normal controller was audited with four frozen novel probes and matched M
(learned graph memory) / C (memory off) requests. M selected zero routes for
every probe; C selected zero routes as required. Running local Gemma calls
under these requests would test two identical readout conditions and could not
answer the authorized A/B question. No local or hosted provider call was made
for this preflight.

The collision-safe learner-key alias correction is committed at
`e98f0bc42abede911a246e6e96c5781545380697`; it correctly maps materialized
variants to their canonical learner key, but that mapping does not remove
route-slot crowding. Historical P2.3, v5, and retrospective evidence remains
unchanged. A future bounded correction must preserve the route bound while
preventing duplicate collision variants from consuming the bounded route set,
or otherwise establish a normal-path readout that genuinely carries the
positive learner edge. Until then, no matched-twin A/B result is scientifically
interpretable.

Machine-readable request and route audit: [JSON](MNEME_P2.3_Matched_Twin_AB_Preflight_20260925.json).
