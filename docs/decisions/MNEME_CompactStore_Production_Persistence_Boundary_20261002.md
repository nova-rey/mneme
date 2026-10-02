# CompactStore production persistence boundary

Status: accepted engineering boundary, 2026-10-02.

The historical `SQLiteStore` snapshot schema served the early research phases
and remains supported for reading historical evidence, inspecting versioned
receipts/checkpoints, explicit reproduction, and copy-only migration. Its
materialized snapshots are not the preferred engine for new long-running
developmental state.

`CompactStore` / `CompactRuntime` is now the default writable persistence path
for new instances. Compact state keeps one current graph and learner value per
live identity, records changed graph rows as revisions, suppresses unchanged
learner journal entries, bounds optional telemetry, truncates WAL on clean
close, and creates full copies only for explicit checkpoints protected by a
free-space guard. Storage-health metrics expose the database, WAL, current
rows, revisions, journals, telemetry, and checkpoints without creating an
unbounded metrics log.

New CLI instances use CompactStore unless `--persistence legacy
--legacy-research-store` is supplied. Historical experiment execution paths
are compatibility paths and require the same explicit legacy opt-in once an
immutable prepared-run artifact is present. A compact instance cannot be
opened through a legacy-only operation; a historical SQLite database cannot be
treated as a compact store without an explicit copy-only migration.

Migration does not mutate the source. The resulting compact descendant must
pass logical-state, semantic-binding, learner, SAA seeded replay, provenance,
restart, and `verify()` checks before development continues. Frozen evaluation
continues to use its source representation read-only. The persistence choice
follows the operation: bounded current development uses CompactStore, while
historical evidence keeps its original SQLite representation.

The promotion does not change SAA semantics, learner rules, introspection
rules, model prompts, experimental schedules, or historical evidence. It is a
storage and entry-point decision only.
