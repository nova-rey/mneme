# MNEME P2.3 Pilot Recovery V6 Extraction Enum Failure

- Date: 2026-09-24
- Run: `p2-pilot-recovery-20260924l`
- Continuation of: `p2-pilot-recovery-20260924k`
- New provider calls: 7
- Result: stopped at `extraction-s1-e7`

The continuation reused accepted developmental state and the corrected assessor
prompt. The prior assessor coordinate `assessment-s1-e5` passed with an exact
nested-Markdown quotation. At `extraction-s1-e7`, Gemma returned otherwise
source-grounded graph material but used the unsupported relationship kind
`holds`; the complete allowed vocabulary did not include it. Strict residue
validation rejected the result. The per-interpretation repair allowance had
already been exhausted by earlier coordinates, so no repair, assessment, or
evaluation call followed. No unchanged resampling occurred.

Progress at stop: 37 developmental responses accepted, 31 valid extractions,
31 completed assessments, 17 admitted relationships, and zero evaluations.
The exact request/results remain in `/tmp/mneme-p23-live-20260924l`.
