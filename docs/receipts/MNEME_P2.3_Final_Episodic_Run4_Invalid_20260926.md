# MNEME P2.3 Final Episodic Run 4 — Invalid Envelope Stop — 2026-09-26

Run `p23-final-episodic-run-4` is preserved as `INVALID`.

The frozen two-branch schedule needs at most 240 role calls before optional
empty-residue skips. The run was prepared with an erroneous 100-call envelope
and therefore stopped at the reservation boundary after 100 returned calls,
through external-branch turn 24. Turn 25 was never reserved or dispatched;
the model branch did not start. No scientific result is assigned.

This is a planning/accounting defect, not a negative consolidation result. The
preflight is corrected to a 300-call hard bound, and one fresh run is permitted
under a new run ID. Run 4's accepted requests, results, lineage state, and
partial traces remain unchanged.
