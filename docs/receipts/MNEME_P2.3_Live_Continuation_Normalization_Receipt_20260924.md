# MNEME P2.3 live continuation and relationship-normalization receipt

- Date: 2026-09-24
- Historical pilot state: preserved; no pilot restart
- Historical returned calls before these continuations: 187
- Continuation q returned calls: 59
- Continuation q interrupted coordinate: `evaluation-s0-p6-r1`
- Continuation r returned calls: 107
- New returned calls in q+r: 166
- Cumulative returned campaign calls: 353
- Nominal ceiling: 299
- Operational contingency ceiling: 399
- Remaining operational allowance after q+r: 46
- Provider cost: not available from the provider receipts

## Relationship decision

The preserved `s1-e7` source says:

> After another hot day, the mulched bed still held moisture for the seedlings.

Gemma used `holds` for the mulched bed retaining moisture and used `supports`
for moisture supporting seedlings. `holds` therefore expresses physical
retention/containment. It is not equivalent to `supports` or `causes`, and the
old relationship vocabulary lacked a neutral retention relation. The
prospective canonical relation is `retains`; `holds` is normalized to it by
the versioned deterministic extraction boundary. Raw provider output remains
unchanged. No prompt prohibition, fuzzy matcher, or favorable resampling was
used.

## Continuation evidence

Continuation q resumed the preserved `s1-e16` coordinate, admitted its valid
`protects`/`prevents` material, and completed the developmental schedule. It
then entered frozen evaluation and stopped when the filesystem could not write
the next reservation. Fifty-nine provider results are returned and durable;
the empty `evaluation-s0-p6-r1.json` is retained as an interrupted
pre-dispatch reservation and has no provider result. The q run is preserved
unchanged.

Continuation r copied q's subject stores and frozen checkpoint, loaded q's
persisted progress, skipped all completed developmental and evaluation
coordinates, and resumed at the incomplete evaluation boundary. It returned
107 evaluation calls. No coordinate was dispatched twice across q+r; the
combined continuation ledger contains 144 distinct returned evaluation IDs.
The copied checkpoint digest is identical in both runs.

The raw r report recorded `development_completed=58` because an accepted
response whose extraction had failed was counted again when its extraction
recovery resumed. The schedule itself contains 48 unique developmental
coordinates. The offline counter correction now counts unique coordinates;
replaying the persisted r progress under that rule yields:

- 48 unique developmental coordinates;
- 48 valid extractions;
- 8 permitted extraction repairs;
- 48 assessor publications;
- 23 admitted relationships;
- 144 frozen evaluations;
- engineering adequacy: `true`.

The raw q/r reports and artifacts remain historical evidence; this correction
does not rewrite them.

## Isolation and coverage audit

All 144 evaluation receipts have equal developmental-state-before and
-developmental-state-after tuples. The private checkpoint digest is stable
across q and r. Evaluation artifacts are outside the lineage stores and no
evaluation operation was accepted as developmental history.

The preserved subject stores expose 23 admitted relationships and a bounded
multi-hop route in the child graph (`e1 → e2`), plus source-backed external,
current-input-echo, absent/unknown, and no-identified-link observations.
The observations and learner updates are retained for the separate pilot
adequacy/research audit; this receipt makes no claim of individuality,
personality, or causal developmental differentiation.

## Offline correction and validation

The resume counter fix is limited to `PilotStudy`: progress and reports count
unique stable developmental coordinates rather than cumulative accepted
transitions. A regression seeds a recovery with an already accepted but not
yet completed coordinate and proves the completed report remains 48 and
engineering-adequate.

Validation after the correction:

- focused pilot tests: 6 passed;
- complete pytest: 362 passed;
- Ruff: passed;
- strict mypy (`mypy src/mneme`): passed;
- wheel build and fresh-install CLI smoke: passed;
- provider calls for the correction: 0.

Historical failed calls, q's filesystem interruption, and all raw provider
results remain unchanged.
