# MNEME P2.1 publication receipt

**Status:** PASS_OFFLINE  
**Provider calls:** 0  
**Validated commit:** `f49070d724e6b791c54348083b4689920a605599`

Atomic interpretation/publication behavior is covered by
`tests/test_memory_publication.py` and `tests/test_phase_two_publication.py`.
The tests prove stable semantic bindings, observation and learner-value
publication in one transaction, idempotent accepted transitions, stale-base
rejection, permission gating, unknown/no-credit handling, and exact learner
opportunity replay across episode and interpretation revisions.
