# MNEME P2.3 Extractor v4 Confidence Prompt Correction

- **Date:** 2026-09-24
- **Status:** OFFLINE PASS; exact failed coordinate remains pending verification
- **Provider calls for correction:** 0

The preserved `p2-pilot-recovery-20260924j` stop showed Gemma omitting required
confidence values despite the existing prose requirement. Extractor contract
`residue-v4` now includes an explicit complete JSON graph-record example and
states that confidence is mandatory on every concept, edge, and route record
and must be a number from 0.0 through 1.0. The validator, admission threshold,
route semantics, learner, and evidence-review boundary are unchanged.

Offline validation: focused interpretation/reconciliation/runtime tests 38
passed; complete pytest 335 passed; Ruff passed; strict mypy passed; wheel and
fresh-install CLI smoke passed. No provider call occurred for this correction.
The next action is a new fixed continuation from `extraction-s1-e5`, preserving
the failed v4 operation and using the new versioned prompt.
