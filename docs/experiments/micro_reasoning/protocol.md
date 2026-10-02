# Final bounded native-reasoning comparison

Compare the frozen micro-stagnation Phase A OFF evidence at commit
42d3d2b4ce63dc24eb41359759f77dc594bcad44 against one ON replay.
No new cases, labels, prompts, prompt selection, Quinn, Phase B, or follow-up.

Reuse the original 128-call manifest in exactly its original order, including
all four prompts, 16 five-exchange windows, two adjacent copies per coordinate.
Preserve original message serialization, model path, seed424242, temperature.7,
top_k64, top_p.95, min_p.05, streamfalse and cache_promptfalse.
ON enables chat_template_kwargs.enable_thinking, removes reasoning_effort:none
(which otherwise overrides the thinking flag), and uses reasoning_format:deepseek
so the runtime exposes reasoning separately. No explanatory prompt is added.

The original eight-token limit counts all generated tokens including reasoning.
A fixed total max_tokens2048 is a necessary allowance for the intended reasoning
treatment; it is not a tuned value or a second substantive treatment. This is
therefore an operational reasoning-mode comparison, not literal equality of all
request parameters except one boolean. All differences are recorded. Context
remains4096 with256 reserved. Any cap/context failure makes the comparison INVALID;
no cap adjustment or rerun is permitted. Final classification still must be exactly
one allowed digit with finish_reason:stop. Never rescue an answer from its reasoning.

Verify model/runtime identity against OFF evidence before calling. Save native
rendering and token counts. A nonempty separately exposed reasoning_content field
is required to establish that the intended ON path occurred. Retain raw replies.
For each adjacent identical coordinate compare reasoning, final content and finish
reason byte-for-byte. Stop on any mismatch before interpreting classification
differences; classify the comparison INVALID. No retries of uncertain attempts.
Reasoning tokens are available only if separately reported by the provider; total
completion tokens must not be relabeled as reasoning tokens.

After all pairs pass, compare each prompt with OFF on the same14 clear cases,
8 progressing,6 circling,2 fixation cases(q11/q12), and both ambiguous cases.
Duplicates demonstrate replay, not independent statistical samples. Compare wording
agreement and per-case gains/losses; invalid final labels remain invalid. No new
thresholds, classifier, combined score or prompt selection. Disposition is one of
PROMISING (clear broad improvement without merely shifting errors), MIXED (important
gains with substantial sensitivity/new false positives), NO MATERIAL IMPROVEMENT
(same basic reliability problem), or INVALID (control/replay failure).

Record ordinary HTTP and full observation durations incidentally, no optimization
or latency sweep. Regardless of outcome, park adaptive stagnation detection.
No call may enter history, SAA, learner, introspection or persistence state.
