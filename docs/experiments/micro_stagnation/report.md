# Five-turn micro-introspection: qualification failed

**Recommendation: too unreliable, with material prompt sensitivity, under this
frozen tiny-prompt configuration.** Runtime cost is operationally reasonable, but
the semantic reading is not qualified as a useful stagnation meter. Stop after
Phase A. Phases B and C were not run; no Quinn or normal conversational generation
was performed. No prompts were repaired or additional variants searched.

## Frozen experiment

The [case bank](qualification_cases.json) contains 16 authored recent-conversation
windows, each five complete participant/assistant exchanges: two examples of each
of the eight requested categories. Private expected interpretations are eight
progress/converged, six unresolved circling, and two genuinely ambiguous. Root
reviewed every window before execution. The bank includes technically progressing
work with repeated vocabulary, paraphrased loops, appropriate resolution, ignored
evidence, and model-side exploration without new external observations.

[Four tiny prompts](prompts.json) were frozen together: binary_a/b and ternary_a/b,
with one wording variation per format. Binary maps 0 to progress/convergence and
1 to circling. Ternary maps 0 to progress/convergence, 1 to unclear and 2 to
circling. Each case/prompt ran twice with identical request bytes: 128 calls,
64 unique prompt/window coordinates. Repeats test reproducibility; they are not
independent accuracy samples. No expected class, category, passive score or prior
assessment was included in a request.

The [protocol](protocol.md) and [freeze hashes](freeze.json) predate every recorded
provider response timestamp. Qualification required at least 11/14 correct clear
cases per repeat, progress recall >=6/8, circling recall >=4/6, and >=30/32 parsed
responses. Both wording variants had to qualify and agree on >=12/14 clear cases.
Ternary was preferred if its pair qualified. These were experiment gates only,
never generation thresholds. The always-progress baseline is 8/14 (57.1%).

## Qualification results

All 128 outputs were well formed, uncapped, and exactly two reported output
tokens. All 64 duplicate pairs matched output bytes and finish reason. No calls
were retried or uncertain. Reproducibility did not imply semantic correctness.

| Prompt | Correct clear cases, each repeat | Progress recall | Circling recall | Ambiguous q15 / q16 | Qualified |
|---|---:|---:|---:|---|---|
| binary_a | 10/14 (71.4%) | 8/8 | 2/6 | progress / progress | No |
| binary_b | 8/14 (57.1%) | 8/8 | 0/6 | progress / progress | No |
| ternary_a | 7/14 (50.0%) | 7/8 | 0/6 | unclear / progress | No |
| ternary_b | 8/14 (57.1%) | 8/8 | 0/6 | progress / progress | No |

Binary_a modestly exceeds the trivial baseline, but misses four of six clear
loops and loses its two successful loop detections under a small wording change.
Binary_b and ternary_b label every case progress. Ternary_a never emits circling;
it abstains on three clear loops, one useful exploration case and one ambiguous
case. Abstention is recorded separately from a correct clear-case classification.

Binary wording agreement is 12/14 clear cases (14/16 overall). Both disagreements
reverse the clearest detected loops, q03/q04, to progress. Ternary wording agreement
is 10/14 clear (11/16 overall); uncertainty disappears in the paraphrase. No prompt
pair qualifies. [Gate decision](gate_decision.json): **STOP_AFTER_PHASE_A**.

## Important successes, errors and passive disagreement

* **q05/q06, productive repeated vocabulary:** every prompt returns progress.
  For q05, the last-turn participant quantity-novelty fraction is zero because
  the successful bake repeats previously used values. The semantic answer is
  appropriate, but the near-universal progress bias prevents treating this alone
  as evidence of useful discrimination.
* **q03/q04, obvious repeated unavailable or completed advice:** binary_a detects
  circling. Binary_b changes both to progress. Ternary_a abstains; ternary_b says
  progress. q03's final model content novelty is .667 and trigram recurrence zero,
  illustrating why one wording can add information missed by surface features,
  but that addition is not robust to the paired prompt.
* **q07/q08, paraphrased loops:** final model content novelty is 1.000/.857 and
  phrase recurrence is zero. Both binary prompts say progress; ternary_b also
  says progress. Ternary_a abstains on q07 but misses q08. The semantic call does
  not reliably rescue the lexical false-movement signal.
* **q11/q12, new evidence ignored:** every prompt says progress. q11 explicitly
  supplies received packets, distinct timestamps and zero missed updates while
  the assistant repeatedly calls the stream silent. q12 supplies aligned clocks,
  a rotated signing key and successful cache refresh while the assistant insists
  on clock skew. Missing these central attractor examples is decisive against
  the intended use. Their expected labels were frozen, not assigned after output.
* **q09/q10, resolved/closing:** all prompts correctly return progress/converged.
  Again, an always-progress meter would also pass them.
* **q13/q14, static environment with useful analysis:** all prompts except
  ternary_a on q13 return progress. q13's content novelty is 1.000, consistent with
  developing alternatives; the abstention is a clear-case false abstention under
  the authored expectation.
* **q15/q16, ambiguous:** ternary_a abstains on q15 only. Other outputs are progress.
  Binary necessarily makes a forced choice; it has no fabricated binary answer
  key for these cases. A digit does not provide calibrated confidence, and
  reasonable human disagreement remains possible.

[The checkpoint matrix](phase_a_analysis/matrix.md),
[full CSV](phase_a_analysis/matrix.csv), and
[detailed analysis](phase_a_analysis/summary.json.gz) retain all readings. Passive
values come from unchanged closure instruments at accepted age five. Since the
windows are authored fixtures, contextual activation, historical pull, extraction
coverage and normal-response token/finish metadata are unavailable, not invented.
Text word counts and surface/quantity readings are available. Micro-call input/
output usage is recorded separately from authored assistant response metadata.
No combined score was constructed.

## Exact runtime and timing

Same resident local `google/gemma-4-E4B-it` host and GGUF as the current MNEME
configuration: `gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`, prior diagnostic hash
`79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`, llama.cpp
commit `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`, RTX3060 Laptop6GiB, context4096.
The filename quantization and server-reported ftype Q4_0 are retained distinctly.
The current health/props snapshot agrees with the preceding diagnostic; no
checkpoint identity was inferred merely from its model name.

Micro-only configuration: reasoning OFF, no SAA payload, seed424242,
temperature.70, top-k64, top-p.95, min-p.05, `cache_prompt:false`, `max_tokens:8`,
`stream:false`, `reasoning_effort:none`, `enable_thinking:false`. This is the
documented reproducible **seeded stochastic** configuration, not untested greedy
decoding. The concurrent operations note was merged from current main before
execution. All actual timing records show zero reused cache tokens. Normal
conversational configuration and resident defaults were not changed.

Native template/tokenizer calls size the complete window without inference.
Oversized windows would be unavailable, never clipped; none were oversized.
Actual input usage was 219–336 tokens. This experiment did not measure the much
longer preserved-conversation windows because qualification failed.

| Latency measure, n=128 | Median | p90, nearest rank | Maximum | <=1s | <=3s | <=5s | <=10s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Generation HTTP call, including prefill | .275s | .323s | 1.350s | 95.31% | 100% | 100% | 100% |
| Full observation through raw-response save | .499s | 1.514s | 2.542s | 88.28% | 100% | 100% | 100% |

Native server prefill: median143.5ms, p90163.9ms, maximum185.4ms. Native generation:
median18.6ms, p9018.7ms, maximum18.9ms. Both components are present for all calls;
they are not substituted for client wall time. Separate native preprocessing
wall time has median.213s, p90.581s, maximum1.623s. Full observation additionally
includes preprocessing and recording overhead. Network, shared-host load and
timing-boundary differences remain relevant; this is not a cold-model benchmark.

The observed cost is operationally reasonable for the intended between-turn use.
Sub-second inference is not required; several seconds would also be acceptable.
These timings were recorded incidentally during semantic qualification, not through
a latency sweep or runtime optimization. The owner's [clarification](protocol_addendum.md)
supersedes the unused ten-second Phase B gate: gross impracticality, not a tight
latency target, is the relevant concern. This does not establish runtime cost for
the longer preserved windows, and does not change the failed semantic qualification.

## Later phases and cadence

**Phase B was not executed.** The conditional [preserved windows](phase_b_windows.json)
were prepared with source hashes and private expectations before reviewing A's
results, but no qualified prompt existed to apply. They select c202 ages5/10,
c008 age5, c003 ages5/10, closure p003/p004 age5, and the old named concise-resolution
fixture at5. No condition labels, future turns or meter scores would enter a call.

Inspection found a ground-truth limitation in that old fixture: at the eligible
age-five checkpoint it contains contradictory unresolved/resolved statements,
not a clean completed conversation. It remains labeled a contradiction diagnostic.
Clean convergence is tested in Phase A. Original receipts are not rewritten.

**Phase C was not executed.** There are no prospective Quinn/Gemma transcripts
for this test and no new developmental/conversational campaign. Skipping later
phases is the frozen gate's intended result, not missing evidence presented as a
successful live test.

The pure selector samples the last five accepted exchanges at observed current-arc
ages5,10,15,… and resets on existing arc transitions. Global ordinal gaps and failed
attempts do not advance accepted age. Tests cover pivots, causal prefixes, missing
text, duplicate identities and recurrence rejection. Partial histories cannot
recover omitted prior membership. Five-turn cadence can delay a new loop reading
by up to four accepted turns, and a short-lived loop may end between checkpoints.
No empirical detection-delay claim is made because the live phase did not run.
No asynchronous production behavior or previous-result feedback was implemented.

## Recommendation and engineering boundary

**Neither binary nor ternary prompt is qualified.** Ternary remains the more honest
interface when evidence is insufficient, but its abstentions here do not establish
reliable ambiguity handling and it never identifies circling. Do not promote
binary_a simply because it wins this small bank. The supported disposition is
too unreliable/prompt-sensitive for the intended semantic meter; retained outputs
are diagnostic evidence only. This finding is bounded to these frozen prompts,
windows, output allowance and reasoning-off configuration, not a universal claim
about every possible use of Gemma.

Added only `src/mneme/experiments/micro_stagnation.py`, isolated runner/report
tools and focused tests. The observer has no production hook, no SAA field,
no developmental ingestion, and no persistence writes beyond its own experiment
artifacts. No previous classifications enter subsequent requests. D100 file SHA,
resident identity/global defaults, production source and all prior meter evidence
remain unchanged; see [independence receipt](independence_receipt.json).

The report replays from retained responses without inference. Qualification used
exactly128 Gemma assessment calls, zero Quinn calls, zero ordinary Gemma replies
and zero extractor calls. No SAA probabilities, wildcard behavior, learner state,
introspection weights or generation policy changed. Stop after this report.


## Validation and replay

All **744 tests passed**, including 18 isolated micro-meter tests and 10 report
checks. Ruff passed. Strict mypy passed all 72 package files and both new tools
without import suppression. Tests cover five-turn cadence/pivots, source isolation,
missing/oversized windows, strict digit parsing, exact provider-call counts,
uncertain-attempt refusal, duplicate mismatch stopping, no input mutation,
fixed-denominator gates, ambiguity handling, timing availability and deterministic
reports. The three report artifacts replay byte-for-byte; frozen inputs and code
remain unchanged. See [validation receipt](validation.json).

Recompute analysis from retained responses, with no model calls:

```sh
PYTHONPATH=src:. .venv/bin/python tools/report_micro_stagnation.py \
  --cases docs/experiments/micro_stagnation/qualification_cases.json \
  --prompts docs/experiments/micro_stagnation/prompts.json \
  --readings docs/experiments/micro_stagnation/phase_a/readings.json.gz \
  --output /tmp/mneme-micro-meter-replay
```

The bank is small and authored, with expected interpretations rather than a
population-level gold standard. q11 deliberately resembles the prior c202 failure,
so it is not independent domain generalization. Single-digit outputs do not
explain why the model chose them; the study cannot separate task misunderstanding
from a label preference. These limits narrow the conclusion, but do not justify
advancing a prompt that misses the intended clear cases.

## Integration closure

Integrated onto current main after the local determinism operations note.
Canonical validation again passed all 744 tests, Ruff and strict package/tool
mypy. [Implementation CI](https://github.com/nova-rey/mneme/actions/runs/37072270172)
passed for `18fb2d487cb94ce505cd484d2a0b09362529cdc9`.
The [closure receipt](closure_receipt.json) records preservation of the CompactStore
ancestor and all 8,552 pre-existing untracked paths. The documentation-only closure
commit receives its own final CI verification, reported with the final commit.
