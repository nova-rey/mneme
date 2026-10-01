# P3 storage recovery appendix

The Thread-75 audit measured I-75 at 1,095,016,448 bytes and N-75 at 1,230,663,680 bytes (4096-byte pages, freelist 0). The dominant tables were learner_updates (I 498,712,576; N 561,078,272), learner_snapshots (I 179,666,944; N 203,358,208), and learner_values (I 156,057,600; N 175,058,944). Graph snapshot duplication was real (462/479 snapshots; roughly 237/218 physical concept/edge rows per unique key) but smaller than the learner history.

Copy-only compaction retained the latest logical learner state and streamed immutable learner history to zstd. Compact I-75 was 165,036,032 bytes (SHA-256 591f09cd73688abbfa5b60c0f154f2ff87b2edefad91fde6b0ef5dfbb16a332f); compact N-75 was 183,562,240 bytes (SHA-256 68883236b8c8fec23063aa9bb78c6b9c8672910fcecc715b676e349320b1b10). SQLiteStore.verify, current manifests, graph row sets, learner state, SAA replay, payload, provenance, and removal/restoration capability were equivalent. Threads 1-75 were not rerun.

The accepted r23 continuation grew final I-100 to 440,381,440 bytes and N-100 to 495,190,016 bytes; V was 18,763,776 bytes. The r23 process encountered one disk-full interruption during removal after all 432 primary readouts and 75 removal reservations had returned; the remaining removal coordinates were resumed from their durable reservation ledger after stale temporary Git staging was removed. No development or primary readout was rerun.

Historical compressed archives and learner-history streams remain canonical evidence. Before a production service, replace periodic full materialized graph copies and redundant full SQLite backups with revision deltas/structural sharing and explicit evidence/checkpoint separation.
