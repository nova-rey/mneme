# MI1 C3 diagnostic result

C3 is diagnostic evidence only; it is not scored Test A/B/C and does not qualify MI1 for MNEME integration.

## What the 44 coordinates show

The four visible-text controls scored **8/8** once the scorer recognized Gemma's complete path expressed with LaTeX `\rightarrow` separators. This exactly matches the eight earlier visible-positive fixtures and shows that the simple one-chain task form is currently understandable.

All 8 no-bank controls reached the 2,048-token limit while reasoning about the absence of rules and produced no visible final answer. The generic-memory-cue/no-bank controls did the same (2/2). That is a failed negative-control output contract, not a valid `unknown` response, and it cannot qualify an A/B/C comparison.

The latent conditions did not yield a usable final answer:

- Sparse/moderate: 0/8 correct. In inspected traces Gemma stated that the rules were absent from the ordinary prompt and did not finish a final response.
- Broad/moderate: 0/8 correct; outputs included empty finals, code fences, and repeated/garbled short tokens.
- Broad/strong: 0/8 correct; outputs repeatedly emitted target or unrelated labels, without a directed path. The same pattern occurred in the two generic-cue/strong coordinates.

All 44 requests and responses are durably stored. The 26 attached-bank coordinates reported the exact expected parsed-bank fingerprint. Thus bank misbinding is not the explanation for C3's poor latent outputs. The C3 evidence is consistent with two separable issues: the no-bank prompt needs a bounded, explicit `unknown` response form; and broad/strong side-bank exposure can disrupt generation, while sparse/no-cue cases do not show finished behavioral uptake. It does not yet establish why the latent bank is not converted into a correct final answer.

## Next diagnostic

C4 freezes a two-factor diagnostic before generation: a terse two-line answer contract (informed by C2's successful negative controls) and a generic private-memory cue, crossed with no-bank, visible, sparse-latent, and broad-latent conditions. The prompt-cue and no-cue pairs are text-identical between no-bank and latent conditions. C4 retains the same four simple fixtures, seeds, model, sampler, reasoning mode, and 2,048-token allowance. It excludes C3's broad/strong gain because its repetitive failures are already informative and repeating it would not separate cueing from excess exposure.

Full raw per-call reasoning and token streams remain outside Git at `/home/nyx/mneme-artifacts/phase4-mi1/calibration-C3/evidence/`. The compact [machine-readable receipt](MNEME_Phase_4_MI1_C3_Result_20261010.json) gives the plan/index/score hashes and per-coordinate outcome fingerprints.
