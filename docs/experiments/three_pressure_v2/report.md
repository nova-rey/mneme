# Three-pressure meters: second investigation

This is passive measurement research, not a new SAA policy. The first pilot at
`71c4012` is preserved. This investigation began on the promoted CompactStore
boundary at `7a74a92cbd0c084d420a7da9444bd1258d660b4c` in an isolated worktree.

## What was added

`pressure_meters.py` computes three distinct families of deterministic readings:
contextual vocabulary/continuity, earned-history distribution and context
reshaping, and recent repetition/movement. They are not percentages summing to
one. Definitions, inputs, timing, null rules and limitations were frozen in
[formulas.json](formulas.json) before live scores; its SHA-256 is
`42611164905d84c7a76b94d66d88ed14a101f4cba950c2de750a9d1c2160ff18`.
The old C1–C3 composites are retained without tuning.

The [source map](source_map.md) traces actual runtime APIs and separates direct
signals, cheap derivations and unavailable quality judgments. The instrument
accepts recorded data only: no provider/store handles, experimental labels,
private schedules, fidelity judgments or future arc membership. Reports join
labels afterward. It adds no production hook or developmental write. The
recording runner uses CompactStore read-only; historical R8 observation is an
explicit isolated read-only legacy fixture, never a default developmental path.

## Construction and review

[Construction](construction.md), [frozen schedules](construction.json),
[runtime preflight](runtime_preflight.json), and the prospective
[review protocol](review_protocol.md) retain the design. Three domains (network,
watering, held-out baking) each have F-new, F-same and S-rephrased schedules with
ten planned accepted turns. Domain openings, D100 state, seed rule, host settings
and context policy are shared. Quinn uses the existing shared conversational
partner machinery with a private factual ledger/action; only its public message
reaches Gemma. Required facts/quantities/negation are checked before dispatch.

Gemma retains the resident model/quantization/reasoning configuration. It receives
a 2,048-output-token ceiling without a brevity instruction. The 4,096-token server
context allows at most the existing last two complete pairs and a 1,792-token
prompt bound, with a 256-token reserve. Normal omission of older history is
distinct from extra omission for headroom. Input token coverage and adapter
semantic coverage are recorded separately. No extra model or judge is introduced.

Root read every attempted transcript before scores. [The fidelity review](fidelity_review.md)
contains quotations, whole-trajectory validity decisions, partial attempts and
assistant progress within nominal circling conditions. The two allowed complete
replacements were assigned to the first two invalid original trajectories before
scoring, with unchanged construction and predeclared seed offsets. No call was
repeated because the repository advanced. No metric selected a replacement.

## Interpretation boundaries

Arc age says how many accepted members have been observed in the current declared
arc. These schedules deliberately keep their broad topic fixed; this is not an
independent semantic detector confirming that an arc never changed. The offline
pivot control exercises an actual supplied transition and age reset.

Text overlap measures surface reuse. Existing extraction can support conceptual
movement only when the required source/window is covered. Missing or partial
extraction is unavailable, never zero novelty. Generic numeric/negation/outcome
atoms can notice changed evidence with stable nouns but cannot establish its
truth, utility or implications. Post-response extraction cannot regulate the
already-produced reply.

Historical strength describes what the saved learner makes accessible. Comparing
its normalized distribution with actual SAA weights describes reshaping by
context and separately retained adjustments, not causal influence on prose or
an ideal mixing coefficient. Frozen-history concentration is expected to stay
constant across turns.

[Model-free controls](controls.md) expose both useful behavior and false signals:
literal repetition scores highly; changing quantities with fixed labels lowers
the evidence-aware repetition candidate; concise resolution can look stagnant;
copy-boundary marker fragments create false novelty under padding. These are
engineering controls, not successful live classification evidence.

## Outcome and primary comparison

**No reliable focused-versus-stagnant separation is established.** Only c003
(network S-rephrased) passes the complete-trajectory fidelity gate. There is no
valid F/S pair, including in the held-out domain. This is first a construction
failure, not evidence that a classifier achieved or failed a particular accuracy.
The review caught assistant quantity/negation errors, loss of task context,
private action leakage, and useful new proposals in a nominal S conversation.

The original matrix yielded 87 accepted turns; two complete permitted replacements
yielded 20 more. Six preflight turns are kept separately. There were 328 normal
calls: 113 Gemma, 113 existing extraction and 102 Quinn. Instrumentation, replay
and historical diagnostics made zero model calls. All 113 Gemma replies stopped
naturally; none hit the 2,048-token ceiling. There were no extra whole-pair removals
for headroom. All text reached the extractor within its verified word-token bound.
Gemma reported 50,076 completion tokens and Quinn 3,343 across all phases;
extractor token usage is unavailable. See [evidence validation](evidence_validation.json).

## Turn matrices and availability

The [CSV matrix](analysis/matrix.csv) contains **642 rows**: all 107 accepted
main/replacement turns × participant/Gemma/combined × windows 3/5. It includes
original authored condition, validity, turn, arc identity/age/pivot, source length,
primitives, composites and SAA field statistics. Empty cells mean unavailable.
[Full rows](analysis/rows.json.gz) retain quotes, atoms and candidate diagnostics;
[grouped summaries](analysis/summary.json) retain denominators and early/middle/
mature phases for each conversation before any pooling. All live arc-pivot flags
are false by the supplied broad-domain grouping. Rejections are not arc members.

Coverage for each 107-turn source view (identical across windows):

| View | No known pipeline omission | Nonempty concept sets | Known empty sets | Incomplete/unavailable sources |
| --- | ---: | ---: | ---: | ---: |
| Participant | 43 | 4 | 39 | 64 |
| Gemma | 1 | 1 | 0 | 106 |
| Combined | 1 | 1 | 0 | 106 |

No concept/relationship rolling novelty mean or structural/evidence composite is
available at either window. Thus old C1–C3 and the new structure/evidence-aware
composites are **untested on this live recording**, not zero. Whole-arc new
structure is available only for participant c003 turns 2–4: counts 3, 0, 0;
per-100-meter-token rates 10.714, 0, 0. These three readings cannot compare F/S.
There is only one nonempty evidence-atom observation per source view, and no
rolling evidence progression. For example, c202 turns 6, 7, 9 and 10 contain
explicit new counts in the full text but have covered **empty** extracted source
sets and no evidence quotes. Text availability is not semantic extraction recall.

The source text still supports surface repetition on 96/107 turns per view: the
11 openings lack a preceding turn. Wider windows do not repair missing semantic
information. The primary [length-matched subset](analysis/length_matches.csv) is
empty because there is no primary-valid F-same trajectory. This coverage failure
is reported rather than filled with invalid trajectories or selected fragments.

## Descriptive findings from all attempts

These are diagnostics on original authored conditions, **not primary F/S results**.
Mature means use accepted turns 6–10 (only 6–8 for incomplete c008).

| Attempt | Authored condition | Primary valid | Participant surface repeat W3 | Gemma surface repeat W3 | Mature Gemma meter-word count |
| --- | --- | --- | ---: | ---: | ---: |
| c001 network | F-new | no | .054 | .123 | 376.2 |
| c002 network | F-same | no | .433 | .249 | 206.6 |
| c003 network | S-rephrased | yes | .077 | .199 | 190.4 |
| c004 watering | F-new | no | .042 | .078 | 225.0 |
| c005 watering | F-same | no | .272 | .127 | 208.8 |
| c006 watering | S-rephrased | no | .050 | .150 | 285.2 |
| c007 baking | F-new, 9 turns | no | .041 | .102 | 257.8 |
| c008 baking | F-same, 8 turns | no | .379 | .088 | 191.0 |
| c009 baking | S-rephrased | no | .041 | .174 | 217.0 |
| c201 network replacement | F-new | no | .151 | .145 | 282.0 |
| c202 network replacement | F-same | no | .380 | .309 | 222.6 |

The fixed word3/character5 candidate confuses repeated phrasing with stagnation.
In all original domains, F-same participant text scores more repetitive than
S-rephrased participant text despite its real numeric/constraint changes. A
larger window retains that problem: c008 participant W5 mature mean is .390,
versus c003 .095. This is a likely false broadening signal for focused evidence
accumulation. It cannot be repaired by merely waiting for an older arc.

Speaker separation does expose a useful diagnostic. In c202, Gemma's final
surface score is .775 after the review identified its repeated false
"Instability to Silence" interpretation. Its raw early mean is .161 and mature
mean .309. In c008's useful but incomplete mature segment, Gemma's mean falls
from .132 early to .088 mature while the participant's rises .160 to .379.
For the valid c003 circling exchange, Gemma rises .139 to .199 and participant
.027 to .077. These patterns overlap and depend on phrasing; they are not a
validated stagnation threshold, and source novelty does not prove useful thought.

Response length is variable and sometimes shorter in mature turns. Across all
main/replacement turns, recorded whitespace word counts range 92–448 for Gemma;
the meter uses the existing lexical tokenizer, so its word denominators differ
slightly. Both definitions remain inspectable. Neither length nor normalized
structure rates establish effort or quality. There are no capped observations to
exclude, but no valid matched length comparison to support a length-independent
F/S claim either.

## Contextual and historical axes

The focus-related primitives are available but measure different things. Positive
stored-graph activation coverage ranges .131%–2.678% across turns. Opening/recent
text continuity is available independently. c008's mature participant recent-text
Jaccard is .390 versus c003 .180, correctly describing stronger lexical continuity
without implying less progress. Activation concentration alone is ambiguous:
mature c005 HHI is .289 at .389% graph coverage, while c003 is .118 at 1.38%.
Concentration should therefore remain separate from activation mass and coverage.
The model-free topic pivot drops opening overlap to zero and resets supplied age.

The [historical diagnostic](history_diagnostic.json.gz) reuses all 107 exact
recorded queries and field seeds on D100 and R8 with no generation or state writes.
Both file hashes remain unchanged. Candidate universes differ, so TV is computed
within each state's eligible set, not between unmatched universes.

| Frozen state | Eligible candidates | Earned entropy (nats) | Effective count | Earned top mass | Earned HHI | Mean earned-to-conditioned TV | Maximum TV |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D100 CompactStore | 54 | 3.5128 | 33.5406 | .06623 | .04188 | .00680 | .06460 |
| R8 historical read-only | 21 | 2.6412 | 14.0304 | .28571 | .11464 | .02170 | .13265 |

This axis works as an inspectable distribution diagnostic: R8 is more concentrated,
and context reshapes its weights differently. Earned baselines are constant, as
expected for frozen histories. Mean normalized rank displacement is .00968 for
D100 and .01869 for R8. Tiny TV/rank changes can also arise from existing
fixed-point probability rounding and ties; they are not evidence of semantic
importance. Applied accessibility adjustment maps are empty in these runs and
remain separate from earned strength. No introspection call was added.

D100's candidate set stays at 54 with adjacent overlap 1. Background-only eligible
counts range 50–54 and their total mass .7963–1.0000. There are 49–53 unselected
background candidates per turn. This directly shows eligible alternatives remain
available, but "background" is the field's contextual class, not a semantic
distance oracle. Repeated landing/neighborhood/route diagnostics are preserved;
they offer no established progress distinction in this frozen-state recording.

## Verdict and smallest next experiment

* **Contextual focus:** useful descriptive instrumentation for vocabulary fit and
  continuity; ambiguous as a focus-quality meter. Keep magnitude, coverage and
  concentration separate. Graph sparseness, common vocabulary and topic-preserving
  new evidence can all mislead a single scalar.
* **Historical pull:** promising and directly supported as a distribution/state
  diagnostic. It measures what is accessible and context's reshaping of those
  odds; it does not establish prose influence or an exploration mixing weight.
* **Stagnation/exploratory opportunity:** not demonstrated. Arc age alone is
  nondiscriminating; lexical repetition has clear false signals; structural and
  evidence-aware composites lack usable rolling inputs here. No composite is
  shown superior to primitives. A nonzero wildcard possibility remains a future
  design concern, not an implemented floor or schedule.

False positives include concise resolution, corroborating tests with the same
nouns, correct repeated constraints, sparse extracted representations and short
answers. False negatives include paraphrased circling, boilerplate with changed
wording, and nominal F participant novelty masking an assistant error loop.
Private action leakage and limited conversation context confound construction.
Missing extraction must never trigger broadening by being interpreted as stasis.

The smallest justified next step is one short, fixed F-same/S pair plus a concise
resolution control, with required facts **and actual conversational actions**
reviewed before generation, followed by the same whole-exchange fidelity gate.
First test whether already-retained raw extraction/text can supply supported
numeric/negation changes without the current coverage collapse; this need not
start with another model role. Freeze any representation revision on controls,
then test once on that new pair. The current result does not prove additional
semantic inference is necessary, but it does not supply a reliable substitute.

Only after that prerequisite should a separately authorized small experiment
compare unchanged SAA against one predeclared bounded exploration adjustment on
matched continuations from the same frozen state/seeds. Use measurements from
completed prior turns, treat unavailable signals as no evidence for adjustment,
and inspect both productive-focus disruption and circling behavior. Preserve
some wildcard accessibility as a future constraint. Change accessibility odds,
never prescribe a weird analogy. No such modulation is implemented here.

## Reproduction and integration

The [evidence index](evidence_index.md) links frozen raw requests/results,
transcripts, rejections and operational coverage. The [replay receipt](replay_validation.json)
confirms byte-identical matrices, summary, length matching, provenance receipt and
historical diagnostics, with the frozen formula hash unchanged.

To regenerate reports without inference:

```bash
PYTHONPATH=src:. python tools/report_pressure_meters.py \
  docs/experiments/three_pressure_v2/main/records.json.gz \
  docs/experiments/three_pressure_v2/replacement1/records.json.gz \
  docs/experiments/three_pressure_v2/replacement2/records.json.gz \
  --manifest docs/experiments/three_pressure_v2/main/condition_manifest.json \
  --manifest docs/experiments/three_pressure_v2/replacement1/condition_manifest.json \
  --manifest docs/experiments/three_pressure_v2/replacement2/condition_manifest.json \
  --fidelity-review docs/experiments/three_pressure_v2/fidelity_review.json \
  --output /tmp/mneme-meter-replay
```

Historical replay uses `tools/compare_pressure_histories.py` with
`all_meter_inputs.json.gz`, the retained R8 snapshot path, `--fidelity-review` and
`--output`. The retained diagnostic includes its full secondary field/strength
inputs, so inspection and arithmetic replay do not require a new generation.
The frozen D100 snapshot remains external; its full per-turn measurement inputs
are retained here rather than duplicating a large developmental database.

After live work ended, fetching `origin/main` confirmed the starting promotion
commit `7a74a92` was still current. This work already descends from that boundary;
no rebase conflict or persistence exception was required. No production persistence,
SAA, learner, extractor or conversation-runtime implementation was edited.

[Validation](validation.json): all **688 tests** passed, repository Ruff passed,
and strict package mypy passed across 70 source files. The three new tools also
passed explicit strict checking with imported historical-module diagnostics
suppressed. An expanded import traversal exposed a pre-existing `Any` return in
the unmodified historical runner; it is documented rather than silently repaired.
The prior disk-full test attempt was inconclusive and superseded by the complete
RAM-backed test run. Tests cover purity/call isolation, deterministic replay,
prefix-only age/reset, high movement/repetition, missing coverage, source separation,
distribution arithmetic, construction gates, read-only state and report label
isolation. Final remote CI is checked on the integrated commit at publication.

This task stops at measurement and evidence. No historical campaign, developmental
retuning, exploration modulation or Phase Four work is started.

Implementation commit `6f13785a957b429e02e888c284761fd2ad33edd1` passed
[GitHub CI run 37054892755](https://github.com/nova-rey/mneme/actions/runs/37054892755).
The [publication receipt](publication_validation.json) records that exact tested
revision. The subsequent closure commit only records validation and queue closure;
its final CI and local/remote ref agreement are verified at handoff.
