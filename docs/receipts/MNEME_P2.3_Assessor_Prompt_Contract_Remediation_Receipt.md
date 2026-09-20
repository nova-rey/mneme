# MNEME P2.3 assessor prompt-contract remediation receipt

**Status:** OFFLINE REMEDIATION COMPLETE — FRESH QUALIFICATION REQUIRED  
**Date:** 2026-09-20  
**Scope:** P2.3 assessor qualification boundary only

The first fixed three-call qualification was retained as historical evidence. DeepInfra returned all three results and the credential was functional, but each result violated the production assessor JSON contract. The failure was caused by an underspecified model-facing prompt: it referred to declared enum values without enumerating the complete top-level, row, coverage, evidence, and dependence contract.

The production prompt is now `p2-assessor-production-v2`. It explicitly enumerates every validator-constrained value and field, requires exactly one row per monitor, requires raw JSON only with no fences/prose/comments, and states the source-coverage and quotation rules for present, absent, and unknown results. The strict validator and qualification criteria were not weakened; unsupported labels, malformed top-level objects, omitted/duplicate rows, incomplete absence claims, and invalid quotations remain rejected.

Offline validation after the correction:

* `pytest -q`: 267 passed;
* Ruff: passed;
* strict mypy over 47 source files: passed;
* no provider call or credential access during remediation.

A fresh fixed three-call qualification attempt is required before any pilot execution. The prior qualification results remain unchanged and the proposed 299-call pilot remains untouched.
