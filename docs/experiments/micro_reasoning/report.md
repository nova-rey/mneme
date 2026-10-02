# Final native-reasoning micro-stagnation comparison

**Disposition: MIXED.** Native reasoning materially improved circling and fixation
detection on the frozen bank. Improvement was not robust across wording variants:
three prompts falsely labeled some productive work as circling, binary wording
agreement worsened, and both ternary prompts stopped using abstention. Preserve
this as a future research lead; no prompt is selected. Adaptive stagnation detection
is parked. No Phase B, Quinn, new cases, prompt tuning or control policy follows.

## Direct OFF versus ON results

Counts use one result per unique case/prompt; both duplicate copies agree.
The original 14 clear cases comprise eight progress/converged and six circling;
q11/q12 are the two ignored-evidence fixation cases within the circling group.
The two ambiguous cases have no invented binary answer key.

| Prompt | Clear correct OFF → ON | Progress correct /8 | Circling correct /6 | Fixation correct /2 | New productive false-circling cases |
|---|---|---|---|---|---|
| binary_a | 10/14 (71.4%) → 14/14 (100%) | 8 → 8 | 2 → 6 | 0 → 2 | None |
| binary_b | 8/14 (57.1%) → 10/14 (71.4%) | 8 → 5 | 0 → 5 | 0 → 2 | q01, q13, q14 |
| ternary_a | 7/14 (50%) → 12/14 (85.7%) | 7 → 7 | 0 → 5 | 0 → 1 | q13, formerly unclear |
| ternary_b | 8/14 (57.1%) → 11/14 (78.6%) | 8 → 5 | 0 → 6 | 0 → 2 | q01, q13, q14 |

All four improved circling detection substantially. Three detect both fixation
cases; ternary_a still misses q11, the received-packets/zero-misses case that the
conversational assistant keeps framing as silence. Both repeated-vocabulary
progress cases q05/q06 and both appropriate-resolution cases q09/q10 remain correct
for all prompts. Reasoning therefore supplies useful discrimination that the OFF
run often lacked, but it also shifts some errors onto legitimate progress:

* q01: useful sensor/cable/supply troubleshooting is mislabeled by binary_b and
  ternary_b despite progressive evidence.
* q13: useful exploration with no new external facts is mislabeled by binary_b,
  ternary_a and ternary_b.
* q14: another useful model-side exploration case is mislabeled by both b variants.
* q08: the varied-vocabulary unresolved opening-time loop remains missed by binary_b.

Binary_a's perfect clear-case result is a result on this small authored bank, not
a selected prompt or generalization claim. Its wording partner loses four clear
cases. This is why the overall disposition is MIXED rather than PROMISING.

[Case matrix](matrix.md), [machine comparison](comparison.json), and
[all 128 call readings](calls.csv) retain the direct comparisons.

## Wording, ambiguity and validity

| Quantity | OFF | ON |
|---|---:|---:|
| Binary wording agreement, clear cases | 12/14 | 10/14 |
| Binary wording agreement, all cases | 14/16 | 12/16 |
| Ternary wording agreement, clear cases | 10/14 | 11/14 |
| Ternary wording agreement, all cases | 11/16 | 12/16 |
| Valid final classifications | 128/128 | 128/128 |
| Exact duplicate pairs | 64/64 | 64/64, including reasoning |

Reasoning did not consistently reduce prompt sensitivity. Binary disagreement now
covers q01/q08/q13/q14; ternary disagreement covers q01/q11/q14/q16. Agreement alone
can also hide shared errors, such as ternary false-circling on q13.

On ambiguous q15, all ON prompts choose circling. On q16, binary_a/b and ternary_b
choose circling, while ternary_a chooses progress. Neither ON ternary variant uses
unclear anywhere in the bank. OFF ternary_a used unclear on q15, three clear loops
and q13. Thus the availability of an abstention label did not become more useful.
These are forced categorical outputs, not calibrated confidence estimates.

Every ON final answer is exactly an allowed digit with normal stop. None is rescued
from reasoning prose, and reasoning quality is not scored. All 128 replies expose
nonempty reasoning_content separately; all 64 pairs match reasoning, final content
and finish reason. This establishes repeatability for tested coordinates, not
robustness to wording, seeds, natural conversations or other hardware.

## Frozen controls and necessary reasoning accommodations

The unchanged [original bank](../micro_stagnation/qualification_cases.json),
[labels and prompts](../micro_stagnation/prompts.json), and original 128-call
manifest were reused without rewriting, reordering, selection or additional calls.
The [freeze receipt](freeze.json) predates execution. Original OFF evidence is
unchanged. Request messages use the original serializer byte-for-byte.

Same resident `google/gemma-4-E4B-it`, same
`gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf` path, pinned llama.cpp revision
`4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`, context4096, one slot.
Generation seed424242, temperature0.7, top_k64, top_p0.95, min_p0.05,
streamfalse and cache_promptfalse are unchanged. All reported cache_n values are0.
No SAA payload, field seed, prior assessment or private case label enters a request.

There is one intended treatment, native reasoning ON, with four declared request
changes needed to implement it in this runtime:

1. Set chat_template_kwargs.enable_thinking=true.
2. Remove reasoning_effort:none, which otherwise overrides and disables thinking.
3. Request reasoning_format:deepseek to expose reasoning separately from the final.
4. Allow2048 total output tokens instead of8 because the limit includes reasoning.

This is an operational reasoning-mode comparison, not literal equality except for
one boolean. The larger allowance was frozen before calls and never tuned. ON used
266–928 total completion tokens, with no cap reached; OFF used2 and was also uncapped.
The native template adds its reasoning control tokens (reported prompt counts are
2 higher), while user/system message content and formatting stay unchanged. No
reasoning budget termination, extra instruction or changed sampler was introduced.
See [pinned runtime control evidence](source_controls.md),
[config](runtime_config.json), [protocol](protocol.md), and
[all frozen exact requests](run/frozen_execution.json.gz).

API model path/alias, reported ftype, build, template, default settings and slot
count exactly match OFF, before and after ON. The filename quantization designation
and server ftype Q4_0 remain separately recorded. Fresh remote physical GGUF hashing
was unavailable; prior same-day physical hash plus live API continuity is the
identity evidence, not a new checksum attestation. No service setting was changed.

## Ordinary runtime cost

No latency optimization, sweep or runtime tuning was performed. Of128 calls,
127 retain HTTP and complete-observation wall clocks. One derived receipt lost
volatile timing during a disk-full interruption; its complete raw response and
native timing survived. Missing duration is excluded, not fabricated.

| Prompt | ON HTTP observations | HTTP median | HTTP maximum |
|---|---:|---:|---:|
| binary_a | 31/32 | 9.53s | 16.10s |
| binary_b | 32/32 | 9.26s | 13.97s |
| ternary_a | 32/32 | 9.05s | 14.63s |
| ternary_b | 32/32 | 10.83s | 12.87s |

Overall HTTP median9.60s, p9012.68s, maximum16.10s. Full observation including
preprocessing and recorder writes: median9.80s, p9012.88s, maximum16.30s.
For the127 observed full durations, 0% finish within1/3/5s and51.97% within10s.
These are seconds, not routine minutes: operationally plausible during human
between-turn activity, though no real-user interval study was performed. Latency
does not determine the MIXED disposition. OFF full median was0.50s.

Native prefill median154.56ms; generation median9363.54ms. Median total completion
usage550 tokens. The provider gives no separate reasoning-token count, so all128
reasoning-token readings remain unavailable. Total tokens are not relabeled as
reasoning tokens. No extra tokenization/model call was made to estimate that split.

## Storage interruption, preservation and verification

At call89, disk exhaustion interrupted only the derived receipt write after the
raw response had been saved successfully. Its request, context and complete raw
response were validated, and its receipt reconstructed without inference. The
original call90 then reproduced it exactly. One call has unavailable wall clocks;
no semantic result was lost, retried, replaced or rescored. Regenerable local
validation caches were removed; experiment evidence was preserved. The
[recovery receipt](storage_recovery.json) and exact recovery script are retained.
This interruption does not invalidate the matched semantic comparison.

The new runner is isolated under tools, reuses the unchanged OFF serializer, and
permits only the four declared control changes. It stops on cache reuse, missing
reasoning, truncation, inadequate context, uncertain requests or duplicate mismatch.
The pure comparison requires all coordinates and replay success before comparing
final classifications. Tests exercise these boundaries with mocked transport.
A post-freeze analysis-only type annotation/local-name repair is documented in
[typing amendment](analysis_typing_amendment.json); formulas and execution code
remained frozen.

The [result receipt](result_receipt.json) records source and runtime preservation.
The CompactStore ancestor checksum remains unchanged; no production, SAA, learner,
developmental, introspection, history or persistence code is modified.

Reproduce the comparison without inference:

```sh
PYTHONPATH=src:. .venv/bin/python tools/report_micro_reasoning.py \
  --bank docs/experiments/micro_stagnation/qualification_cases.json \
  --prompts docs/experiments/micro_stagnation/prompts.json \
  --off docs/experiments/micro_stagnation/phase_a/readings.json.gz \
  --on docs/experiments/micro_reasoning/run/readings.json.gz \
  --output /tmp/micro-reasoning-comparison.json
```

No new thresholds, learned classifier or composite score was fitted. This small
previously examined authored bank cannot establish live meter reliability. Native
reasoning is a meaningful future lead for recognizing loops, but current wording
sensitivity, productive false positives and absent abstention prevent a robust
meter recommendation. **Stop here and park adaptive stagnation detection.**

## Validation

All760 tests passed, including16 new focused recorder/comparison tests. Ruff and
strict mypy passed for the72 package files and both new tools. Comparison replay
was byte-identical without inference. Every actual ON request differs from its
retained OFF request only in the four declared reasoning accommodations. All8,552
pre-existing untracked paths remain preserved. See [validation](validation.json)
and [raw-evidence hashes](retention_manifest.json). CI is checked on the integrated
commit and reported in the closure receipt/final response.

[Implementation CI](https://github.com/nova-rey/mneme/actions/runs/37076996592)
passed for `a97d4a1d21810c99dc9ab1dfbbb92c32852df06e`. The
[closure receipt](closure_receipt.json) records completion; final closure-commit CI
is verified separately and reported with the exact final commit.
