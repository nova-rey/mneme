# MNEME P2.3 extractor relationship normalization receipt

- Date: 2026-09-24
- Historical coordinate reviewed: `extraction-s1-e7`
- Historical runs preserved: `p2-pilot-recovery-20260924l`, `p2-pilot-recovery-20260924m`
- New provider calls: 0
- Offline correction commit: this receipt's publishing commit

## Forensic disposition

The immutable source was:

> After another hot day, the mulched bed still held moisture for the seedlings.

Gemma used `holds` for mulched bed → moisture and `supports` for moisture →
seedlings. The first relation means physical retention/containment. It is a
useful relation absent from the prior vocabulary, so the canonical prospective
relation is `retains`; `holds` is normalized deterministically at the
extraction boundary. No prompt prohibition or stochastic resampling was used.

The raw extractor label remains in the persisted provider result. The
normalized residue, alias decision, and any rejected items are exposed through
the versioned `relationship-normalization-v1` report. An unrelated unsupported
label such as `processed by` is rejected item-wise when keyed; routes depending
on it are rejected, while independently valid graph evidence remains eligible.
Malformed structure, unsupported concepts, invalid source quotations, missing
endpoints, and other validation failures still fail closed.

## Offline evidence

- `holds` → `retains` preserves the source-backed edge and route continuity.
- `processed by` is rejected without discarding an independently valid edge.
- Raw provider JSON remains unchanged and separately inspectable.
- Alias/rejection decisions are deterministic across replay.
- Historical invalid-output fixtures remain fail-closed except for the newly
  intended item-level unsupported-edge behavior.

Validation before any live continuation:

- focused interpretation tests: pass;
- complete pytest suite: pass;
- Ruff: pass;
- strict mypy: pass;
- package/fresh-install smoke: pass (wheel built and installed in a fresh venv).

The preserved 157 returned calls and all prior receipts remain unchanged. The
next live action is a bounded continuation from the failed `s1-e7` coordinate,
not a restarted pilot or favorable resampling campaign.
