# P2.3 provenance-group identity correction receipt

Tested production commit: `b80a52387a75ea9960c8c5742fba87b689b945ce`  
Remote CI: `36208961171` (success)  
Provider calls: 0

## Correction

When a provenance group has no exposure or replay root, external evidence now
uses its immutable `source_id` (`external:<source_id>`) when one is available.
The request-local source-slot fallback remains only for preserved requests that
have no durable source identity. Recorded-ancestry fallbacks use `source_id`
before `source_slot` for the same reason.

This prevents two independent external episodes that both serialize their
evidence as `s0` from collapsing into one lifetime accounting group.

## Validation

* `457 passed` with `.venv2/bin/pytest -q`;
* Ruff passed;
* strict mypy over `src/mneme` passed;
* wheel build and fresh-target import smoke passed;
* JSON validation and `git diff --check` passed;
* focused provenance regression proves distinct source IDs produce distinct
  groups and repeated use of one source ID remains stable;
* remote CI passed at the tested commit.

## Boundary

This correction does not reinterpret historical receipts or mutate learner
state. The preserved v6 derived arc audit remains `NO_CREDIT_CHANGE`. The
adversarial audit also identified that the live conversational runners do not
yet persist and pass multi-turn arc records through the production adapter;
that integration gap remains an explicit P2.3 review blocker and is not hidden
by this source-identity fix.

