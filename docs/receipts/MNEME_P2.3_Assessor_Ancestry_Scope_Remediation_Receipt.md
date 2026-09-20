# MNEME P2.3 assessor ancestry-scope remediation receipt

**Status:** OFFLINE REMEDIATION COMPLETE — FRESH QUALIFICATION REQUIRED  
**Date:** 2026-09-20  
**Scope:** assessor provenance validation after `qualification-20260920-v2`

The fresh three-call qualification remains failed historical evidence. Its Q2 result exposed one implementation defect in addition to model semantic errors: the validator treated any request-level memory or replay ancestry as applying to every monitor. That incorrectly rejected independence for monitors whose required source slots had no ancestry.

The validator now scopes the recorded-ancestry prohibition to the monitor's own required source slots. An ancestry-bearing monitor still cannot claim `no_identified_link`; unrelated monitors are not contaminated by another monitor's exposure. The production prompt now defines `external_supported`, `current_input_echo`, `replay_linked`, `exposure_linked`, and `no_identified_link`, including the rule that ancestry for one monitor does not apply to unrelated source slots.

The strict qualification assertions remain unchanged. This correction does not make the failed run pass: Q1 still has incorrect semantic classifications, Q2 still falsely supports the rain-jacket relation and uses the wrong shade dependence, and Q3 still confuses unavailable coverage with absence. The old live results and failure receipt were not rewritten.

Offline validation after remediation:

* `pytest -q`: 268 passed;
* Ruff: passed;
* strict mypy over 47 source files: passed;
* no provider call or credential access.

A new qualification authorization is required before any future provider call. The proposed 299-call pilot remains untouched.
