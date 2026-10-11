# MI1 C14 atomic-recall diagnostic

C14 failed its frozen calibration gate: Gemma retrieved **0/32** facts from selected-site latent banks at either tested gain, while it read **8/8** visible facts for each polarity and returned `unknown` in **8/8** no-bank and **8/8** cue-only controls. All 64 calls completed normally. No held-out confirmation calls were authorized by the gate.

This was a one-hop codeword lookup designed to remove the multi-step graph reasoning that confounded C13. It therefore establishes that the tested bank path did not make an exact stored fact behaviorally retrievable in these fixtures. It does not by itself decide whether the method can carry process priors or associative framings.

The failed coordinate was not caused by an absent bank attachment or lack of numerical routing. A prefill-only capture of the exact model-visible prompt for `C14-A25-latent_A_selected_fourfold-34201` recorded 154 prompt tokens, 42 query layers, and the 12 appended bank slots. At the final prompt query, the 16 selected query heads assigned the bank a mean attention mass of **0.498** (range **0.055–0.970**). Across all 336 heads the mean was 0.0237. The request journal independently records the expected bank fingerprint, SHA-256, enabled state, and attachment revision. Despite this, the final answer was `unknown`; reasoning explicitly said it had no actual internal record and would have to simulate the search.

That result localizes the failure to a gap between numerical attention access and semantic readout, or to the bank representation/operation after routing. The capture measures attention probabilities, not whether the selected values preserve or decode the fact. Earlier C11 instrumentation also observed changed downstream hidden states, so “the bank had no computational effect” is not supported. The exact post-attention value contribution to the answer remains unresolved.

| Condition | Exact hits | Finish reason |
|---|---:|---|
| No bank | 8/8 `unknown` | stop 8/8 |
| Assertive cue, no bank | 8/8 `unknown` | stop 8/8 |
| Visible A / B | 8/8 each | stop 16/16 |
| Latent A / B, 2× | 0/8 each | stop 16/16 |
| Latent A / B, 4× | 0/8 each | stop 16/16 |

The complete compact rates, coordinate list, and hashes are in the [machine-readable readout](MNEME_Phase_4_MI1_C14_Calibration_Readout_20261011.json). Canonical requests and complete outputs remain at `/home/nyx/mneme-artifacts/phase4-mi1/c14-calibration/evidence/`; the 110 MB exact-prompt attention capture remains at `/home/nyx/mneme-artifacts/phase4-mi1/c14-calibration/diagnostics/A25-latent-A-4x-seed34201.mi1qry` (SHA-256 `926d3646c0b8f06d0a3a3da15ab9acf70cf3e9e8c609bcf68485a2e239b54316`).

This is a diagnostic failure, not a final MI1 disposition. The next investigation must distinguish whether the selected bank values carry usable content and whether this host/runtime’s source-token K/V interpretation is faithful at generation time. No MNEME state was loaded or changed.
