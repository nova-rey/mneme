# P2.3 Interloper blank-output forensic audit and correction

Date: 2026-09-25

This receipt records the diagnosis and bounded correction applied before the next prospective supplemental run. Historical v2/v3 runs remain unchanged.

## Historical evidence

The persisted records show successful DeepInfra returns from `Qwen/Qwen3-235B-A22B-Instruct-2507`, not transport uncertainty:

| Run / calls | Provider result | Usage | Request boundary |
| --- | --- | --- | --- |
| v2 `t03`–`t11` | `content: ""`, `finish_reason: "stop"` | 1,679 input / 1 output / 1,680 total per call | `system, user, assistant, user, assistant`; final message was prior Qwen output with role `assistant` |
| v3 `t03` | `content: ""`, `finish_reason: "stop"` | 1,889 / 1 / 1,890 | same malformed suffix |
| v3 `t07`–`t09` | `content: ""`, `finish_reason: "stop"` | 1,781 / 1 / 1,782; 1,779 / 1 / 1,780; 1,779 / 1 / 1,780 | same malformed suffix |

Representative persisted request/result pairs are retained in the original private run artifacts. A sanitized representative is:

```text
Qwen request messages:
  user:      prior Gemma response
  assistant: prior Qwen participant message
  [no latest Gemma response as a new user message]

provider result:
  content: ""
  finish_reason: "stop"
  usage: {input_tokens: 1781, output_tokens: 1, total_tokens: 1782}
```

The v3 current-circumstance state was present in the private system prompt, but it did not repair the malformed conversational suffix. The request was nonempty, and no blank participant text was forwarded downstream. The DeepInfra adapter did not apply whitespace sanitization, stop-sequence filtering, or length truncation; the persisted result was an exact empty decoded content string with a normal `stop` finish and one output token.

The historical artifacts do **not** retain the original provider `choices` object, HTTP response headers/status, or alternate fields such as `reasoning_content`. The prior `_payload()` dropped `GenerationResult.raw_metadata`, so those fields cannot be reconstructed without regenerating the calls. They are recorded here as unavailable rather than inferred.

## Root cause

The request construction defect was the missing current user message. `_interloper_history()` correctly rendered prior pairs from Qwen’s perspective, but `_interloper_request()` did not append the newest Gemma response. Requests therefore ended with a prior Qwen assistant message, creating an assistant-prefill/continuation boundary. This violated the intended perspective contract and is the smallest evidence-backed cause consistent with the one-token `stop` responses.

## Correction

The prospective contract now:

- appends the latest Gemma response exactly once as Qwen’s `user` message;
- uses the declared schedule prompt as the current user message for open-loop generation;
- persists sanitized provider `raw_metadata` with every decoded result for future forensic review;
- treats missing/null provider content as decoded empty content rather than a transport exception;
- hard-stops a supplemental run on an unusable Interloper message after one same-coordinate recovery attempt;
- dispatches no Gemma, extraction, assessment, learner, or opportunity work after the second empty result;
- never admits an empty message to conversation history.

The recovery request uses the same scientific turn coordinate and a distinct technical call ID (`...-recovery-1`). Both attempts remain persisted.

## Offline evidence

Focused regressions cover empty, whitespace-only, missing/null, valid, same-coordinate recovery, second-empty hard stop, no downstream episode/opportunity work, role serialization, and raw metadata retention. The corrected run is versioned prospectively; historical v2/v3 artifacts are not rewritten.
