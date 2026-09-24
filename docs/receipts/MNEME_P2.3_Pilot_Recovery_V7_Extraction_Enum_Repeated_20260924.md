# MNEME P2.3 Pilot Recovery V7 Repeated Extraction Enum Failure

- Date: 2026-09-24
- Run: `p2-pilot-recovery-20260924m`
- Continuation of: `p2-pilot-recovery-20260924l`
- New provider calls: 2
- Result: stopped at `extraction-s1-e7-recovery-extraction-s1-e7`

The residue-v4 prompt was corrected offline with explicit negative examples for
unsupported relationship values. The fixed recovery call nevertheless repeated
`relationship: "holds"` for the same source, and strict validation rejected it
as an unsupported relationship kind. The prior invalid operation and this new
versioned recovery operation remain immutable. No assessment, evaluation, retry,
or unchanged resampling followed.

Progress at stop: 38 developmental responses accepted, 31 valid extractions,
31 completed assessments, 17 admitted relationships, and zero evaluations.
This is a repeated same-class model-output failure after a targeted prompt
correction; further continuation requires review rather than automatic
resampling. Exact request/results remain in `/tmp/mneme-p23-live-20260924m`.
