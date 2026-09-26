# MNEME P2.3 Final Episodic Run 6 — Invalid Remote Decode — 2026-09-26

Run `p23-final-episodic-run-6` is preserved as `INVALID`. It is not a
scientific result and does not alter the historical P2.3 disposition.

The external branch completed its fixed 30-turn schedule. The model branch
reached turn 11 and then its local Gemma development call at turn 12 became
`UNCERTAIN`: the SSH adapter decoded remote stdout as strict UTF-8 and raised
`UnicodeDecodeError` on malformed bytes before the returned model content
could be persisted. The run stopped immediately; no automatic regeneration or
downstream interpretation was performed for that coordinate.

This is an adapter/instrumentation defect, not evidence for or against
episodic recurrence or consolidation. The exact reservation and partial
artifacts remain immutable at:

`/tmp/mneme-p23-final-episodic-20260926-run6/`

Representative digests:

* `run-manifest.json`: `365f18a28309c7e0b9510422390ac878c0ec1f7b785e177f5dc1347bcfd2472b`
* uncertain reservation `development-model-t12.json`: `4b06a2b897ae649948d98cf096ad469acf1dd33122ff151de405b417404b5aaa`
* last completed model transcript `model-turn-11.json`: `64b1a006630561f8942efc473ecbf0b1118cd8f16337a592cbb9c18e52f7e91e`

The in-scope correction is limited to decoding remote subprocess output with
replacement semantics so malformed bytes cannot discard an otherwise returned
result. It does not alter model, learner, provenance, or acceptance rules. A
fresh run ID is required because this run cannot be resumed as a valid complete
experiment.
