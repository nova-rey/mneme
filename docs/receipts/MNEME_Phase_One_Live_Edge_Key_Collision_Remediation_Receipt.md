# MNEME Phase One edge-key collision remediation receipt

Date: 2026-09-19
Observed run: `20260919-continuation-09bbf42`
Remediation code: working tree after tested `895a421`

The continuation run's persisted extraction results contained two valid
source-backed relationships. Both model residues used the interpretation-local
edge key `e1`. The first publication stored `e1`; the second publication copied
the prior snapshot and then silently skipped the colliding incoming `e1`.
Consequently the second edge was absent from the latest graph snapshot and the
required route was not formed. This was an infrastructure/publication defect,
not a provider or credential failure and not a reason to weaken the acceptance
criterion.

The remediation assigns deterministic collision-safe keys to incoming graph
edges and explicit routes when their interpretation-local keys collide with
existing snapshot rows. The suffix is derived from relationship content and
source evidence, contains no administrative identifier, preserves local-key
provenance in annotations, remaps explicit route references, and leaves the
bounded directed route search unchanged.

Regression coverage proves that two accepted interpretations reusing `e1`
retain both directed edges and produce a two-edge route with both provenance
records. Existing route bounds, directionality, eligibility, and insertion
independence tests remain active.

No provider call was made for this remediation. The observed private artifacts
remain unchanged outside Git:

- `live_summary.json` SHA-256: `1ecafed7d4b7a0f2b455b20305a5043e49b219f6ef7b67966665c8b1ac766160`
- `lineage.sqlite3` SHA-256: `2825e0a7d838a59754df3775f78d5cd7c615b7ebadc7aec02d0fa6f12313dd70`
