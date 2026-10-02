# Prospective fidelity and analysis gate

The source specification is byte-preserved in `specification.md`. The isolated
implementation branch starts at `7a74a92cbd0c084d420a7da9444bd1258d660b4c`, after
the three persistence-promotion commits following the first pilot. That pilot is
immutable. No persistence-promotion source file is in this task's edit scope.

The frozen meter definitions are in `formulas.json`, initially SHA-256
`42611164905d84c7a76b94d66d88ed14a101f4cba950c2de750a9d1c2160ff18`.
They were reviewed before live meter scores. No formula changes, coefficient
search, classifier, or threshold fitting follow inspection of results.

Network and watering are construction/development domains. Baking is the
untouched-domain check: no scored baking results are inspected before definitions
are frozen. All conditions share a domain opening, frozen developmental state,
host settings, seed rule, and context policy. Labels and private ledgers are
joined into reports only after measurement, never passed to meter functions.

## Construction and coverage decisions

Start at 2,048 Gemma output tokens, without a brevity instruction or reasoning
change. The actual resident server advertises a 4,096-token context. Use existing
last-two-pair conversational history and remove the oldest complete pair until
the rendered prompt fits 1,792 tokens, leaving 2,048 output plus a 256-token
reserve. Tokenization/template application are preprocessing, not model inference.
Apply this same policy to all conditions, retaining actual omissions and token
counts. If the current turn and system cannot fit, reject before generation.

Quinn receives a private factual ledger and action. A deterministic gate checks
required factual sentences, quantities and negation before Gemma dispatch.
S-rephrased ledgers must vary wording while preserving the same situation; a
repeated fixed sentence is not a sufficient construction of paraphrased circling.
All conditions use the same rendering style. Exact lexical gates are conservative
construction checks, not sufficient fidelity judgments.

The existing GLiNER path combines participant and response source slots in one
call. Token coverage and adapter capacity are distinct: the existing adapter
retains at most six relationship proposals, possibly omitting evidence from one
speaker. Retain raw extraction, source spans, normalization decisions and coverage
status. Partial or unknown coverage cannot become an empty semantic observation.
Quantities/markers are source-supported lexical observations, not inferred facts
or proof of advancement.

## Required review before scoring

Root reads every resulting transcript and publishes a separate fidelity record
with exact supporting quotations before any new meter score is inspected.
Preflight is reviewed first; construction can be corrected within its finite
budget before final prompts and schedules freeze. Main attempts are immutable.

For each trajectory, record:

* factual fidelity: required observations/quantities/negation arrived, and no
  unsupported results were claimed;
* pattern fidelity: F-new adds useful distinctions within one task; F-same
  advances evidence/tests with largely stable vocabulary; S-rephrased adds no
  factual advancement despite changed wording;
* exchange fidelity: whether Gemma itself contributes useful new structure or
  resolves a supposedly circling exchange, and whether apparent F progress is
  merely repeated speculation;
* coverage: accepted/missing turns, capped answers, omitted context pairs,
  extraction coverage, source separation and any semantic ambiguity.

Missing required evidence, invented results, or a material pattern departure
invalidates the entire trajectory for the primary comparison. Preserve partial
attempts and reasons; do not splice, relabel, or regenerate turns inside a
trajectory. At most two full replacement trajectories use the same frozen design
and predeclared replacement seeds. No additional live budget is inferred from
successful attempts or from a wish for clearer scores.

Review may classify a trajectory as fidelity-unavailable/invalid; this is not a
meter failure. Record capped answers as incomplete observations and exclude them
from claims about natural response length. Do not hide valid inconvenient turns.

## Analysis rules

Only after the signed/dated review artifact exists, compute windows 3 and 5 for
participant, Gemma and combined views over the same recorded inputs. Retain all
attempts; primary comparisons use the pre-score validity decisions. Summarize by
conversation and domain before pooling, disclose availability denominators and
length-matched subset coverage, and treat overlapping windows as dependent.

Compare F-same against S-rephrased explicitly. Describe disagreements using actual
source passages. Neither lexical novelty nor response length establishes quality,
motivation, effort, progress or causation. A failure of construction is reported
separately from missing measurement and an unhelpful meter on valid conditions.

Historical diagnostics use two frozen states and the same recorded inputs with
no generation. Compare strength and context-conditioned distributions within each
state's actual eligible candidate set, preserving canonical bindings and accepted
adjustments separately. Different eligible universes are disclosed.

Model-free literal repetition, topic pivot, concise resolution and repeated-text
padding are engineering controls, not additional live conversations. No diagnostic
or control writes to developmental state or feeds back into SAA.

The task stops after evidence, tests, CI and serialized integration. No regulator,
probability floor, automatic shake-up or claim of curing a measured loop follows.
