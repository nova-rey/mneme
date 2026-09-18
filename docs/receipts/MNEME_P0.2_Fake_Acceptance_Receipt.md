# MNEME P0.2 FakeHost acceptance receipt

Date: 2026-09-18
Baseline: implementation working tree after approved P0.2 plan

The network-free demonstration completed with a temporary store:

- lineage A: three accepted episodes, current revision `3`;
- checkpoint `33333333-3333-4333-8333-333333333333` created and reopened read-only;
- lineage B: forked from A at revision 3 with copied ancestor history, then one independent episode at child revision `1`;
- B retained A as its parent and exposed four inherited-plus-local episodes;
- backup of B reopened independently;
- accepted-operation retry returned the original receipt without a second revision;
- FakeHost generation was identical when administrative lineage/run/checkpoint metadata differed;
- process interruption before commit recovered the prior revision;
- failed host generation became `UNCERTAIN` without advancing the revision.

Machine-readable local output is in `artifacts/p02_acceptance.json` (ignored runtime
artifact; it is not a source-of-truth database).

The bounded real-Gemma persistence step subsequently passed using a separate fresh store.
Its sanitized receipt is `artifacts/p02-real-gemma-receipt.json`; the credential and raw
conversation are absent from that receipt. The real store was reopened read-only and its
accepted revision, host provenance, and integrity checks passed.
