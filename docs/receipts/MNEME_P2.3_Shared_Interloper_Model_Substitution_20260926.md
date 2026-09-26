# Shared-Interloper model substitution and health probes

Date: 2026-09-26  
Experiment: `p2.3-valid-three-thread-shared-interloper-ab`  

The previous two Qwen3-235B shared-Interloper attempts remain preserved with
their `INVALID_PROVIDER_RATE_LIMIT` disposition. They were not rewritten or
reclassified.

The DeepInfra catalog was queried before selection. The exact current smaller
Qwen chat model selected for the Interloper role is:

`Qwen/Qwen3-30B-A3B`

It is materially smaller than `Qwen/Qwen3-235B-A22B-Instruct-2507` (30B total
parameters with 3B activated per token versus 235B/22B) while remaining a
Qwen chat model. The Interloper requires ordinary conversation, schedule
following, anti-attractor behavior, and a shared continuation across two
responses; it does not require frontier assessor reasoning. The exact model
ID, provider fingerprint, and catalog context length are pinned in the new
run manifest. Reasoning is explicitly disabled for this role so output tokens
remain participant text rather than hidden reasoning.

## Probe records

1. `Qwen/Qwen3-30B-A3B-Instruct-2507`: HTTP 404 `model_not_found`. This
   catalog spelling is not currently served and was not used.
2. `Qwen/Qwen3-30B-A3B`: HTTP 200, but a deliberately tiny 32-token request
   ended with `finish_reason=length` and empty final content. This was treated
   as an unusable health result, not a success.
3. `Qwen/Qwen3-30B-A3B` with the bounded role configuration
   `reasoning_effort=none` and `max_tokens=96`: HTTP 200, `finish_reason=stop`,
   nonempty participant text returned, 31 total tokens. This is the accepted
   health probe.

The successful probe returned request ID `R4zpVyyp1TqjtdMvYrgxPyZS`. No
authorization headers or credentials are included. The selected model is
used only for the shared Interloper; the existing Qwen3-235B assessor role is
unchanged.

The frozen three-thread schedule, perspective-specific history, anti-attractor
contract, paired local Gemma seeds, treatment gate, null-output stop, and
historical evidence boundaries remain unchanged.
