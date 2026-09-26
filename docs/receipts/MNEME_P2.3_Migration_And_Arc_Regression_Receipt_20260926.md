# P2.3 migration and arc regression receipt

Tested commit: `e21b4f2fa3863a43792a92fc95f2c83bbd36799a`  
Remote CI: `36210057361` (success)  
Provider calls: 0

## Added evidence

The schema regression now exercises an explicit populated schema-10 store
migrating to schema 11. It verifies the migration backup, preservation of
existing development observations, creation of all three conversation-arc
tables, the five arc-related observation columns, and an empty foreign-key
check.

The FakeHost supplement regression now exercises the production runner path
far enough to prove that one accepted turn publishes exactly one immutable arc,
one member, and its OPEN/CLOSE events. This is separate from the unit tests
for deterministic grouping and idempotent retry.

## Validation

* `.venv2/bin/pytest -q`: **461 passed**;
* `.venv2/bin/ruff check src tests`: passed;
* `.venv2/bin/mypy --strict src/mneme`: passed;
* isolated Hatchling wheel build and fresh-target import smoke: passed;
* `work-queue --queue .codex/work-queue.json validate`: passed;
* remote CI `36210057361`: passed.

These tests strengthen P2.1/P2.2 migration and P2.3 arc-wiring evidence only.
They do not reinterpret historical v6 records, create learner credit, spend
provider calls, or satisfy the unresolved P2.3 separated-support/consolidation
adequacy review.
