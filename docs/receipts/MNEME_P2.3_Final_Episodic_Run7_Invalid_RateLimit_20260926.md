# MNEME P2.3 Final Episodic Run 7 — Invalid Provider Rate Limit — 2026-09-26

Run `p23-final-episodic-run-7` is preserved as `INVALID`. It is not a
scientific result and does not alter the historical P2.3 disposition.

The external branch completed all 30 fixed turns. The model branch completed
through turn 26; at the next participant coordinate the designated DeepInfra
host returned HTTP 429 before a participant result was returned or persisted.
The run stopped immediately. No subsequent Gemma, extraction, assessment, or
learner work was dispatched for that coordinate.

This is a transient provider/infrastructure failure, not evidence for or
against episodic recurrence or consolidation. The exact partial run remains
immutable at:

`/tmp/mneme-p23-final-episodic-20260926-run7/`

The authorized recovery is limited to the failed final model-branch
coordinate, using a copied read-only continuation workspace. It does not
regenerate completed turns or restart either branch.
