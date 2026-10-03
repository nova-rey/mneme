# Reasoning ON/OFF developmental funnel analysis

Run `mneme-reasoning-25-fresh-20261003-r1`; analysis is read-only and made no model calls or specimen writes.

Source receipt: `docs/receipts/MNEME_Clean_Slate_Reasoning_25_Thread_Fresh_R1_20261003.json` (SHA-256 `1807684476ba755146c3133623dc8b17bc0d8e5d2cd1e06d577f6cee19dd2a49`). Raw developmental evidence remains outside Git at `/home/nyx/mneme_artifacts/mneme-reasoning-25-fresh-20261003-r1/development-evidence.json`. The complete receipt and external CompactStore specimens are not copied here.

## Executive result

OFF finished with 81 canonical admitted edges and ON with 42. The preserved evidence supports a funnel explanation: raw GLiNER proposal counts were nearly equal (323 vs 315), but ON produced about 3.06× more visible output tokens, so its proposal rate was much lower; ON also passed a smaller fraction of proposals through the single local NLI admission gate (13.3% vs 25.1%). Provenance and learner eligibility were the same for every admitted observation, and neither branch showed recurrence or consolidation.

## Branch totals

| metric | OFF | ON | interpretation |
|---|---:|---:|---|
| Visible Gemma output tokens | 30655 | 93634 | |
| Extraction proposals | 323 | 315 | |
| Admitted relationships | 81 | 42 | |
| Rejected relationships | 242 | 273 | |
| Proposal / 1,000 output tokens | 10.5366 | 3.3642 | |
| Admitted / 1,000 output tokens | 2.6423 | 0.4486 | |
| Admission rate | 25.1% | 13.3% | |
| Accepted operations | 37 | 19 | |
| Positive credit events | 81 | 42 | |
| Credited amount | 2960000 | 1520000 | |
| Recurrence events | 0 | 0 | |
| Consolidation events | 0 | 0 | |
| Empty extraction records | 10 | 12 | |
| Partial extraction records | 18 | 10 | |
| All-rejected extraction records | 53 | 69 | |
| Final unique concepts | 102 | 62 | |
| Final unique edges | 81 | 42 | |

The accepted-operation credit pool is 80,000 fixed units per operation in this runner, matching the observed final totals (37×80,000 = 2,960,000; 19×80,000 = 1,520,000).

## Per-thread funnel

The CSV contains the same table in machine-readable form. `new_unique_edges` is based on canonical admitted edge keys; `recurrence_events` is admitted events whose canonical edge already existed.

| branch | thread | output tokens | proposals | admitted | rejected | admit % | proposals/1k tokens | admitted/1k tokens | new edges | cumulative edges | cumulative concepts | empty | partial |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| OFF | 1 | 815 | 13 | 2 | 11 | 15.4% | 15.9509 | 2.454 | 2 | 2 | 4 | 1 | 1 |
| OFF | 2 | 1325 | 21 | 6 | 15 | 28.6% | 15.8491 | 4.5283 | 6 | 8 | 12 | 0 | 2 |
| OFF | 3 | 857 | 18 | 11 | 7 | 61.1% | 21.0035 | 12.8355 | 11 | 19 | 19 | 1 | 2 |
| OFF | 4 | 1269 | 17 | 7 | 10 | 41.2% | 13.3964 | 5.5162 | 7 | 26 | 27 | 0 | 1 |
| OFF | 5 | 725 | 9 | 4 | 5 | 44.4% | 12.4138 | 5.5172 | 4 | 30 | 31 | 0 | 0 |
| OFF | 6 | 1647 | 8 | 2 | 6 | 25.0% | 4.8573 | 1.2143 | 2 | 32 | 34 | 0 | 0 |
| OFF | 7 | 1273 | 8 | 0 | 8 | 0.0% | 6.2844 | 0.0 | 0 | 32 | 34 | 1 | 0 |
| OFF | 8 | 1115 | 6 | 1 | 5 | 16.7% | 5.3812 | 0.8969 | 1 | 33 | 36 | 1 | 0 |
| OFF | 9 | 1220 | 7 | 2 | 5 | 28.6% | 5.7377 | 1.6393 | 2 | 35 | 39 | 0 | 0 |
| OFF | 10 | 1013 | 5 | 2 | 3 | 40.0% | 4.9358 | 1.9743 | 2 | 37 | 40 | 1 | 0 |
| OFF | 11 | 1594 | 12 | 2 | 10 | 16.7% | 7.5282 | 1.2547 | 2 | 39 | 43 | 0 | 0 |
| OFF | 12 | 1034 | 12 | 4 | 8 | 33.3% | 11.6054 | 3.8685 | 4 | 43 | 48 | 2 | 0 |
| OFF | 13 | 1313 | 12 | 4 | 8 | 33.3% | 9.1394 | 3.0465 | 4 | 47 | 51 | 0 | 0 |
| OFF | 14 | 1429 | 5 | 0 | 5 | 0.0% | 3.499 | 0.0 | 0 | 47 | 51 | 1 | 0 |
| OFF | 15 | 1342 | 13 | 2 | 11 | 15.4% | 9.687 | 1.4903 | 2 | 49 | 54 | 0 | 0 |
| OFF | 16 | 898 | 10 | 5 | 5 | 50.0% | 11.1359 | 5.5679 | 5 | 54 | 61 | 0 | 4 |
| OFF | 17 | 974 | 18 | 3 | 15 | 16.7% | 18.4805 | 3.0801 | 3 | 57 | 67 | 0 | 1 |
| OFF | 18 | 1589 | 15 | 1 | 14 | 6.7% | 9.4399 | 0.6293 | 1 | 58 | 69 | 0 | 1 |
| OFF | 19 | 1594 | 11 | 2 | 9 | 18.2% | 6.9009 | 1.2547 | 2 | 60 | 73 | 0 | 1 |
| OFF | 20 | 1420 | 18 | 5 | 13 | 27.8% | 12.6761 | 3.5211 | 5 | 65 | 80 | 0 | 2 |
| OFF | 21 | 1140 | 4 | 2 | 2 | 50.0% | 3.5088 | 1.7544 | 2 | 67 | 82 | 1 | 0 |
| OFF | 22 | 1446 | 22 | 4 | 18 | 18.2% | 15.2144 | 2.7663 | 4 | 71 | 89 | 0 | 1 |
| OFF | 23 | 1395 | 9 | 2 | 7 | 22.2% | 6.4516 | 1.4337 | 2 | 73 | 93 | 1 | 0 |
| OFF | 24 | 1209 | 31 | 2 | 29 | 6.5% | 25.641 | 1.6543 | 2 | 75 | 95 | 0 | 0 |
| OFF | 25 | 1019 | 19 | 6 | 13 | 31.6% | 18.6457 | 5.8881 | 6 | 81 | 102 | 0 | 2 |
| ON | 1 | 2518 | 27 | 0 | 27 | 0.0% | 10.7228 | 0.0 | 0 | 0 | 0 | 0 | 0 |
| ON | 2 | 4163 | 18 | 1 | 17 | 5.6% | 4.3238 | 0.2402 | 1 | 1 | 2 | 0 | 1 |
| ON | 3 | 2826 | 13 | 9 | 4 | 69.2% | 4.6001 | 3.1847 | 9 | 10 | 15 | 0 | 2 |
| ON | 4 | 4006 | 17 | 4 | 13 | 23.5% | 4.2436 | 0.9985 | 4 | 14 | 20 | 0 | 1 |
| ON | 5 | 2066 | 12 | 1 | 11 | 8.3% | 5.8083 | 0.484 | 1 | 15 | 22 | 0 | 0 |
| ON | 6 | 4881 | 8 | 0 | 8 | 0.0% | 1.639 | 0.0 | 0 | 15 | 22 | 2 | 0 |
| ON | 7 | 4214 | 1 | 0 | 1 | 0.0% | 0.2373 | 0.0 | 0 | 15 | 22 | 3 | 0 |
| ON | 8 | 4070 | 6 | 1 | 5 | 16.7% | 1.4742 | 0.2457 | 1 | 16 | 24 | 0 | 0 |
| ON | 9 | 3467 | 19 | 0 | 19 | 0.0% | 5.4802 | 0.0 | 0 | 16 | 24 | 0 | 0 |
| ON | 10 | 3701 | 20 | 4 | 16 | 20.0% | 5.4039 | 1.0808 | 4 | 20 | 28 | 0 | 1 |
| ON | 11 | 4149 | 23 | 2 | 21 | 8.7% | 5.5435 | 0.482 | 2 | 22 | 31 | 0 | 1 |
| ON | 12 | 3771 | 8 | 3 | 5 | 37.5% | 2.1215 | 0.7955 | 3 | 25 | 36 | 1 | 0 |
| ON | 13 | 3953 | 14 | 0 | 14 | 0.0% | 3.5416 | 0.0 | 0 | 25 | 36 | 0 | 0 |
| ON | 14 | 3815 | 8 | 0 | 8 | 0.0% | 2.097 | 0.0 | 0 | 25 | 36 | 0 | 0 |
| ON | 15 | 3882 | 5 | 2 | 3 | 40.0% | 1.288 | 0.5152 | 2 | 27 | 40 | 1 | 0 |
| ON | 16 | 3076 | 23 | 2 | 21 | 8.7% | 7.4772 | 0.6502 | 2 | 29 | 43 | 0 | 0 |
| ON | 17 | 3706 | 11 | 2 | 9 | 18.2% | 2.9682 | 0.5397 | 2 | 31 | 46 | 0 | 0 |
| ON | 18 | 4190 | 12 | 3 | 9 | 25.0% | 2.864 | 0.716 | 3 | 34 | 51 | 1 | 1 |
| ON | 19 | 4153 | 8 | 0 | 8 | 0.0% | 1.9263 | 0.0 | 0 | 34 | 51 | 0 | 0 |
| ON | 20 | 4672 | 18 | 0 | 18 | 0.0% | 3.8527 | 0.0 | 0 | 34 | 51 | 1 | 0 |
| ON | 21 | 3473 | 10 | 4 | 6 | 40.0% | 2.8794 | 1.1517 | 4 | 38 | 57 | 1 | 1 |
| ON | 22 | 3860 | 3 | 0 | 3 | 0.0% | 0.7772 | 0.0 | 0 | 38 | 57 | 1 | 0 |
| ON | 23 | 3971 | 10 | 0 | 10 | 0.0% | 2.5183 | 0.0 | 0 | 38 | 57 | 0 | 0 |
| ON | 24 | 3372 | 14 | 1 | 13 | 7.1% | 4.1518 | 0.2966 | 1 | 39 | 59 | 0 | 1 |
| ON | 25 | 3679 | 7 | 3 | 4 | 42.9% | 1.9027 | 0.8154 | 3 | 42 | 62 | 1 | 1 |

## Provenance, credit, recurrence, and consolidation

- Every one of the 123 admitted observations was constructed by the runner as `source_role=external`, `dependence=external_supported`, `eligible=true`, `relevant=true`, `covered=true`, and `present/supported/affirmed`. There is no observed provenance or dependence difference between branches.
- Therefore all 123 admitted observations were credit-eligible and became positive learner-credit events. Rejected proposals were discarded before learner transition; the receipt does not retain learner zero-credit rows for them.
- OFF had 37 accepted operations and ON 19. Each operation awarded the fixed 80,000-unit pool across its accepted targets. Final credited amounts were 2,960,000 and 1,520,000.
- No canonical edge recurred in either branch: admitted events equaled final unique edges (81/81 and 42/42). No consolidation event is visible: every final learner value has one rolling credit/lifetime group and `last_consolidation_opportunity=1`.
- Canonical admitted semantic duplicates were zero in both branches. Raw rejected-proposal duplicates cannot be measured because rejected proposition text was not persisted.

## Rejection, extraction, and repair limits

- The runner’s only rejection boundary is the NLI gate: entailment must be at least 0.45 and strictly greater than contradiction and neutral. All 242 OFF and 273 ON rejected items therefore crossed that common gate, but the receipt lacks their individual scores, so threshold-versus-margin sub-reasons cannot be separated.
- Empty extraction records (zero relationships) were OFF 10/100 and ON 12/100. Partial records (at least one admitted and at least one rejected) were OFF 18 and ON 10. All-rejected nonempty records were OFF 53 and ON 69.
- No malformed/repair event was observed. This runner would fail on malformed specialist JSON rather than retain a repair taxonomy, so “zero observed” does not prove malformed output was impossible.

## Introspection and SAA

- Introspection accepted zero adjustments in both branches. OFF: 23 `NO_CHANGE`, 2 `ABSTAINED_MALFORMED`; ON: 21 `NO_CHANGE`, 3 `ABSTAINED_MALFORMED`, 1 `ABSTAINED_NO_TARGETS`. It did not contribute to graph divergence.
- SAA treatment was healthy after cold start: OFF had 97 healthy and 3 cold-start coordinates; ON had 95 healthy and 5 cold-start coordinates. Nonempty payloads were present on all 192 healthy coordinates. Distinct landing counts were OFF 44 and ON 32.

## Matched funnel examples

- **Thread 1, dry garden:** OFF produced 13 proposals and admitted 2; ON produced 27 and admitted 0. ON’s longer opening answer included actionable advice (“Deep Watering”, “Mulch”, “Prioritize”, “Shade”), but the preserved assessor record contains only aggregate rejection counts, so the exact rejected propositions and scores cannot be recovered.
- **Thread 3, cooking:** OFF admitted 11 of 18 proposals; ON admitted 9 of 13. ON’s response explicitly framed a “Mediterranean/Mediterranean-style meal”; its admitted edges included `ingredients related Mediterranean/Mediterranean-style meal` and `tuna part_of Tuna Sandwich`. OFF’s admitted edges included `vinaigrette depends_on olive oil` and `dressing supports bread`. This is a direct content/topology divergence, not a provenance-credit difference.
- **Thread 16, extreme weather:** OFF admitted 5 of 10 proposals; ON admitted 2 of 23. OFF’s accepted examples included `Water Storage part_of Safety Net`; ON accepted `extreme weather causes cold snap` and `decision tree related extreme weather`. ON generated more extraction candidates but most failed the same NLI gate.
- **Thread 24, festival failure:** OFF admitted 2 of 31; ON admitted 1 of 14. Both branches produced long reflective answers, but admission remained sparse; neither branch had recurrence/consolidation evidence.

## Why 81 edges versus 42?

**Demonstrated:**
1. ON had slightly fewer raw proposals (315 vs 323), and far fewer proposals per visible output token (3.36 vs 10.54 per 1,000).
2. ON rejected a larger fraction at the common NLI gate (86.7% vs 74.9%).
3. Consequently ON admitted 42 unique edges versus OFF’s 81; all admitted edges were new events, so the difference was not caused by recurrence.
4. Provenance/dependence/eligibility and learner credit rules were the same for admitted observations. Introspection accepted no adjustments in either branch.

**Not established:**
- The receipt cannot distinguish which rejected NLI candidates failed the entailment threshold versus lost the contradiction/neutral margin, because rejected scores and text were not retained.
- It cannot measure raw-proposal duplicate redundancy or detailed malformed/repair behavior beyond the aggregate records.

**Plain-English answer:** OFF ended with 81 edges because its visible replies yielded a higher density of proposals that survived the same admission gate, and it had 37 credit-bearing operations. ON’s much longer reasoning-enabled replies did not translate into more extractable/admissible relationships: its proposal density was lower and its rejection rate higher, leaving only 19 credit-bearing operations and 42 unique edges. The evidence does not show that ON had worse provenance, less learner credit per admitted item, recurrence differences, or introspection suppression; those mechanisms were effectively matched or unused.

## Remaining uncertainty

The preserved run was designed to retain compact developmental evidence, not every rejected GLiNER proposition or NLI score. A future diagnostic would need raw candidate-level extraction/NLI records to explain individual rejection causes, but this report makes no model calls and does not reconstruct missing data.
