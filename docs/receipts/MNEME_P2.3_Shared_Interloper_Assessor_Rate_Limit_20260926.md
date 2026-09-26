# P2.3 shared-Interloper A/B — assessor provider-rate-limit stop

Date: 2026-09-26  
Experiment: `p2.3-valid-three-thread-shared-interloper-ab`  
Run: `p23-shared-interloper-ab-20260926-r3`  
Disposition: `INVALID_PROVIDER_RATE_LIMIT`

The two earlier Qwen 235B qualification attempts remain unchanged in
`MNEME_P2.3_Shared_Interloper_AB_Rate_Limit_20260926.md`. This third run used
the selected smaller Qwen Interloper model, `Qwen/Qwen3-30B-A3B`, while
retaining the approved Qwen 235B assessor role. The smaller Interloper passed
its fixed three-call qualification: all three calls returned non-empty text
with `finish_reason=stop` (25, 11, and 12 output tokens; 1,077 total tokens).

The run then completed the local Gemma development call and specialist
extraction at `development-M-A-t0` and `extraction-M-A-t0`. The first
production semantic-assessment coordinate, `assessment-M-A-t0`, reserved the
existing assessor host `Qwen/Qwen3-235B-A22B-Instruct-2507` and received HTTP
429 from DeepInfra. No assessor response or usage was returned, and the
assessment reservation is preserved as `UNCERTAIN`. The run stopped at that
coordinate; no shared conversational turn, control-arm development,
learner update, treatment exposure, readout, or evaluation was dispatched.

This is an invalid provider-availability result, not a behavioral negative
result and not evidence that the smaller Interloper failed. The selected
Interloper health probe and qualification succeeded. The assessor model was
not silently substituted. Historical receipts and all prior call accounting
remain unchanged.

The private run workspace contains the durable request/reservation and
partial development/extraction artifacts:
`/tmp/mneme-p23-shared-ab-20260926-r3`.

No credentials, authorization headers, or secret-bearing environment data
are included in this receipt.
