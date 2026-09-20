# MNEME P2.3 assessor polarity contract regression receipt

**Disposition:** offline contract audit passed; no provider call made

The current production assessor contract is `p2-assessor-v5` with prompt
`p2-assessor-production-v7`. It separates proposition coverage from relation
support and expression polarity, requires exact source-bound evidence for
present observations, and rejects inconsistent combinations. The learner
boundary preserves contradicted observations without awarding positive credit
or converting them into absence. Historical v4 receipts remain archival and
unchanged.

This audit adds paired regression coverage for an explicitly insufficient
statement (`present` / `unsupported` / `unknown`) and a double-negative
affirmation (`present` / `supported` / `affirmed`). Existing tests continue to
cover positive affirmation, explicit negation, complete-coverage absence,
unavailable-source unknown, exact quotation resolution, provenance precedence,
replay, and contradiction-safe publication.

Validation on the audited worktree:

- `pytest`: 312 passed
- Ruff: passed
- strict mypy: passed
- wheel build and fresh-install smoke: passed
- provider calls: 0

The latest fixed live qualification remains the preserved polarity-v8 pass;
this receipt does not reclassify historical results or spend another live
qualification budget. The next provider-backed action must use a newly changed
behavioral contract or remain unnecessary rather than repeating an unchanged
qualification.
