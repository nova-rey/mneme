# MNEME P2 extractor relationship normalization addendum

- Date: 2026-09-24
- Status: active in-scope correction
- Contract: `residue-v4` with `relationship-normalization-v1`

The preserved `extraction-s1-e7` source says:

> After another hot day, the mulched bed still held moisture for the seedlings.

Gemma's residue used `holds` for the mulched bed → moisture edge and used
`supports` separately for moisture → seedlings. In this context `holds` means
physical retention/containment of moisture. It is not equivalent to `supports`,
`causes`, or `part-of`, and the approved vocabulary previously had no neutral
retention relation.

The smallest defensible correction is therefore a prospective canonical
`retains` relationship plus the deterministic extraction-boundary alias
`holds` → `retains`. The raw extractor result remains immutable and retains the
original label; the normalized residue and the alias decision are recorded
separately. This does not add a synonym dictionary or ask the model to learn a
preferred spelling.

An edge with another unsupported relationship label, or a keyed edge whose
endpoints do not name declared concepts, is rejected at item level.
Independently valid concepts and edges remain eligible, and any route that
depends on the rejected edge is rejected as well. Missing stable keys,
malformed concept collections, unsupported concepts, invalid evidence, and
other structural errors remain fail-closed. No replacement edge is invented,
and no semantic-review provider call is used for this deterministic boundary.

The normalization is versioned as `relationship-normalization-v1` and is
replayable. The extraction artifact exposes the raw provider result,
normalization decisions, rejected items, and normalized residue. Historical
pilot operations and receipts are unchanged.
