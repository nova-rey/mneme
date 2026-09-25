# MNEME Phase Two modeled temporal advance correction

Date: 2026-09-25
Status: OFFLINE VALIDATED; no provider calls

## Change

The approved Phase Two plan exposes `mneme --store STORE learner advance
--context CONTEXT --steps N`, but the dispatch path previously stopped with a
placeholder error. The command now uses a durable `ModeledAdvanceService`.

Each accepted modeled advance is recorded in the immutable
`modeled_advance_operations` ledger with an idempotency key, base manifest,
context, step count, and deterministic target set. The row and the new learner
snapshot/manifest/revision are published in one SQLite transaction. Replay
consumes the ledger row as an explicit modeled transition, so it advances the
learner clock and decays only the pinned eligible targets without creating an
episode or synthetic observation.

Retries with the same operation ID return the original materialization. A
different request using that ID is rejected. Missing learning permission,
missing targets, stale/corrupt materialization, read-only stores, and malformed
operations fail closed. The CLI emits machine-readable status, operation,
revision, graph revision, accepted-episode count, and opportunity fields.

Schema version 10 adds the immutable modeled-advance ledger and a v9-to-v10
migration with backup support. Existing quarantine/rebuild materialization
continues to use its original opportunity semantics; modeled advances use the
new replay opportunity. The historical Phase Two learner and pilot artifacts
were not rewritten.

## Evidence

Focused tests cover durable replay, exact-once retry, idempotency conflict,
permission and target rejection, CLI output, transaction rollback after a
simulated interruption, and v9-to-v10 migration with a preserved backup.

- `pytest -q`: 419 passed
- Ruff: passed
- strict mypy (`mypy src/mneme`): passed
- wheel build and fresh-install import smoke: passed (`mneme 0.1.0`, schema 10)
- queue validation: passed
- provider calls: 0

This correction remains offline engineering work. P2.3 pilot adequacy and the
contingent-conversation live authorization boundary are unchanged.
