# MNEME Phase Two Interloper executive-state correction

**Status:** OFFLINE READY — new live run requires explicit authorization

The historical interactive transcript remains immutable evidence. This
correction changes only prospective Interloper request construction for a new
contract revision.

## Implemented control boundary

- Contract revision: **2**.
- Interloper policy revision: **3**.
- Private executive state: `interloper-executive-v1`.
- Attractor detector: `observable-attractor-v1`.
- Every Interloper request receives a fresh private environment window,
  approximate remaining turns, three concrete private concerns, transition
  proximity, attractor risk, and a compact factual state summary.
- Only the most recent **two complete conversation pairs** are sent to the
  Interloper. Older dialogue is excluded from the provider-visible request.
- The attractor detector uses short-range lexical repetition, repeated
  conversational markers, recent lexical overlap, and late-window stagnation
  signals. It emits only `low`, `elevated`, or `high`; it does not generate
  dialogue or select a topic.
- Revision 3 explicitly permits interruption, disagreement, abandoned threads,
  and a natural subject change. Private concerns do not contain desired
  Gemma associations, learner state, or evaluation criteria.

Environment concerns are ordinary practical circumstances: constrained dinner
preparation, balcony plants during heat and travel, and a remote field station
with unreliable deliveries, power, and shared equipment. They are motivations,
not scripted utterances or target answers.

## Offline evidence

The preserved Lentil Incident shape (`I am here.` / `We stay.` / `Enough.` /
`We remain.`) is covered by a FakeHost regression. The request carries only the
two recent pairs plus fresh balcony-plant concerns and an elevated/high
attractor signal; the test accepts any generated wording and does not prescribe
an exact next message.

Validation passed provider-free:

- focused contingent tests: **16 passed**;
- full pytest: **403 passed**;
- Ruff: passed;
- strict mypy: passed;
- wheel build and fresh-install import smoke: passed;
- work-queue schema validation: passed;
- CI: **36079256665 passed** for implementation commit `a48937a`;
- historical transcripts and failed run artifacts: unchanged;
- provider calls for this correction: **none**.

The failed run demonstrates that ordinary context-window momentum can mimic
developmental persistence. It remains a control limitation for later fixation
experiments and is not evidence of personality, attachment, romance,
consciousness, or individuality.

No new live experiment has been started. Transcript publication remains
mandatory at every future stop, continuation, checkpoint, and completion.
