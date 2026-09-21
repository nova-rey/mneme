# MNEME P2.3 assessor coverage/polarity v9 offline receipt

**Disposition:** offline correction passed; no provider call made  
**Current contract:** `p2-assessor-v6` / `p2-assessor-production-v8` / `p2-provenance-v1`

The assessor contract is prospectively versioned after the Q3 negation review.
Proposition coverage (`present` / `absent` / `unknown`), relation support
(`supported` / `contradicted` / `unsupported` / `unknown`), and expression
polarity (`affirmed` / `negated` / `not_expressed` / `unknown`) are independent
fields with fail-closed cross-field validation. Explicit negation is represented
as `present` / `contradicted` / `negated`; it is never represented as absence.
Incomplete required-source coverage is `unknown`, never `absent`.

Supported and contradicted observations retain uniquely resolved exact evidence
quotes. Absent observations require complete available-source coverage and no
quotation. Unknown observations require incomplete coverage and an explicit
reason. The prompt now states these meanings and the allowed combinations
directly to the assessor.

The previous `p2-assessor-v5` results remain readable only through the explicit
historical reader, and the older v4 vocabulary remains archival. Historical
provider results and receipts were not rewritten.

The learner boundary was audited without adding a contradiction-learning rule:
the durable observation retains `contradicted` / `negated` evidence, while the
positive-credit candidate path admits only `supported` / `affirmed` observations.
Contradiction therefore earns no positive support, is not converted to absence,
does not create a contextual consequence, and replays with the same disposition.
The existing conflicting-duplicate fail-closed rule remains active.

## Offline validation

- focused assessor, qualification, publication, replay, and learner tests: passed;
- complete pytest suite: **318 passed**;
- Ruff: **passed**;
- strict mypy: **passed** (`50` source files);
- wheel build and fresh-install `mneme --help` smoke: **passed**;
- provider calls: **0**.

The next live action is one fixed Q1/Q2/Q3 qualification using the new v6/v8
contract. It remains subject to the existing Phase Two ceiling and stop rules;
this receipt does not authorize or consume pilot calls.
