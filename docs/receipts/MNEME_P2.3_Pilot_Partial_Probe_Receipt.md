# MNEME P2.3 partial pilot probe receipt

- **Status:** `PARTIAL_PILOT_PROBE`; no adequacy or research claim.
- **Scientific identity:** `p2-developmental-pilot / contract_revision 1`.
- **Qualification:** fixed polarity v8 passed; see [qualification receipt](MNEME_P2.3_Assessor_Qualification_Polarity_V8_Pass_Receipt.md).
- **Calls consumed:** 2 post-qualification pilot calls (one Gemma development response and one Gemma extraction), both returned and durably persisted in the temporary run before this receipt was written.

The fixed engineering input was:

> I sorted the socket wrenches into labeled workshop bins, so finding the right size for a repair takes less time.

Gemma returned a supportive response, and the extractor returned a structurally valid residue with source-bound concepts and edges. The sanitized machine-readable request/result record is in the companion JSON. No assessor or evaluation calls were made.

The probe stopped after a harness serialization error while printing the accepted operation receipt. It did not retry or replace the provider call. Audit also found that the repository currently has a bounded `PilotRuntime` primitive but no committed fixed-fixture schedule/orchestrator or CLI path that can safely execute the approved 48 development responses, 48 extractions, 48 assessments, 144 frozen readouts, and finite repair pool. Therefore this probe is not a P2.3 acceptance run.

If execution resumes after that in-scope gap is closed, these two calls consume two of the unchanged post-qualification pilot allowance and must remain accounted for; their coordinates must not be regenerated.
