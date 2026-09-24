# Contingent Conversation / Interloper Study

This is the additive P2 supplement `P2-SUPPLEMENT-INTERLOPER-01`. It tests one
interactive environment against a matched open-loop environment while keeping
MNEME's existing Gemma developmental host and learner unchanged.

## Contract

The scientific identity is `contingent-conversation-interloper-20260924`,
contract revision 1. Interactive and open-loop branches each contain 24
participant/Gemma pairs in chapters A (cooking), B (balcony plants), and C (a
fictional remote winter habitat). The Qwen interloper sees actual Gemma replies
only in the interactive branch. The open-loop branch is generated and frozen
before subject execution and never receives fabricated replies.

The exact system prompt, scenario card, bounded-context rules, host bindings,
budget, and readout probes are encoded by
`mneme.experiments.contingent.ContingentStudy`. Partner records are synthetic
environment evidence, tagged `synthetic_environment_model`; they are not human
testimony or persistent self-state.

## Gates

1. **Wire and verify:** production-path continuity/exposure preflight, role and
   source-mask isolation, bounded context, durable coordinate tests, package
   smoke, and CI.
2. **Run:** four-call interloper fit check, then sequential interactive and
   open-loop branches with checkpoints and frozen readouts.
3. **Inspect and report:** readable transcripts, source-linked opportunities and
   routes, readout examples, call ledger, and separate implementation,
   condition, adequacy, and behavioral dispositions.

The historical P2.3 run remains unchanged and remains
`COMPLETED_INADEQUATE`. This supplement is one exploratory pair, not a powered
causal study and not Phase Three.

## Offline preflight receipt

The production-path authored-data check is recorded in
`docs/receipts/MNEME_P2_Contingent_Interloper_Offline_Preflight_Receipt.md`.
