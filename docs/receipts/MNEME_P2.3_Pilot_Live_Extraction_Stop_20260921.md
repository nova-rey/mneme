# MNEME P2.3 Pilot — Second Live Extraction Stop

**Status:** FAIL_STOP — bounded verification stopped after the first failed repair
**Run:** `p2-pilot-live-20260921b`
**Correction under test:** edge-less residue is an explicit excluded opportunity

This fixed run used the remaining campaign envelope of 287 calls and
189,696 reserved output tokens after 12 historical calls. Six new Gemma calls
returned at fixed coordinates: two development responses, three extraction
attempts (including one permitted repair), and one Qwen assessment. The run
stopped at subject 0 / episode 1 after the repair still failed strict
source-bound quotation validation. No retry, replacement, resampling, or
evaluation call occurred.

| Role | Calls | Input | Output | Total | Disposition |
|---|---:|---:|---:|---:|---|
| Gemma development | 2 | 49 | 248 | 297 | first episode accepted; second accepted before extraction stop |
| Gemma extraction | 3 | 2,401 | 1,979 | 4,380 | initial episode 0 valid; episode 1 initial invalid; one repair invalid |
| Qwen assessment | 1 | 1,247 | 144 | 1,391 | episode 0 returned and published |
| **Total** | **6** | **3,697** | **2,371** | **6,068** | **FAIL_STOP** |

The reservation ledger records 3,697 input, 2,371 output, and 6,068 total
tokens. Provider cost is unavailable in the sanitized reservation records.

The episode 1 repair failed with:

> `residue.core_concepts[3].evidence[0]: evidence quotation does not occur verbatim in source`

The model omitted Markdown emphasis delimiters from the quotation
`Moisture Retention: This is the big one you mentioned...`, while the immutable
model-output source contains `**Moisture Retention:** This is the big one you
mentioned...`. The strict validator correctly rejected it.

The first episode produced one accepted relationship and one Qwen assessment;
the deterministic adapter/publication path was reached successfully. The
complete sanitized request/result bundle is preserved in the accompanying JSON
file. The earlier live-stop receipts remain unchanged.

This evidence shows a recurring small-host extraction formatting failure under
the fixed strict provenance contract. It is not a credential, transport,
assessor, or learner arithmetic failure. The remaining campaign budget is now
281 calls, which is below the 288 scheduled pilot calls before any repairs;
continuation therefore requires explicit budget review or a new approved
campaign envelope.
