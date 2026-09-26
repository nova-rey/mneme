# MNEME P2.3 Final Episodic Run 3 — Invalid Harness Stop — 2026-09-26

Run `p23-final-episodic-run-3` is preserved as `INVALID`.

The run dispatched and durably returned the first external-branch coordinate
(participant, Gemma development, local specialist extraction, and assessor).
After that accepted coordinate, the harness attempted to publish a per-turn
transcript through a nonexistent `ArtifactStore.publish_artifact` method and
raised an implementation error. No later coordinate was dispatched. The
partial request/result, developmental state, arc records, extraction, and
assessment remain in the run tree unchanged.

This is an instrumentation failure, not a scientific result. The corrected
harness uses the existing `PilotRun.publish_artifact` boundary and is rerun
under a new run ID. Historical Phase Two evidence is unaffected.
