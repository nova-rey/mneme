# P2.3 Recovery Migration Fix Receipt

- **Recorded:** 2026-09-24
- **Exposed by:** continuation run `p2-pilot-recovery-20260924d`
- **Failure:** after one recovery extraction call returned, publication of a
  valid edge-less residue reached graph-copy code and SQLite reported
  `no such table: main.__v7_candidates`.
- **Cause:** the v7→v8 table rebuild used SQLite's enhanced ALTER semantics,
  which rewrote foreign-key declarations in dependent graph and learner tables
  to temporary migration names before those names were dropped.
- **Correction:** the explicit migration enables legacy ALTER semantics before
  renaming the interpretation family, then restores normal behavior. Rebuilt
  stores retain stable foreign-key names and pass `PRAGMA foreign_key_check`.
- **Provider calls in failing continuation:** one Gemma extraction recovery;
  no repair, assessor, or evaluation call was dispatched after the failure.
- **Offline validation after correction:** 319 pytest, Ruff, strict mypy,
  focused migration/recovery tests, and package smoke pass; no provider call
  was made for this correction.
