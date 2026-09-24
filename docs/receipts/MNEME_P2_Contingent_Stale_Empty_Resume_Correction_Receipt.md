# MNEME P2 contingent stale-empty resume correction

Date: 2026-09-24

The first post-capacity resume reached publication and exposed a preserved-run resume edge: an earlier empty interpretation had a base manifest older than a later accepted episode. Rewinding or publishing that empty residue against a stale manifest would be unsafe. The supplement now records a sanitized `SKIPPED_STALE_EMPTY_INTERPRETATION` artifact and continues only when the residue contains no relationship edges. Relationship-bearing stale publications remain fail-closed.

The failed resume made no new provider call; all existing coordinates and raw results remain preserved. This is an execution-resume correction only and does not alter learner semantics, accepted history, or source grounding.

Offline validation: 380 pytest tests, Ruff, strict mypy, wheel build and fresh-install smoke pass. CI is required before the next resume.
