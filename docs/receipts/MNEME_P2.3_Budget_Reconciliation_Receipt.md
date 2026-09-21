# MNEME P2.3 live-budget reconciliation receipt

**Disposition:** accounting correction; no provider call made  
**Ceiling:** 299 calls / 204,288 maximum output tokens  
**Reconciled through:** `70277a517f12cac47d188e703cbd3e351016b369`

The earlier queue note undercounted historical qualification calls. The
governing assessor-role addendum requires all previous qualification attempts to
remain charged in the lifetime/campaign total. This receipt counts each
persisted provider call once, preserves every source receipt unchanged, and
does not count a receipt-only audit correction as a call.

## Unique provider-call accounting

| Evidence group | Calls | Input | Output | Total |
|---|---:|---:|---:|---:|
| Historical qualification attempts, including failed Gemma/Qwen attempts | 24 | 22,211 | 5,858 | 28,069 |
| v9 coverage/polarity qualification | 3 | 3,784 | 801 | 4,585 |
| Historical pilot calls, unique coordinates | 15 | 8,596 | 5,329 | 13,925 |
| **Campaign total** | **42** | **34,591** | **11,988** | **46,579** |

The `pilot-1` partial probe's two calls are included in the later six-call
`MNEME_P2.3_Pilot_Extraction_Stop_Receipt`; they are not double-counted. The
two receipts using run ID `qualification-20260920-v4` describe distinct
provider attempts (Gemma v4 and Qwen prompt-v4) and are both counted because
their persisted requests/results and contracts differ.

Provider-reported cost is unavailable in the retained results. Actual token
usage is reported above; no unknown usage was converted to zero.

## Budget consequence

- Calls consumed: **42**
- Calls remaining under the unchanged ceiling: **257**
- Approved no-repair pilot schedule: **288** calls
- Repair pool in the full proposal: **8** additional calls
- Pilot calls dispatched after the v9 qualification: **0**

The approved pilot cannot complete under the current ceiling. P2.3 remains
`WAITING` on budget review and the prior extraction-stop review. No pilot call
is dispatched, no historical receipt is rewritten, and no Phase Three work is
started.
