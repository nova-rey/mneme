# Phase 4 MI1 continued resolution

Can our local Gemma use a whole neighborhood supplied through side memory rather than its ordinary prompt?

**Memory Inception on our Gemma does not work well enough to advance.** The local MI1 path demonstrably routes side-bank K/V into Gemma attention and changes intermediate computation, but the preserved controlled tests do not show reliable recovery of bank contents or attributable use of a structured neighborhood. The completed Test A/B/C and removal/reuse results already answer the feasibility question; another calibration is not needed to explain the 8/8 versus 2/6 visible-control discrepancy.

This is an additive resolution to the historical receipts. It does not rewrite their run classifications or claim that Memory Inception must fail on other hosts or implementations.

## Why the visible controls differed

The earlier 8/8 result was not a hidden-bank result. It used four short, single-target directed chains with their rules printed in the ordinary user prompt. C2 used three materially harder visible tasks: two candidate targets, disconnected distractor edges, exception/inactive-node logic, varied relation verbs, and a required complete named path. Its six visible calls yielded 2/6:

| C2 result | Count | Diagnosis from the retained response |
|---|---:|---|
| Complete visible answer/path | 2/6 | Correct under the frozen rubric. |
| Correct chain in reasoning, abbreviated labels in final path | 1/6 | The final answer used `A -> B -> C -> D`; the frozen criterion required the full names. This was an answer-format omission, not a scorer/parser error. |
| Incorrect reachability or invented relationship | 3/6 | The reasoning included an inactive/disconnected route or a link absent from the visible rules. These are substantive task-reasoning errors. |

C3 then returned to the earlier simple visible fixture family and scored 8/8 on the visible positive condition after the scorer recognized the model's complete path syntax. This supports the diagnosis that the 2/6 calibration result reflected the harder fixture demands, rather than a changed model, seed path, or hidden-bank state. The frozen C2 artifacts remain valid evidence that those harder tasks failed their gate; C3 does not retroactively change that result.

The 8/8 and 2/6 figures therefore answer different control questions. The 8/8 shows the task form can be solved when short rules are plainly visible. The 2/6 shows the more demanding multi-edge calibration was too difficult to serve as a clean positive control. Neither is evidence for side-memory efficacy.

## What the side-memory evidence establishes

The full frozen Test A/B/C suite completed 268/268 coordinates: 144 Test A retrieval calls, 108 Test B associative-use calls, and 16 Test C lifecycle calls. Across the relevant evidence:

| Question | Observed result | Meaning |
|---|---|---|
| Did bank material reach the isolated attention path? | Yes. Bank fingerprints matched; selected heads attended to appended slots. C11 measured mean bank attention mass 0.448 across 16 selected heads at the final prompt token, with zero mass on unselected heads. C14 measured mean selected-head bank mass 0.498. C11 also measured downstream query-state changes. | Mechanical access and computation change are demonstrated. They do not establish semantic retrieval. |
| Did bank A/B content control the requested relationship answers? | No. Test A latent A and B each scored 0/24; no-bank and irrelevant-bank controls each scored 23/24 `unknown`. | Counterfactual content-specific behavioral transmission was not demonstrated. |
| Did it make whole neighborhoods available in ordinary tasks? | Not established. Test B's 108 outputs did not show a repeatable latent-correct effect distinguishable from no-bank, irrelevant-bank, altered-topology, or advice implied by the task itself. | Output changes alone are not attributable evidence. |
| Did removal/reuse recover an effect? | Bank attach, replacement, disable, restore, and fingerprints worked. All 16 Test C outputs were `unknown`, including fresh A, replacement B, disabled, restored A, and new-bank coordinates. | Physical lifecycle works; behavioral removal/restoration cannot be credited because there was no established effect to remove or restore. |
| Did broader routing repair access? | No. C17 exposed the assistant-turn bank to all 42 query layers and all 8 heads, using all 24 KV-source layers. Latent exact retrieval was 1/8 for A and 0/8 for B; the sole matching A output had no reasoning trace. Other outputs were malformed or unrelated. | Broad access was disruptive and did not establish semantic use. |

Additional bank construction and cue attempts did not change the conclusion: C10 tested descriptor-contextualized-only and raw-plus-contextualized banks (0/8); C14 tested selected-site atomic facts at two gains (0/32); C16 tested assistant-turn memory encoding (0/16). C11 recalibrated selected query sites and still had no retrieval. C15 tested tokenization/role variants. These attempts and their unsuccessful coordinates remain preserved.

## Resolution and remaining uncertainty

The best-supported failure explanation is at the **semantic readout boundary**: numerically attended K/V and measurable hidden-state changes did not become dependable, bank-specific output behavior on this Gemma Q2/llama.cpp path. The evidence rules out a missing bank attachment, absent selected-head mask, and the C2 visible-control mismatch as explanations for the entire failure. C16 reasoning explicitly reported that the hidden note was unavailable despite the bank being attached; Test A and C14 provide independent answer-level evidence.

The evidence does **not** isolate whether the remaining limit is Gemma's learned response to side-loaded K/V, Q2 quantization, a Gemma-specific attention/KV semantic mismatch in the isolated port, or an interaction among these. Attention mass and query-state movement are not enough to prove the value information is decoded as intended. The result is therefore a supported disposition for this tested host and implementation, not a universal impossibility claim.

No further local calibration is justified for this MI1 path: it would not repair the missing behavior demonstrated across the completed direct-recall, relational-use, bank-replacement, and all-head tests. **Recommendation: park this local implementation; do not integrate it into MNEME.** Any different attention implementation or host requires a new frozen qualification rather than inheriting these results as a pass.

## Costs and evidence durability

The 268-call scored Test A/B/C suite recorded 5,217.55 seconds of request latency (median 14.93 s; p90 34.83 s). Bank construction across 38 recorded source builds averaged 1.457 s per encode plus 0.031 s per package/configure; a typical selected-site bank was about 9.23 MB.

To close the lifecycle-cost gap, I restarted only the isolated server and ran a no-generation API benchmark using a frozen C14 A/B bank pair: 2 warm-up cycles followed by 25 measured attach → replace → disable → clear cycles. Each operation succeeded and returned the expected enable/fingerprint state. Measured loopback HTTP medians were attach 9.18 ms, replace 9.31 ms, disable 1.51 ms, and clear 1.22 ms; attach p90 was 9.30 ms and replace p90 was 11.03 ms. These are warm-cache steady-state timings and include the HTTP request and response plus file read/validation for attach/replace. They exclude bank encoding, server startup, artifact transfer, generation, and SAA processing. The final bank was empty/disabled; the server was stopped and port 18472 verified closed. The raw journal, plan, script, and summary remain outside Git under `/home/nyx/mneme-artifacts/phase4-mi1/continued-resolution/lifecycle-cost/`; summary SHA-256 `549932477704e8262b5d808413f6003df290cf68deffd0dc51e76cf191f44907`, raw-journal SHA-256 `a341b96188883d57a0be4b96da96723b65a5c2ecfee26b054eeba54f700d4ce9`.

Combining the previously measured mean encode and package/configure times with this measured attach median gives an indicative local path of about 1.50 seconds from encoded source to attached bank, excluding model initialization and file transfer. This is a cross-run arithmetic estimate, not a single end-to-end timed sample.

Test C also encoded and attached a new four-edge neighborhood (`Daxi activates Bero; Bero activates Cuni; Cuni activates Efo; Efo activates Gaxi`) in two recipient contexts. It used the already frozen sparse selector with the same 16 query sites and selector hash; only the bank was normally encoded, and no per-neighborhood selector recalibration was performed. Both responses were `unknown`, so this establishes low-cost bank construction/attachment, not reusable semantic access.

All required A/B/C conditions, including removal/reuse, were already completed and durably indexed. Test A/B/C evidence index SHA-256: `bf2968b9bd8ae26b533a32c4c1feb5c49f21898ab6866ea6ded93f289beb33db`. C17 calibration score SHA-256: `6c3b325485c072b8cc0c3e6f237195cf973989c3a1b870b1f3b80c006de99697`. Full raw requests, reasoning, outputs, and tensor artifacts remain outside Git under `/home/nyx/mneme-artifacts/phase4-mi1/`.

Supporting readable receipts: [C2 calibration gate](MNEME_Phase_4_MI1_Calibration_Final_Gate_20261010.md), [C3 task-form diagnostic](MNEME_Phase_4_MI1_C3_Result_20261010.md), [C10 contextual-bank result](MNEME_Phase_4_MI1_C9_C10_Diagnostic_Result_20261010.json), [C11 selected-site readout](MNEME_Phase_4_MI1_C11_Readout_20261011.md), and [prior final disposition](MNEME_Phase_4_MI1_Final_Disposition_20261011.md).
