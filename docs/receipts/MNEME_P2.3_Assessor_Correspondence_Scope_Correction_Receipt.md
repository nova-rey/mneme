# P2.3 Assessor Correspondence Scope Correction Receipt

- **Recorded:** 2026-09-24
- **Exposed by:** fixed v9 continuation `p2-pilot-recovery-20260924f`
- **Provider calls in that run:** three returned calls (development and
  extraction were durable replays; one Qwen assessment); no retry was
  dispatched after the stop.
- **Failure:** Qwen preserved the exact source quotation and semantically
  identified a current-input correspondence, but the production monitor had
  declared only model-output source slots for correspondence. The validator
  correctly rejected the undeclared `s0` correspondence.
- **Correction:** production monitors now declare every required source slot
  for semantic correspondence. Source roles and recorded ancestry remain the
  deterministic authority for provenance and credit.
- **Offline validation:** focused pilot regressions, 319 pytest, Ruff, strict
  mypy, package smoke, and zero provider calls for this correction.
