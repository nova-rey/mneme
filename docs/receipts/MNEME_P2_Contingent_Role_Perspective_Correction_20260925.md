# MNEME Phase Two contingent role-perspective correction

Date: 2026-09-25  
Contract: `contingent-conversation-interloper-20260924` revision 3  
Role renderer: `explicit-model-perspective-v1`  
Historical run preserved: `contingent-live-20260925`

## Defect

The historical 252-call run used one `(user, assistant)` renderer for both
models. That made Gemma's responses appear as Qwen's prior assistant messages
when the Interloper request was serialized. The run remains immutable and its
interactive condition is unsuitable for claims about contingent developmental
behavior. Its transcripts remain instrumentation evidence.

## Correction

Stored pairs remain `(interloper_message, subject_response)`, but requests now
use explicit perspective-specific renderers:

* Gemma: interloper message as `user`, Gemma response as `assistant`.
* Qwen: Gemma response as `user`, Qwen's prior message as `assistant`.

Open-loop schedule prompts are treated as the other-speaker input and use the
same Qwen perspective. The latest Qwen request therefore serializes an
unfinished Gemma response such as `layered with smoked` as a `user` message;
it cannot become an assistant prefill for Qwen.

The Interloper system prompt now describes an ordinary human participant and
contains no research-study or evaluator framing visible to Gemma. Private
executive state remains controller-only. A blank provider result is persisted,
published as an invalid environment turn, and rejected before it can be sent
to Gemma or added to history.

## Offline evidence

The serialized-request regression fixtures assert both message arrays across
multiple turns, including the `layered with smoked` case. Focused contingent
tests pass (19 tests); the complete suite passes (422 tests), Ruff passes,
strict mypy passes, and queue validation passes. Package/fresh-install smoke
is required before live dispatch and will be recorded with the run evidence.

No provider calls were made by this correction. The next run must be a fresh
prospective execution under revision 3; no historical dialogue or provider
result is regenerated.
