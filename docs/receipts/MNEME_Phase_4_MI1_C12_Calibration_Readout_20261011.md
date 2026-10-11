# Phase 4 MI1 C12 calibration readout

**C12 did not qualify latent-bank readout.** The exact predeclared gate failed: Gemma answered all hidden-bank coordinates `unknown` at every tested bank prior, while visible-bank controls remained accurate and unknown controls behaved as expected. No C12 held-out generation was run.

The frozen matrix used four new two-edge directed-reachability fixtures, two seeds, and eleven conditions (88 completions). Results below use strict final-label equality; a missing final answer is a failure. The predeclared threshold was at least 7/8 for each latent polarity at one shared bank prior, with visible and unknown controls also at least 7/8.

| Condition | Correct | Interpretation |
|---|---:|---|
| No bank | 8/8 unknown | Unknown control passed |
| Generic side-memory cue, no bank | 8/8 unknown | Cue did not induce guesses |
| Visible bank A / B | 8/8; 7/8 | Visible comprehension passed narrowly for B |
| Latent A, 1x / 2x / 4x prior | 0/8 at each | No correct hidden-bank retrieval |
| Latent B, 1x / 2x / 4x prior | 0/8 at each | No correct hidden-bank retrieval |
| Irrelevant latent bank, 4x | 8/8 unknown | Irrelevant-bank control passed |

Across all latent A/B/irrelevant responses, none of the 112 individual source-fact strings was reproduced in reasoning. In inspected latent examples Gemma repeatedly says that no graph or record was provided, even though the bank endpoint acknowledged the expected attached-bank fingerprint. The two `finish_reason=length` coordinates were one latent B fourfold response and one visible B response; both have empty final content and score as failures. The other 86 calls finished normally.

## Diagnosis

This does not look like a missing-bank or selected-head-mask failure. A separate no-generation capture used the exact 129-token C12 A13 prompt and the attached A13 fourfold bank (17 bank-token slots). Across its 16 frozen selected query sites, the final prompt query assigned a mean 0.3043 attention mass to bank slots (minimum 0.2808, maximum 0.3539). Unselected heads had zero bank mass. The native server also acknowledged the expected fourfold bank fingerprint during generation. These observations establish attachment and material selected-site attention; they do not establish that the model decoded the bank's meaning.

The visible-text path correctly solved the same synthetic reachability task, and the same selected bank content failed at 1x, 2x, and 4x prior. Increasing the per-slot bank-logit prior therefore did not rescue the observed semantic readout. The evidence supports a model/readout limitation under this prompt and bank interface, rather than a simple missing attachment. It does not yet identify whether the remaining cause is bank representation, selected-site choice, instruction framing, or Gemma's inability to use this latent side context.

The cue-only control's perfect abstention is useful: the generic cue did not itself cause answers. It also reveals that Gemma interprets “may be available” as compatible with no accessible record. A justified next diagnostic should make availability explicit while preserving a no-bank false-positive control, and test whether the sparse selector is the limiting path by comparing it with broad query-site access. The wording and matrix must be frozen before those calls.

## Evidence and accounting

The pre-generation freeze is [C12 calibration freeze](MNEME_Phase_4_MI1_C12_Calibration_Freeze_20261011.json), SHA-256 `66d61ff220d002db55e48089ff994a87ec90b481f1b4a3f1a2c2922aab3e0272`. The compact coordinate scoring, condition rates, response hashes, and exact capture metadata are in [C12 machine-readable result](MNEME_Phase_4_MI1_C12_Calibration_Readout_20261011.json). Canonical streamed reasoning and outputs remain outside Git in `/home/nyx/mneme-artifacts/phase4-mi1/c12-calibration/evidence/`; its `index.json` SHA-256 is `fcf1ea0c477c84359b817819fd7b7935fe48c405edb225d9b4d30347ce5a03ed`.

The exact-prompt no-generation query/attention capture remains local at `/home/nyx/mneme-artifacts/phase4-mi1/c12-calibration/A13-mi1-exact.mi1qry`, SHA-256 `a8eff36e7b5050b7c4c4640c2c0631dda1ba9d557f5462cf50a5b0fafa8743c3`. The exact chat-template prompt SHA-256 is `8527979fc3c226e3bc3bdba98fa3307ad255455ec1eebf8fd43dd63d9cbb182f`; the selected A bank variant SHA-256 is `49572c82726c37b383596424c611f88334e068b34a31da85a6bd3c2625d7ea33`.

C12 completed 88/88 calls between 16:26:50 and 16:40:16 UTC (14 minutes by response timestamps). The cumulative campaign ledger is 880 generations, including 792 preceding calls. No bank facts or outputs were written into MNEME developmental history. The isolated server was restarted after the capture; health returned `ok`, the MSI was on AC power, and observed GPU temperature was 48 °C at idle.

**Disposition:** C12 calibration failed; MI1 efficacy remains unestablished. This is not yet the final WORKS/DOES NOT WORK disposition. The calibration evidence rules out the specific weak cue / narrow selected-site / 1x–4x prior configuration and motivates the frozen accessibility-and-routing diagnostic described above. No held-out coordinates were run and no calibration threshold was relaxed.
