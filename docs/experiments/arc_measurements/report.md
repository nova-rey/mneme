# Passive arc movement investigation

Scope: prospective measurement only. No SAA regulator, selector adjustment,
learner retuning, new judge, historical campaign rerun, or Phase Four work.
Source baseline: `99075e4d40e1df40d82b70422c89192cfbdacd63`.

## Existing machinery, inspected before implementation

| Runtime surface | Existing information and limits |
| --- | --- |
| `development/episodes.py:EpisodeTracker` | Accepted turn IDs, ordinals, caller-supplied topic keys, one-turn tangent tolerance, explicit pivots, closure and reentry. This is not open-ended semantic inference. |
| `declared_conversation_arcs` / `persist_conversation_arc_progress` | Adjacent equal schedule labels define arcs; bounds and membership are persisted. Full declarations include future members: current age must count only the prefix through the current accepted turn. Ordinal span can differ from membership age. |
| `experiments/contingent.py`, `p23_supplement.py` | Schedule chapter labels supply topics. Labels are experimental inputs, not independent evidence of coherent discussion. |
| `tools/run_p3_introspection_100.py:_arc_slices` | Separate review-boundary helper: explicit participant discourse markers after at least two turns, bounded arc count. Its docstring mentions lexical divergence, but implementation does not use lexical divergence to cut arcs. |
| `experiments/shared_interloper.py` | Quinn/Qwen receives private concerns and shared assistant responses. Gemma sees its own history only, normally two previous pairs. This study reuses that machinery without exposing condition labels. |
| `experiments/pilot_runtime.py:extract` | Existing extractor call yields validated `ExtractionOutcome.residue`; request, raw response, normalization, and validation are available. Capturing the normalized residue avoids later database joins and requires no inference. |
| `memory/interpretation.py`, `residue.py`, `resolution.py` | Source-role/slot provenance, concepts, candidate relationships and routes. Exact normalized labels and explicit aliases are supported; semantic synonym resolution is not. Concept/edge local IDs are not reliable cross-turn semantic identities. |
| `development/field.py:FieldResult` | Full final accessibility weights, landing, contextual activations, active neighborhood, propagation paths, and contextual/background component classes. `active_concepts` includes zero-activation concepts; concentration must use positive contextual activations. |
| `state/compact_runtime.py` | Same field result plus health diagnostics. No CompactStore changes are needed. |

## Available signals and missing information

Direct: accepted ordinals and arc membership; normalized extracted concepts,
relationship candidates and source provenance; candidate weights, sampled landing,
active neighborhood, propagation paths, and contextual activations.

Cheap derivations: membership age, ordinal span, adjacent/rolling set movement,
new-label/triple proportions, repetition, union expansion, structure per accepted
turn, candidate entropy/effective count, maximum mass, positive-context HHI,
candidate/neighborhood/path overlap, repeated landing, and background-only mass.

Not available: a reliable judgment of human progress, equivalence of arbitrary
paraphrases, whether new evidence changes a diagnosis without changing extracted
labels, semantic distance of background candidates, or a counterfactual benefit
from exploration. No extra inference is introduced to fill those gaps.

Relationships are compared as normalized endpoint-label / relationship /
endpoint-label triples, not residue edge IDs: the minimal extractor's edge IDs
include source slot and evidence text. Normalization is existing NFC, whitespace
collapse, and casefold; no inferred synonym merging. Extracted structure is not
necessarily admitted or earned developmental structure.

## Definitions frozen before live results

Window = 3 accepted turns. Age starts at 1 and resets at an existing arc boundary.
Maturity = `min(1, (age - 1) / 5)`. Rolling concept and relationship novelty means
use each turn's fraction unseen in its preceding, at-most-three-turn window.
The first turn has no baseline, not novelty 1. A full known, nonempty measurement
window is required; with window 3 the first composite can occur at age 4.

* C1 = maturity × (1 − rolling concept novelty mean).
* C2 = maturity × (1 − mean(rolling concept novelty mean,
  rolling relationship novelty mean)).
* C3 = C2 × contextual HHI.

These are structural repetition proxies, not calibrated probabilities or quality
scores. They are not optimized against condition labels and feed no runtime rule.
Missing or insufficient semantic information stays unavailable. An empty valid
extraction is distinguishable from extraction failure, but supplies no denominator
for a novelty proportion. Unknown windows are not silently bridged.

Existing SAA `novelty` is one minus maximum lexical context activation, not
within-arc novelty. Final distribution entropy mixes context, developmental
strength and existing adjustments. Background-only means zero measured lexical
activation, not proven semantic distance; the lottery has no separate wildcard
draw. Neighborhood movement can reflect a different seeded landing while the
conversation is unchanged.

## Implementation and reproduction

`src/mneme/experiments/arc_measurements.py:measure_conversation` is a pure offline
function over recorded dictionaries. It accepts interleaved conversations,
validates order and frozen membership, and never receives a store, controller or
host. No existing production file imports it. The new runner's `--replay` path
constructs no hosts; measurement is performed after generation. The original
selector, extractor, learner, renderer, episode machinery and CompactStore are
unchanged.

The input record carries `conversation`, `condition` (reporting metadata only),
`turn`, accepted `ordinal`, frozen `arc`, optional `accepted_turn_id`, validated
`residue` or null, and pre-generation `field` or null. Output retains normalized
labels/triples so each set comparison can be inspected. Local keys and evidence
hashes cannot manufacture novelty. Source quotes remain in the raw residue.
Whole-arc comparisons become unavailable after a missing earlier observation;
rolling comparisons recover once their required contiguous history is known.
Successful empty extraction yields count zero and, with a known prefix, zero new
structure; undefined proportions and composites remain null. `warmup` describes
the three-turn set window; `composite_warmup` also accounts for the first turn's
missing comparison baseline.

The `concept/relationship_*` fields expose count, whole-arc novelty, new count,
adjacent movement, prior-window novelty/repeat, window coverage, saturation,
rolling novelty mean and rolling new structure per turn. Saturation is
`1 - |union(sets)| / sum(|set|)` across three current/recent turns: its maximum
for three identical nonempty sets is 2/3, not 1. Lottery weights are normalized
before entropy `-sum(p*log(p))`; effective candidate count is `exp(entropy)`.
Contextual HHI is `sum((positive_context_weight / total_positive_weight)^2)`.
Landing repetition is `1 - distinct_landings / window`; paths retain order.
Empty/all-zero distributions are unavailable, while a singleton has entropy 0.

```sh
.venv/bin/python tools/run_arc_measurements.py --replay \
  docs/experiments/arc_measurements/records.json --output /tmp/arc-measurement-replay
```

That command reproduces full JSON/CSV matrices and transcripts without any model
call. [Construction and live invocation](construction.md) describe the optional
explicit `--execute` path. No historical receipt supplies experiment outcomes.
Determinism is a recorded-input measurement guarantee, not a claim that hosted
Quinn or a fresh live conversation will reproduce identical text.

## Conversation construction and retained evidence

Two topics × F/S × ten turns = **40 accepted turns**. Each matched pair shares
its opening, initial checkpoint and per-turn Gemma/field seeds. Quinn uses the
existing shared builder with the single Gemma reply duplicated in its private
A/B slots. Only Quinn sees that turn's authored circumstance; Gemma sees its own
two-exchange history and the generated public message. No F/S labels, requests
for weirdness, forced callbacks or target analogies enter Gemma's instructions.

Watering concerns a balcony reservoir/cotton-wick setup. Its intended F schedule
adds measured inflow, evaporation, reservoir height, wick width, pot-specific
needs and a reserve budget. S repeatedly revisits overwatering versus drying.
Network concerns a workshop sensor disappearing from a dashboard. Its intended
F schedule adds neighboring-sensor comparisons, uptime resets, measured voltage,
cable/outlet/battery tests and access-point evidence. S revisits power versus
Wi-Fi uncertainty without test results.

* [Frozen private schedules and definitions](construction.json),
  [construction details](construction.md), [model bindings](bindings.json).
* [Complete Quinn/Gemma transcripts](transcripts.md) and [all raw calls](calls.json).
* [Raw measurement inputs](records.json), [40-turn readable matrices](matrix.md),
  [full scalar CSV](matrix.csv), [full JSON](matrix.json).
* [Descriptive aggregates and matched-turn comparisons](analysis.json),
  [call summary](summary.json), [state invariance checks](state_checks.json).

The completed run used exactly **40 Gemma + 40 GLiNER + 36 Quinn = 116 calls**,
all returned, with **zero measurement or judge calls** and no retries. All 40
extractions validated; six were empty: watering-F 2, watering-S 9, network-F 2,
network-S 8–10. Empty extraction is not evidence that nothing meaningful happened.
Every conversation had one declared arc, age 1–10, with no declared pivot. The
current fork's accepted revisions happen to be 1–10; the runner queried them.
No extra topic-switch conversation was run. Existing pivot/reset behavior is
covered by synthetic tests, not claimed as a live control result.

Four isolated descendants came from the same read-only R8 checkpoint. Before/after
hashes of graph concepts/edges/routes and learner values/updates matched for each;
the source checkpoint's SHA-256 also matched after the study. These are the
checks actually retained by the live process. Later runner hardening also
requires and hashes snapshot tables, but is not retroactively claimed as live
evidence. Graph/learner publication was intentionally absent: these are new
conversations over a fixed developmental state, not a developmental campaign.
Disposable databases remain outside Git at `/tmp/mneme-arc-measurements-v1`.

## Realized-condition fidelity

**The intended contrast was only partly realized.** Inspection of the actual
messages found that Quinn omitted several F circumstances. Watering-F did add
40 grams/four hours at turn 3 and a three-day/400 ml budget at turn 9, alongside
material/evaporation distinctions, but dropped other scheduled evidence.
Network-F introduced uptime resets, then drifted into speculative re-sync/power
load discussion at turns 4–10 instead of consistently presenting the planned
cable, battery and access-point results. Its final turn asks which components to
monitor during staggered re-sync. That is not a clean instance of the authored
productive troubleshooting sequence.

S also sometimes introduced approaches: network-S turn 4 proposes moving the
router/borrowing a booster. Turns 5 and 6 then repeat the same message verbatim;
turns 8–10 include a battery plan, conversational closure and renewed uncertainty.
Thus these are **intended labels**, not independent verified quality classes.
No labels were relabeled, no conversation rerun, and no metric optimized to
repair the result. The modest sample and construction failure make this a
measurement-feasibility pilot, not a validated F/S benchmark.

## Comparison at comparable arc age

Mature means age 6–10, where the frozen maturity factor reaches 1. All groups
have five such turns. Values below are means over available rows; parentheses
give available n out of 5. Missing values are excluded, not zero-filled.

| Mature statistic | Watering F | Watering S | Network F | Network S |
| --- | ---: | ---: | ---: | ---: |
| Recent concept novelty | .978 (5) | .626 (3) | .811 (5) | .655 (2) |
| Recent relationship novelty | 1.000 (5) | .889 (3) | .956 (5) | 1.000 (2) |
| New concepts per turn | 5.067 (5) | 2.200 (5) | 3.800 (5) | 1.533 (5) |
| New relationships per turn | 3.667 (5) | 2.733 (5) | 4.467 (5) | 1.600 (5) |
| Concept saturation | .000 (5) | .120 (5) | .175 (5) | .054 (4) |
| C1: age × concept persistence | .022 (5) | .374 (3) | .189 (5) | .345 (2) |
| C2: age × concept/relationship persistence | .011 (5) | .243 (3) | .117 (5) | .173 (2) |
| C3: C2 × context HHI | .009 (5) | .192 (3) | .038 (5) | .038 (2) |
| Effective SAA candidate count | 14.052 (5) | 14.183 (5) | 14.036 (5) | 14.031 (5) |

Early turns cannot support a composite: there is no previous baseline at turn 1.
In the S conversations, C2 at turn 4 is only .046/.029, then rises later.
Both F turn-2 extractions are empty, delaying their first available composite to
turn 5. That delay reflects measurement coverage, not evidence of productive focus.

At the same mature turn, C1/C2/C3 are higher in S for all **five jointly available
pairs** (watering 6–8, network 6–7). That is only 5 of 10 possible mature pairs.
It is not five independent replications: windows overlap and observations belong
to four conversations. The missing late-S windows are precisely where a detector
might be useful. C2 is not shown to improve on C1 or concept novelty; adding
near-ceiling relationship novelty dilutes the concept contrast. C3's network
condition means are essentially identical, and its ranges overlap substantially.

Across mature network turns, F's C1 range .114–.319 overlaps S's .310–.381;
C2 ranges .079–.188 and .155–.190 also overlap. A threshold near .17 would flag
intended-F turn 10 (C2 .188) and miss S turn 6 (C2 .155). This is an illustrative
false signal, not a fitted threshold, and the F fidelity failure prevents calling
it a confirmed false positive on truly productive discussion. There is no valid
human-quality confusion matrix here.

Adjacent concept movement reaches 1 even in mature S; network-S relation novelty
is 1 in both available mature windows. Neither is a reliable stand-alone sign of
progress. Network concept saturation goes in the opposite expected direction on
three of four comparable mature turns. Changing extracted labels/phrasing and
empty observations can overwhelm the intended dynamics.

A concrete example: network-S participant turns 5 and 6 are identical, but the
extracted concepts change from `battery, device, failure, fix, no power, power,
power test` to `no power, troubleshooting`. Turn 6's relationship is
`troubleshooting / depends_on / no power`, a new triple despite the repeated
participant message. This exposes the effect of assistant-side structure on the
measurement without needing a judge call.

SAA has **21 candidates throughout**; consecutive candidate-set Jaccard is 1.
The fixed graph makes those statistics uninformative here. Mature entropy is
approximately 2.64–2.69 nats, with high background-only mass (means .962–1.000).
Matched conditions have identical landings and neighborhoods on 9/10 turns for
each topic. Seeded landing/neighborhood reuse adds no useful mature contrast in
this pilot. A background candidate losing is observable, but is not evidence of
unmet creative need or a semantically distant option being suppressed.

## Promising, ambiguous and uninformative candidates

* **Promising for another passive test:** recent concept novelty/persistence and
  new-structure counts per accepted turn. They differ at equal age in this pilot,
  especially watering. These are exact-label structural statistics only.
* **Ambiguous:** C1 is an interpretable age-gated presentation of concept
  persistence, not demonstrated additional information. C2 adds coverage demands
  and near-ceiling relationship novelty without demonstrated benefit. Whole-arc
  novelty conflates length with repetition; rolling windows are easier to
  interpret. Relationship novelty, adjacent movement and saturation produce
  conflicting signals, particularly in the compromised network pair.
* **Not useful for discrimination here:** age alone (matched by construction),
  candidate-set overlap/count (constant), landing/neighborhood reuse, and the
  contextual-concentration composite C3. Field entropy/HHI remain potentially
  useful diagnostics, but these results do not support them as stagnation signals.

There is no demonstrated composite that separates the conditions more reliably
than the best primitive. No classifier, cut point, coefficient or window was fit.

## Failure modes and practical limits

1. The label representation misses synonymous repetition and can mistake new
   numbers, evidence or constraints about unchanged concepts for stagnation.
   Conversely, fresh wording can look like progress during a loop. A legitimately
   focused confirmation/measurement phase is a likely false positive.
2. Extraction observes participant and assistant sources. Assistant elaboration
   can add structure while the participant circles; concise agreement can yield
   an empty residue. No inference separates useful from decorative structure.
3. **34/40 Gemma outputs ended at the existing 256-token cap**: all watering F/S
   and network F outputs, plus four network S outputs. Mature network replies
   average 164 versus 75.8 whitespace-delimited words (F/S); watering 163.2 versus
   161.2. Network progression rates are therefore confounded by response length
   and conversational closure. Word counts are descriptive, not quality metrics.
4. Coverage is selective. Six valid empty extractions suppress ratios; all final
   three network-S turns lack composites. Available-case means can overstate
   separation. Empty counts may lower structure rates without measuring stagnation.
5. Fixed initial graph, seeds, extraction vocabulary and topic familiarity limit
   transfer. No developmental adaptation, replicated seed blocks, genuine live
   pivot control or independent quality ratings were tested.
6. Age inherits the chosen existing arc contract. A constant declared topic cannot
   detect an unannounced semantic pivot. This study does not validate that detector.
7. Measurements use post-response extraction and pre-response field traces.
   A future online consumer could only apply the completed-turn signal to a later
   turn; applying it to that same generation would introduce look-ahead.

## Conclusion and smallest next experiment

**Existing information supports cheap, explainable structural measurement, but
this pilot does not establish reliable stagnation detection.** Some signals
separate intended conditions without another inference call; limitations of
exact-label extraction, selective coverage and conversation construction prevent
a stronger claim. This is not proof that an additional semantic model call is
necessary: existing source-role information and a better controlled conversation
construction remain untested opportunities.

Before treating any statistic as a regulator input, use one new matched F/S
Quinn transcript pair whose realized evidence progression/circling is inspected
and frozen in advance. Reuse those exact public messages across two isolated
Gemma copies per condition: unchanged SAA versus one prospectively specified,
small bounded exploration adjustment, with matched checkpoint/seeds and response
budget. First require a passive coverage/fidelity gate on that construction; if
it fails, stop without intervention. This is a proposed four-conversation pilot,
not an authorized or implemented follow-on.

Use age plus recent concept persistence as the simplest candidate, retaining
primitive values and requiring adequate coverage; this evidence does not justify
the relationship/concentration composites. The future adjustment would affect
odds among already eligible history-shaped associations, not force a callback or
analogy. Preserve some nonzero opportunity for eligible less-obvious associations
as a future design constraint; no floor, multiplier, schedule or balancing policy
is chosen or implemented here. Compare normal SAA and the proposed bounded
adjustment for inappropriate broadening during verified productive focus as well
as behavior during circling, without an added judge call.

## Verification

* Full repository pytest: **621 passed** (52.58 s).
* `ruff check .`: passed.
* Strict `mypy src/mneme`: passed, 68 source files.
* 25 instrumentation tests cover reproducibility/input immutability, declared arc
  age/reset with ordinal gaps, missing members/semantics, successful emptiness,
  local-ID/quote-hash invariance, synthetic movement/repetition, field edge cases,
  and generation/state/provider-count parity using the real controller/FakeHost.
* Five runner tests cover budget/lengths, private partner scheduling, pass-through
  recording, refusal of existing output before calls, and byte-identical replay
  while host constructors are forbidden.
* Existing episode, shared-partner, SAA/field and controller regressions pass as
  part of the complete suite. Read-only matrix replay and artifact validation are
  retained in `validation.json`.

The code changes are additive. Historical evidence, SAA probabilities and current
developmental state remain unchanged. Unrelated pre-existing untracked workspace
artifacts are preserved. Stop boundary: report this result; no regulator or larger
campaign follows without explicit authorization.
