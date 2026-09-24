# P2.3 Assessor Quote Prompt Correction Receipt

- **Recorded:** 2026-09-24
- **Exposed by:** continuation run `p2-pilot-recovery-20260924e`
- **Provider calls in that run:** 20 returned calls; no uncertain calls and no
  retry was dispatched after the stop.
- **Failure:** Qwen semantically identified the monitored relationship, but
  returned `Good Contrast: Juxtaposing "hot day" with "still held moisture"`
  for source text containing the exact Markdown-marked quotation
  `**Good Contrast:** Juxtaposing "hot day" with "still held moisture"`.
- **Cause:** the production prompt required verbatim evidence but did not
  explicitly state that Markdown markers, escapes, punctuation, and
  whitespace are part of the immutable source.
- **Correction:** prospective assessor prompt contract `p2-assessor-production-v9`
  states that formatting-preserving exact quotation is mandatory. Strict
  source-bound validation is unchanged; historical v8 results and failure
  receipts remain unchanged.
- **Offline validation:** 319 pytest, focused assessor regressions, Ruff,
  strict mypy, package smoke, and zero provider calls for this correction.
