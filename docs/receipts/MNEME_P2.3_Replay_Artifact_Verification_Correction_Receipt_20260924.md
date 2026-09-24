# MNEME P2.3 replay and artifact verification correction receipt

**Status:** OFFLINE_CORRECTION_VALIDATED  
**Provider calls:** 0  
**Code commits:** `26cbfb55e20ec5fc7672d4e0ba591b00718300b`,
`f49070d724e6b791c54348083b4689920a605599`

Two implementation defects found during the P2.3 audit were corrected.

1. Accepted episode manifests now carry forward the Phase Two learner fields,
   including the global opportunity. A sequential episode/interpretation
   regression proves opportunities `1, 2` and exact materialized/replay
   agreement.
2. `ArtifactStore.verify_run()` now accepts the direct JSON evaluation receipts
   emitted by the Phase Two runtime while still rejecting symlinks, non-JSON
   files, and malformed JSON.

The completed private `p2-pilot-recovery-20260924r` tree now passes the artifact
verifier. The interrupted `q` tree remains false by design because it contains
the preserved empty pre-dispatch reservation for the interrupted coordinate;
that historical evidence was not deleted or rewritten.

The original subject stores were not modified. For audit, copies were explicitly
migrated from schema 8 to schema 9 and rebuilt from their immutable accepted
operation ledgers. Before rebuild, both copies reproduced the known mismatch
(ledger opportunity 24 versus materialized opportunity 1). After deterministic
rebuild, both copies reported `matches_materialized: true` at opportunity 24.

This repair proves the replay/materialization mechanism and the artifact
inventory boundary. It does not create the missing separated-support pilot
opportunity and does not change the P2.3 adequacy disposition.
