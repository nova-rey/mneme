# MNEME P2 contingent restart-assessment reconstruction correction

Date: 2026-09-24  
Repository: `nova-rey/mneme`  
Run: `contingent-live-20260924`  

## Scope

The preserved contingent-conversation run already publishes exact sanitized
conversation transcripts at each boundary in
`MNEME_P2_Contingent_Conversation_Transcript_20260924.md`. This correction
hardens restart reconstruction for the same run; it does not regenerate any
conversation, extraction, or assessment call.

## Correction

When rebuilding accepted turns, a valid extraction is now considered a
trustworthy interpretation only when its persisted assessment record is also
valid. A persisted failed assessment reconstructs as
`measurement_unknown / interpretation_unavailable`, with assessment failure
classification and its recorded validation reason. A valid extraction with no
assessment record remains complete because that turn did not require an
assessor call. Extraction failure remains terminal unknown. This preserves the
rule that an accepted conversation is retained while failed interpretation
earns no learner credit, absence inference, or negative evidence.

## Evidence and validation

- New regression coverage exercises failed-assessment reconstruction and the
  valid-extraction/no-assessor path.
- Focused contingent tests: 11 passed.
- Full pytest: 386 passed; Ruff passed; strict mypy passed; wheel build and
  fresh-install import smoke passed.
- Existing transcript and live-stop receipts remain unchanged and authoritative.
- The run remains paused after 9 accepted interactive turns: 6 trustworthy,
  3 terminal interpretation-unknown, 66.7% success; the declared post-eight-
  turn threshold therefore requires interpretation-rate review before any
  continuation.
- No provider calls were made for this correction.

## Disposition

The correction is offline-only. The preserved run is not restarted and no
turns 0–8 are regenerated. The queue remains WAITING on
`review:contingent-interpretation-rate-stop`; the measurement stop is a
scientific adequacy gate, not an implementation permission to bypass.
