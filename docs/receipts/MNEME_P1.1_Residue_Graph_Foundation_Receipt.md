# MNEME P1.1 Residue-to-Graph Foundation Receipt

Date: 2026-09-19
Base: `48d70210d416572d52bfe833b788ff3603af6492`
Package: `P1.1`

P1.1 establishes the Phase One interpretation boundary without adding response
influence, retrieval, identity, or adaptive learning. The accepted episode is
durable first; extraction is a separate host operation with persisted request
and result, one explicit repair allowance, fail-closed uncertainty handling,
source-slot validation, and atomic graph publication.

The package includes the narrow prior-layer repairs required by the approved
plan: DeepInfra forwards a separate system instruction exactly once and rejects
unsupported native structured output; prepared host fingerprints are checked
before dispatch; accepted-history digests retain ancestry-ordered content while
excluding administrative identifiers; source bindings distinguish external
evidence, replayed context, controller dependencies, and model output; hard
budget limits remain distinct from estimates; checkpoint forks stage and migrate
privately; and read-only checkpoint history follows root-to-child ancestry.

Residues are bounded and source-backed. Invalid fields, fabricated slots,
invalid Unicode spans, malformed routes, non-finite or boolean numeric values,
and oversized payloads are rejected without graph publication. Exact normalized
resolution decisions are persisted with provenance; explicit alias or ambiguity
decisions may be supplied and are immutable. Complete graph snapshots are
materialized transactionally, with stale-base rejection and idempotent retry.

The Phase One development opt-in is explicit at creation:
`mneme instance create --development-enabled`. Stores created without it and
migrated legacy stores have interpretation disabled by default. P0.2 storage
and export permissions remain separate from this Phase One opt-in.

Validation performed at this gate:

- `.venv2/bin/pytest -q`: **138 passed**
- `.venv2/bin/ruff check src tests`: **passed**
- `.venv2/bin/mypy --strict src`: **passed** (31 source files)
- `git diff --check`: **passed**
- `work-queue validate`: **valid**
- Offline integrated FakeHost demonstration: accepted episode at lineage
  revision 1, accepted interpretation at revision 2, graph revision 1,
  restart verification passed, checkpoint fork verification passed, and the
  inherited checkpoint exposed two ordered history transitions. The bounded
  fixture made two host calls (development response and interpretation).
- Adversarial coverage includes invalid residue and repair limits, uncertain
  provider recovery without automatic retry, stale publication, duplicate
  publication, host drift, schema migration, fork staging, inherited-history
  ordering, cache key invalidation/rebinding, and explicit permission denial.

No network or paid model call was needed for this foundation gate. Real-host
extraction remains a later, explicitly budgeted acceptance action. P1.2 response
influence and identity work has not started.
