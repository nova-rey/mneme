# Phase Three storage correction

The Thread-75 I/N checkpoint databases were audited before resumption. The
authoritative full copies were preserved as exact zstd archives; Threads 1–75
were not rerun.

## Measured cause

I-75 is 1,095,016,448 bytes (267,338 pages at 4,096 bytes) and N-75 is
1,230,663,680 bytes (300,455 pages). Both had zero freelist pages. The large
tables were learner history, not the graph snapshot tables:

| lineage | learner_updates | learner_values | learner_snapshots | graph concepts | graph edges |
|---|---:|---:|---:|---:|---:|
| I | 498,712,576 | 156,057,600 | 179,666,944 | 34,471,936 | 59,478,016 |
| N | 561,078,272 | 175,058,944 | 203,358,208 | 37,998,592 | 68,087,808 |

I contained 462 graph snapshots, 293,867 concept rows for 1,240 unique concept
keys, and 275,179 edge rows for 1,263 unique edge keys. Thus graph snapshots
do duplicate unchanged rows (about 237 concept rows and 218 edge rows per
unique key), but they account for roughly 100 MiB rather than the gigabytes.
The dominant growth is append-only learner updates, materialized values, and
full learner snapshots; full SQLite checkpoint copies then duplicate those
stores again.

## Correction

`tools/compact_p3_checkpoint.py` creates a copy-only, auditable compact
checkpoint. It streams every removed learner row to an exact zstd JSONL
archive, retains the latest materialized learner value and its update for each
instance/edge/context, retains the latest learner snapshot per instance, and
leaves graph, source, interpretation, provenance, and development tables
unchanged. It restores the immutable-table triggers and validates SQLite
integrity and foreign keys.

The compact I/N copies are 165,036,032 and 183,562,240 bytes. Their learner
state digests, graph rows, current manifest/state, SAA field result, and
`SQLiteStore.verify()` output matched the full copies. Full learner archives
remain at:

* `MNEME_P3_Introspection_100_Thread_Run_20261001_I75_learner_history.jsonl.zst`
* `MNEME_P3_Introspection_100_Thread_Run_20261001_N75_learner_history.jsonl.zst`

The continuation uses those compact copies as read/write development inputs
on `/dev/shm`, preserving the frozen Thread-75 checkpoint while avoiding a
second multi-gigabyte working copy on the root filesystem. The existing
0/10/25/50/75 checkpoint evidence remains available through the preserved
archives/parent manifest. Only the required Thread-100 checkpoint is created
for the continuation. Readouts open frozen checkpoints read-only and do not
fork additional databases.

The exact full-copy archives and compact-copy hashes are recorded in
`MNEME_P3_Storage_Audit_20261001.json`. Expected live scratch use is below
the 2 GiB `/dev/shm` capacity for the compact pair, bounded 76–100 growth, and
one final checkpoint pair; no Thread 1–75 calls are dispatched.
