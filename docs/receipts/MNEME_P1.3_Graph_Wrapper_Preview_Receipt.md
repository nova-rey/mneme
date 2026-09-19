# MNEME P1.3 Graph-Wrapper Preview Receipt

Date: 2026-09-19  
Accepted P1.2 base: `b46e8c728e2dbf80e553b14b4de99713e6610a1bf`  
Initial candidate: `13acdfafe630000672f8e96ea252c7171cf3c06c`  
Audited tested code: `2a14ab0fc3f951d1c69a2979e2c41d32d807e892`  
Package: `P1.3`

P1.3 adds the graph-wrapper preview over read-only P0.2 checkpoints. The
comparator executes matched `no_memory`, lexical raw-episode, and fixed graph
route treatments at the same subject/probe/repetition coordinates. Lexical and
graph payloads use bounded typed notes and deterministic content tie-breaking;
confidence, salience, recurrence, recency, frequency, and praise do not become
Phase One accessibility weights.

Checkpoint inspection labels lineage revision, accepted-episode count/ordinal,
graph revision, and self-view version separately. Comparison requests and
results carry coordinate, request, system, and output digests. The frozen view
checks both the SQLite logical state and checkpoint file digest before and after
each host call. Comparison artifacts are private working evidence: raw output
is removed from the sanitized JSON/Markdown receipt, while output digests and
measurements remain auditable. Re-entry validates checkpoint, provenance,
coordinates, and matched seeds and returns the completed result without calling
the host again; conflicts fail closed.

Validation performed at this stop gate:

- `.venv2/bin/pytest -q`: **153 passed**
- Focused comparison/inspection tests: **5 passed**
- `.venv2/bin/ruff check .`: **passed**
- `.venv2/bin/mypy --strict src`: **passed** (37 source files)
- `git diff --check`: **passed**
- CLI parser/helper smoke: matched comparison command parses and executes.
- Offline FakeHost acceptance: 12 matched frozen readouts across two probes,
  two repetitions, and three treatments; checkpoint/file invariance,
  separately labeled counters, sanitized artifacts, and completed re-entry
  against a host that would fail if called all passed.

This receipt covers the credential-free preview gate. The separate required
live acceptance action was attempted and is recorded as blocked in
`MNEME_Phase_One_Live_Acceptance_Blocker.md`; it did not produce release
evidence. No adaptive learner, individuality claim, or Phase Two mechanism was
added.
