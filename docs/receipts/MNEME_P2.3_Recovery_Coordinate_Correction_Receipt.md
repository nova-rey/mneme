# P2.3 Recovery Coordinate Correction Receipt

- **Recorded:** 2026-09-24
- **Prior correction commit:** `9524306`
- **Observed defect:** the first versioned recovery call returned an invalid
  residue. The subsequent repair coordinate did not retain the recovery
  operation identity, so software rejected the repair before dispatch.
- **Provider calls consumed by that attempt:** one Gemma extraction recovery;
  no repair call was dispatched and no accepted developmental call was
  repeated.
- **Correction:** repair now reuses the same recovery operation ID while the
  laboratory reservation keeps a distinct repair coordinate. Each later
  recovery operation derives a deterministic coordinate from its superseded
  operation ID, preserving exact-once retry identity without resampling.
- **Historical evidence:** the returned result, failed recovery row, and
  reservation remain preserved under the private recovery run.
- **Offline validation:** 319 pytest tests, Ruff, strict mypy, and package
  smoke pass; no provider call was made for this correction.
