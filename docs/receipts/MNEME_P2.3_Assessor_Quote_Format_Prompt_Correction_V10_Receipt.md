# MNEME P2.3 Assessor Quote Format Prompt Correction V10

- Date: 2026-09-24
- Scope: bounded prompt clarification after preserved recovery-v5 stop
- Provider calls: 0
- Historical evidence: unchanged

The production assessor prompt now includes a concrete nested-Markdown example:
when immutable source text contains `* **"text"**`, the returned quotation must
contain exactly those markers; `* "text"` is invalid. Strict source-bound
validation, assessor semantics, provenance resolution, learner behavior, and
acceptance criteria are unchanged.

Offline validation: 355 pytest, focused assessor/pilot regressions, Ruff,
strict mypy, wheel build, and fresh-install smoke passed.
