# MNEME P2.3 pilot recovery v2 failure receipt

**Date:** 2026-09-24  
**Run:** `p2-pilot-recovery-20260924h`  
**Disposition:** stopped at the fixed extraction-repair boundary; no evaluation calls

This private continuation copied the preserved `p2-pilot-recovery-20260924g`
lineage stores. It reused the already accepted `development-s0-e8` response,
issued one versioned `residue-v2` recovery extraction, and continued the fixed
schedule without redispatching accepted developmental responses. Historical
qualification v9 was reused; no qualification calls were dispatched.

The run returned 48 provider results: 18 developmental responses, 23
extractions, and 7 assessor calls. It reached 27 accepted developmental
responses, 25 valid extractions, 25 assessments, and 13 admitted relationships.
The eight-call extraction-repair allowance was exhausted. No evaluation call
was dispatched.

The run stopped at `extraction-s1-e1` after its initial extraction and one
permitted repair. Both results were durably retained and both failed strict
source-bound quotation validation. The model returned the rendered words
`Reduces Evaporation: The layer of mulch acts as a barrier, shading the soil
and significantly slowing down the rate at which water evaporates due to the
heat of the sun and warm air.` for source `s1`, while the immutable model
output contained the Markdown bullet and bold markers:
`* **Reduces Evaporation:** The layer of mulch acts as a barrier, shading the
soil and significantly slowing down the rate at which water evaporates due to
the heat of the sun and warm air.`

The strict validator correctly rejected the quotation because it was not a
verbatim substring. This is a model-output/contract-formatting failure, not a
transport, persistence, or credential failure. The one-repair rule and
fail-closed provenance requirement were preserved. No historical artifact was
rewritten.

Usage for this continuation was 35,348 input tokens, 9,751 output tokens,
45,099 total tokens, and approximately $0.0009181 in provider-reported
estimated cost. Cumulative campaign accounting is 118 returned calls before
any further continuation, below the standing 399-call contingency cap.

The next action requires an offline prompt correction targeted at copying
Markdown list/bold source text, followed by the normal test/CI gate. No
unchanged resampling is authorized by this receipt.
