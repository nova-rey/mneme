# MNEME P2.3 pilot extraction stop receipt

- **Status:** `FAILED_STOP`; pilot adequacy and research outcome were not assessed.
- **Scientific identity:** `p2-developmental-pilot / contract_revision 1`.
- **Qualification:** polarity v8 Q1/Q2/Q3 passed before pilot.
- **New provider calls:** 6 (Gemma development 2, Gemma extraction initial 2, Gemma extraction repair 1, Qwen assessment 1).
- **Usage:** 3,411 input, 2,128 output, 5,539 total tokens; provider cost unavailable.

The first development/extraction pair was accepted and its assessor call returned a valid semantic result. The second development response also returned. Its extraction returned a residue that failed strict source-bound validation because one quotation supplied for model-output source `s1` did not occur verbatim in that source. The single permitted repair returned another residue with the same non-verbatim evidence failure. The fixed pilot stop rule therefore halted execution immediately. No evaluation calls were made, and no further development, extraction, repair, assessment, or readout calls were dispatched.

The raw provider outputs, source-bound validation errors, usage, and durable call dispositions are preserved in the companion JSON. The earlier partial-probe receipt remains unchanged. One pre-dispatch assessor reservation was marked `FAILED` after an implementation role-binding error; it made no provider call and is separately recorded.

This is an honest pilot failure, not a qualification failure and not evidence that the assessor host is unsuitable. The next decision is whether to correct the extraction/pilot fixture or stop for review; no automatic resampling is authorized.
