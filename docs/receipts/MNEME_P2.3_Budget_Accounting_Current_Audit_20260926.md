# MNEME P2.3 budget and accounting current audit

Date: 2026-09-26  
Audited commit: `3cb31b91c44250e2ea91399044be7600e1c7d0f5`  
Provider calls during audit: 0  
Disposition: **FACTUAL LEDGER RECONCILED; AUTHORITY REVIEW REMAINS OPEN**

## Reconciliation

| segment | calls | persisted |
|---|---:|---:|
| baseline through q→r | 353 | 353 |
| original cross-thread v6 | 82 | 82 |
| corrected local MNEME readouts | 18 | 18 |
| corrected blinded evaluation | 2 | 2 |
| provider return lost before local persistence | 1 | 0 |
| **total** | **456** | **455** |

The arithmetic is `353 + 82 + 18 + 2 + 1 = 456` attempted/returned calls and
`353 + 82 + 18 + 2 = 455` persisted results. Reused control rows are not
counted as new calls. The lost provider return remains a charged attempted call;
its missing result is not reconstructed or silently counted as zero.

The q→r portion is independently recorded as `187 + 59 + 107 = 353` in the
live continuation receipt. The original v6 reservation tree contains 82 unique
returned reservations. The corrected readout and blinded-evaluation records
provide the remaining 18 + 2 persisted calls and the one lost persistence
attempt.

## Ceiling and disposition

The approved nominal ceiling is 299 calls. The recorded standing contingency
cap is 399 calls with the output-token ceiling unchanged. The current factual
total is therefore 57 calls above that operational cap (`456 - 399`).

No calls were deleted, reclassified, or made during this reconciliation. The
overage is now fully attributable, but accepting its authority consequence is a
review decision. P2.3 remains `WAITING`; no additional provider execution,
release tag, or Phase Three work is justified by this receipt.

The separate scientific blocker also remains: no persisted evidence demonstrates
the approved separated-support/consolidation transition.
