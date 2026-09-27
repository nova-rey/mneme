# SAA ten-thread preflight contract

Status: `FROZEN_OFFLINE_PLAN`

This receipt freezes the prospective `f0-saa-v1` ten-thread developmental
comparison. It is an execution contract and evidence-schema preflight only;
it made zero provider calls and zero local-model calls. Historical F0, r6, r7,
and invalid-run evidence remains unchanged.

The isolated harness is [run_p23_saa_ten_thread.py](../../tools/run_p23_saa_ten_thread.py).
Its default entry point only emits this contract and refuses to run without an
explicit `--emit-plan` path. A later execution adapter must use the existing
PilotRuntime, local Gemma/GLiNER/DeBERTa stack, and Qwen3-30B shared-Interloper
contract; the scaffold does not alter `controller.py` or the existing F0 field.

## Frozen schedule

Threads T01–T09 provide eight target exchanges each, within the declared
six-to-ten exchange runway, across gardening, travel, cooking, music, repair,
games, visual art, social coordination, and astronomy. T10 is frozen before
development: a coastal community's temporary night market in a converted ferry
terminal, with uncertain power, weather, volunteers, delicate displays, and
closing procedures. T10 offers multiple broad bridge opportunities without
naming a learned association or prior domain.

Every thread starts a fresh host context. Qwen remains the single shared
environmental participant; both branches receive one common continuation, and
branch-specific responses remain private inputs to Qwen. The schedule carries
forward perspective-correct history, anti-attractor behavior, no sibling
leakage, nonempty-output hard stops, and complete transcript publication.

## Frozen SAA configuration

The mode is `f0-saa-v1`, with `exploration=on`, the fixed field RNG algorithm
`python-random.Random-mt19937`, a maximum landing set of eight, propagation
depth two, attenuation `600000/1000000`, pressure budget `1000000`, four active
contributors, exploration budget `100000`, activation decay `800000`, and a
900-character/three-tendency renderer budget. Context relevance is weighted
more strongly for familiar context than for novel context, while novelty
flattens discrimination without erasing developmental priors. All values are
serialized in the companion JSON contract.

Field seeds are the fixed independent sequence `71001..71006`; Gemma readout
seeds are `81001..81003`. Seeds are independent of run IDs, timestamps,
branches, filenames, and database order. The same field seed is therefore
replayed against the same frozen state, and can map differently under a
different developmental distribution.

## Measurement and evidence

The primary comparison is vanilla `C` versus developed `SAA`. Readout uses
four frozen unfamiliar probes and three repetitions per probe. The contract
also freezes `SAA_ON → SAA_OFF → SAA_RESTORED` removal/restoration checks and a
small positive/negative external-consequence subtest after primary readout;
Thread 10 is not allowed to update the primary measurement state before those
readouts finish. A second independently developed history is deferred unless
it fits the bounded run without expanding scope.

Each field coordinate must preserve current input, active context, eligible
candidates, normalized distribution, flatness diagnostic, field seed and draw,
landing, local propagated neighborhood, rendered payload, Gemma seed/output,
and the paired vanilla output. Host payloads remain abstract and bounded; they
must contain no graph IDs, raw provenance, learner scores, treatment labels, or
transcript quotations. Null/blank output, missing field computation, payload
leakage, sibling leakage, or changed T10 schedule is invalid instrumentation,
not a behavioral negative.

The machine-readable frozen contract is
[MNEME_P2_SAA_Ten_Thread_Preflight_20260926.json](MNEME_P2_SAA_Ten_Thread_Preflight_20260926.json).

## Preflight result

The contract validator passed offline. The plan records ten unique threads,
T10 last, the declared runway, the fixed seed schedule, three readout
repetitions, and zero provider/local-model calls. No live experiment was
started by this package.
