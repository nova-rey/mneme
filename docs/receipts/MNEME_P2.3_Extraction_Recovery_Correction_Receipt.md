# P2.3 Extraction Recovery Correction Receipt

- **Recorded:** 2026-09-24
- **Historical stop:** `p2-pilot-live-20260921b`
- **Historical evidence:** preserved unchanged in the live stop bundle and
  the `parent.sqlite3` interpretation ledger.
- **Defect:** the failed extraction operation exhausted its one initial plus
  one repair attempt, and the pilot had no safe way to continue that accepted
  episode after an in-scope contract correction.
- **Correction:** schema 8 removes the accidental one-operation-per-episode
  uniqueness constraint through an explicit v7→v8 migration. A failed
  operation remains immutable; a corrected extraction creates a distinct
  operation and records `RECOVERY_OF:<old-operation>` in its durable ledger
  row. The fixed pilot uses a new recovery coordinate and does not redispatch
  an already accepted developmental response.
- **Strictness:** source-quotation validation, one repair per recovery
  operation, provenance, route, learner, and scientific acceptance criteria
  are unchanged. The recovery prompt is versioned and remains fail-closed.
- **Offline provider calls:** 0
- **Live status:** not dispatched by this correction receipt.
