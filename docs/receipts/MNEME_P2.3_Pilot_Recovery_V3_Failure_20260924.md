# MNEME P2.3 pilot recovery v3 failure receipt

**Date:** 2026-09-24  
**Run:** `p2-pilot-recovery-20260924i`  
**Disposition:** blocked after corrected recovery; no assessment or evaluation calls

This continuation copied the preserved h stores and reused the accepted
`development-s1-e1` response. It dispatched one new `residue-v3` recovery
extraction. The v3 prompt contained an explicit example requiring the leading
Markdown list marker and both bold-marker pairs. Gemma nevertheless returned
the rendered quotation without those markers:

`Reduces Evaporation: The layer of mulch acts as a barrier, shading the soil,
and significantly slowing down the rate at which water evaporates due to the
heat of the sun and warm air.`

The immutable source contains:

`* **Reduces Evaporation:** The layer of mulch acts as a barrier, shading the
soil and significantly slowing down the rate at which water evaporates due to
the heat of the sun and warm air.`

Strict source-bound validation correctly rejected the result. Because the
approved eight-call extraction-repair pool was already exhausted in the h
run, no repair was dispatched. The run therefore stopped before assessment
and evaluation. The v2 and v3 results, requests, reservations, and h/i
lineage stores remain unchanged and auditable.

The i continuation returned two provider results (one reused developmental
response was durably bound to the new coordinate and one v3 extraction), using
1,018 input tokens, 572 output tokens, 1,590 total tokens, and approximately
$0.0000628 in provider-reported estimated cost. Cumulative campaign usage is
120 returned calls, below the standing 399-call operational cap.

This is no longer a credential, transport, persistence, or validator defect.
It is repeated model inability to satisfy the strict immutable-Markdown quote
contract under the selected Gemma extraction role. Further prompt-only
resampling would not be legitimate acceptance evidence; continuation requires
architectural/role review of the extraction contract or host suitability.
