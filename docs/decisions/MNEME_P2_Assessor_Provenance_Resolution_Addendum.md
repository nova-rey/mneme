# MNEME Phase Two — Assessor/Provenance Resolution Addendum

**Amendment:** `P2-ASSESSOR-PROVENANCE-RESOLUTION-01`  
**Date:** 2026-09-20  
**Status:** Offline correction applied; fresh qualification authorization required

This additive correction preserves the approved Phase Two plan, Gemma
developing host, separated assessor role, learner semantics, budgets, and all
historical qualification evidence. It addresses the Qwen Q1 diagnosis: the
semantic judgments were correct, while the model supplied a provenance label
that MNEME already knew deterministically from runtime records.

## Responsibility boundary

The assessor now returns only validated semantic observations:

- relation presence, direction, polarity, participants, and context;
- source coverage and exact quotations;
- semantic correspondence from a model-output occurrence to declared source
  slots when language understanding is required.

The assessor does not return dependence categories, offsets, weights, caps,
or provenance conclusions. MNEME resolves those from immutable source roles,
availability, memory exposure, replay ancestry, source bindings, and operation
records.

The prospective contracts are:

- assessor schema: `p2-assessor-v2`;
- assessor prompt: `p2-assessor-production-v3`;
- provenance resolution: `p2-provenance-v1`.

The shared production boundary is
`validate_and_resolve_assessor_result()`: semantic validation runs first, then
`resolve_provenance()` derives the learner-facing dependence. Qualification
uses this same path.

## Deterministic precedence

For a semantically present occurrence:

1. An authoritative external source resolves to `external_supported`; replay
   or carryover metadata cannot relabel it.
2. A model-output occurrence corresponding to an external source resolves to
   `current_input_echo` and is ineligible for additional model-origin credit.
3. A model-output occurrence corresponding to recorded memory exposure resolves
   to `exposure_linked`.
4. A model-output occurrence corresponding only to recorded replay ancestry
   resolves to `replay_linked`.
5. No recorded antecedent resolves to `no_identified_link`.
6. Unknown or conflicting runtime correspondence resolves conservatively to
   `unknown`/`conflict` with no optimistic credit.

All applicable ancestry records and deterministic provenance group keys are
retained. The learner accepts multiple provenance groups and applies the
minimum remaining lifetime/induced cap across every group before updating any
of them.

## Qualification contract

Q1 preserves the latch, echo, and unrelated semantic cases. The resolver must
produce external support for the external latch and current-input echo for the
model output. Q2 preserves the rain-jacket counterexample and shade memory;
the model-output shade occurrence corresponds to the memory source and the
resolver uses recorded exposure (while retaining replay ancestry when both
records apply). Q3 preserves negation and unavailable-source unknown behavior.

The historical Gemma and Qwen qualification receipts remain unchanged. This
offline correction makes no provider call and does not authorize a new one.
