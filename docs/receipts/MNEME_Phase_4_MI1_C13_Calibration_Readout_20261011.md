# MI1 C13 calibration readout

C13 completed all 72 frozen calls and failed its predeclared calibration gate. Neither selected-site nor broad all-head routing made a latent fact recoverable on the fixture set. This is a calibration failure, not the final MI1 disposition; the owner has authorized further diagnosis.

The visible positive controls scored 15/16 (A: 8/8, B: 7/8). The two negative controls, no-bank and assertive-cue-without-bank, each scored 8/8 `unknown`. Selected-site latent A and B both scored 0/8. Broad all-head latent A and B also scored 0/8; all eight broad relevant/irrelevant-bank calls ended at the 1,024-token limit with repetitive output. The broad route is therefore disruptive and does not pass controls. The selected route ended normally but its reasoning repeatedly stated that the hidden record was unavailable.

No frozen held-out confirmation was run: the gate requires at least 7/8 correct for both polarities, visible controls, and unknown controls. C13 evidence cannot be rescued by reinterpreting its criteria.

The detailed per-coordinate answer/finish/hash summary is in [C13 machine readout](MNEME_Phase_4_MI1_C13_Calibration_Readout_20261011.json). Exact requests, full reasoning and outputs are retained outside Git at `/home/nyx/mneme-artifacts/phase4-mi1/c13-calibration/evidence/`; the 72-row index SHA-256 is `5975da6e66cfd26a11e21f49c94e48fcd98d28e3726bc3074b34e01f4ba0b492`. The scored derivation is at `/home/nyx/mneme-artifacts/phase4-mi1/c13-calibration/scored.json` (SHA-256 `7c2a34b8e09796f6396ffbecb555e82472ef5ec64f6c04765ed7cb9a344bb849`).

The result supports three limited observations. First, Gemma solves this exact relation task when its rules are visible. Second, selected-site bank attachment and a stronger availability cue still do not make those facts behaviorally available. Third, exposing every query head is not a usable fix: it produces pathological repetition. C12's measured bank attention mass and C13's expected fingerprints establish numeric routing, not semantic use.

Next diagnosis is to verify source-KV capture/application semantics against the paper and isolate a simpler one-hop recall task. The C13 held-out coordinates remain frozen and unused; any materially revised calibration must be frozen independently before generation.
