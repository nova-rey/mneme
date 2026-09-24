# P2 contingent reviewed-continuation correction

**Status:** OFFLINE VALIDATED; READY FOR PRESERVED LIVE CONTINUATION  
**Provider calls:** 0

The scientific review resolution authorizes the preserved contingent run to
continue at interactive turn 9 after the historical interpretation stop. The
runtime now records the review disposition in the durable study progress and
uses a prospective post-correction measurement segment for stop evaluation.

The historical cumulative record is unchanged: turns 0–8 remain immutable,
6/9 interpretations are trustworthy, and the three terminal missing
measurements remain `measurement_unknown / interpretation_unavailable`. The
new segment counters are additive and do not erase or relabel those records.
When the review record names `resume_turn: 9`, the interactive branch evaluates
the measurement-quality rule only over turns 9 onward while retaining the full
cumulative counters. The ordinary stop rule remains active within that
segment, and the review record cannot authorize a rewind before the preserved
coordinate. The open-loop branch retains its ordinary independent counters.

Focused regression coverage proves that a 6/9 historical prefix plus two
successful post-correction turns retains the cumulative totals while reporting
a separate 2/2 post-correction segment, and that only an explicit approved
continuation record supplies the reviewed segment start. Existing stop-guard,
restart, transcript, and failure-tolerance tests remain in force.

Validation before live continuation:

- `pytest -q`: 395 passed;
- Ruff: passed;
- strict mypy: passed;
- wheel build: passed;
- no provider call was made for this correction.

