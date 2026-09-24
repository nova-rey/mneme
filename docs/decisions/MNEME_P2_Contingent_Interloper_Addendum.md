# MNEME Phase Two Contingent-Conversation Addendum

**Document ID:** P2-SUPPLEMENT-INTERLOPER-01  
**Status:** additive execution authorization  
**Date:** 2026-09-24

This addendum records the owner-supplied contingent-conversation supplement. It
does not reopen or rewrite the historical P2.3 pilot, its
`COMPLETED_INADEQUATE` disposition, the approved learner, or the Phase Three
boundary.

The supplement compares two clean branches from the same permissioned ancestor:
an interactive branch whose Qwen participant sees each persisted Gemma answer,
and an open-loop branch whose 24 participant messages are generated before any
Gemma answer is visible. The developing host remains DeepInfra
`google/gemma-4-E4B-it`; the interloper and assessor use separate Qwen role
bindings, request histories, artifacts, and call coordinates.

The implementation is a bounded adapter around `PilotRuntime`,
`ProductionAssessmentAdapter`, `FrozenComparator`, and P0.2 checkpoints. It
stores synthetic partner messages as laboratory artifacts with origin
`synthetic_environment_model`; partner context is not developmental memory.
Development uses at most four complete recent turn pairs and a 16-KiB lossless
window. Evaluation opens only a private frozen snapshot with empty chat
context. The schedule is 24 pairs per branch, checkpoints at turns 8, 16, and
24, four C-oriented probes, two treatments, and eight empty-ancestor draws.

The nominal plan is 276 calls including reserve, inside a 300-call supplemental
envelope. The old P2.3 ledger and its historical calls remain separately
accounted. The interloper fit check is four calls at 256 output tokens; partner,
Gemma, extraction, assessment, and frozen-readout caps follow the supplied
specification. Hosted sampling remains provider-managed and no deterministic
seed claim is made for DeepInfra.

Before live execution, the actual production continuity/publication path is
checked with disposable authored data for stable targets, carried opportunity
counters, exposure serialization, consolidation transitions, and dependent
replay ancestry. A demonstrated defect must be corrected narrowly before live
dispatch. No threshold, alias, route, or learner coefficient is changed to
manufacture an outcome.

Evidence home: `docs/experiments/contingent-conversation/`. Final reporting
separates implementation integrity, delivered conditions, opportunity and
measurement adequacy, and descriptive behavioral findings.
