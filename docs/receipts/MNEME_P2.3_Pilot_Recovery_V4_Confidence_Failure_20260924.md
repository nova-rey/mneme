# MNEME P2.3 Pilot Recovery v4 — Confidence Schema Stop

- **Date:** 2026-09-24
- **Run:** `p2-pilot-recovery-20260924j`
- **Continuation:** preserved `p2-pilot-recovery-20260924i`
- **Returned calls:** 13
- **Usage:** 10,249 input tokens, 3,227 output tokens, 13,476 total tokens; provider cost unavailable
- **Status:** FAILED at `extraction-s1-e5`; no evaluation calls

The continuation reused the accepted `s1-e1` response without redispatching it,
completed its extraction/assessment, and advanced through `s1-e4`. At `s1-e5`,
Gemma returned source-grounded concepts and an edge, but omitted the required
`confidence` field on each graph record. The exact validator rejected the result:

`residue.core_concepts[0]: graph material requires confidence`

The preserved model result contained the source quotation
`Repeating the difficult measure slowly helped me hit the right notes.` and
relationship material, but no confidence value. The one-time extractor repair
pool was already exhausted from historical attempts, so the temporary evidence
reviewer correctly did not run: this was a structural schema failure, not an
unresolved quotation. The run stopped without assessment or evaluation for the
failed coordinate. No prior receipts were rewritten.
