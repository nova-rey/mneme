# Final passive-meter closure

Result: retain a vector of inspectable context/history, quantity-change and surface
readings. General semantic movement and understanding/coupling are not measurable
reliably with current signals. The bounded prospective check was incomplete;
its failures and all usable evidence are retained without further regeneration.

This bounded experiment separates the environment supplied by Quinn from Gemma's
response. Construction validity depends only on Quinn fidelity. Gemma's circling,
incorrect reasoning or independent exploration cannot invalidate a faithful
environment. The old V1/V2 evidence and receipts remain unchanged.

## Machinery and measurement boundary

The existing episode/arc machinery tracks accepted membership under caller-supplied
topic keys. The runners supply a broad topic per conversation; arc age is observed
accepted membership, not an automatic discourse-quality judgment. A partial
record cannot recover omitted earlier membership. Source-separated exact text,
turn identities, response usage/finish metadata and pre-response field traces are
already recorded. The existing shared Quinn/Qwen partner produces the next public
message; Gemma receives that message, the ordinary system/SAA payload and bounded
conversation history. GLiNER extraction follows generation. Neither new meter is
on that execution path.

Existing context activation uses conservative lexical matching against graph
concept labels. Total activation, positive coverage and concentration answer
different questions and remain separate. Historical pull normalizes the eligible
earned strengths derived from accessibility/support and consequence restraint;
entropy, effective count, concentration and ranks describe that distribution.
Context-conditioned total variation and rank movement describe its reshaping on
the same candidate universe. They do not predict prose or prove conceptual
relevance. Existing source-separated concept/relationship and continuity readings
remain available wherever their inputs support them.

The new `movement_meters.py` is a pure post-hoc function. It reads only recorded
source text and accepted identity/arc ordering. The report joins construction labels
after measurement and separately retains the unmodified V2 readings. The recorder
uses read-only CompactStore/CompactRuntime and existing generation, extraction,
SAA and context helpers. No observer affects prompts, generation, probabilities,
learning, introspection or persistence. There is no runtime hook or policy scalar.

## Frozen formulas and controls

[formulas.json](formulas.json) freezes the regexes, token lists and definitions.
For each participant/Gemma source and each window of 3 or 5 prior same-arc turns:

* Quantity signatures are normalized numeric strings with literal optional units.
  They have exact original character spans. There is no unit conversion, semantic
  referent assignment or fact-versus-plan judgment.
* State signatures contain a fixed negation/state marker with up to two neighboring
  tokens on each side. They expose wording, not resolved propositions or polarity.
* Content sets contain non-stopword, non-numeric tokens. Phrase sets contain
  contiguous original-token trigrams. These are surface diagnostics.
* New count is the current set minus the union of preceding window sets. New
  fraction divides by current set size. Recurrence is maximum Jaccard against
  individual preceding turns. Counts per 100 tokenizer words expose length effects.
* Same-turn and one-turn-lag echo are the fraction of newly introduced environment
  signatures present exactly in Gemma's response. Denominators and matched atoms
  are retained. The two movement readings are paired coordinates, never collapsed
  into an attractor score.

Missing text is unavailable; present empty sets have count zero and undefined
fractions. Opening-turn novelty is unavailable. Partial windows are marked.
All readings are prefix-causal and deterministic. No label or future membership
enters the instrument. Correlations are descriptive Pearson values only, requiring
at least three available pairs and nonconstant series; no fitted thresholds.

Nine model-free controls retain both useful responses and failures: changing
quantities/state wording, literal repetition, paraphrase, concise resolution,
padding, incorrect polarity with exact quantity echo, source mismatch, missing
information and an actual supplied arc pivot. Paraphrase appears novel; repeated
correct resolution appears repetitive; copying quantities with inverted meaning
gives full quantity echo. These failures were retained, not optimized away.

## Preserved V2 development evidence

[The new environment-only review](v2_environment_review.md) examines all 107
accepted main/replacement turns. It restores six complete moving environments
(c001/c002/c004/c005/c201/c202) and retains complete static c003. Moving prefixes
c007/c008 provide 9/8 accepted turns, not completed ten-turn constructions. c006
is qualified static-observation evidence with added hypothetical constraints;
c009 leaked private instructions. This is development material, not a final test.

For W3 with a full three-turn history, the highlighted cases show:

| Reading, mean over available turns | c003 static, t4–10 | c008 moving prefix, t4–8 | c202 moving, t4–10 |
|---|---:|---:|---:|
| Environment quantity novelty | unavailable (0) | .400 (5) | .381 (7) |
| Environment state-window novelty | .952 (7) | 1.000 (2) | .500 (2) |
| Gemma content novelty | .315 (7) | .449 (5) | .232 (7) |
| Gemma phrase recurrence | .130 (7) | .060 (5) | .196 (7) |
| Same-turn new-quantity echo | unavailable (0) | .750 (4) | .500 (6) |

Parentheses give available row counts. Zero recognized quantities in c003 yields
no quantity-novelty fraction; it does not prove semantic stasis. Its .952 state
novelty is a clear false movement signal from rephrasing unchanged circumstances.
c008's changing bake measurements and useful updating coexist with repeated
vocabulary. c202's progressive evidence coexists with Gemma's repeated “Instability
to Silence / Complete Data Loss” framing. Lower model surface novelty helps expose
that case but cannot diagnose its reasoning. Some c202 responses echo numbers
while misinterpreting zero missed updates. c001/c004 show that high lexical
movement can also accompany poor reasoning.

The relationship extractor cannot support comprehensive rolling semantic
measurement: participant coverage flags are true on 43/107 turns, Gemma on 1/107,
both on 1/107. These flags mean no known pipeline omission, not semantic recall.
The full-text instrument remains available without pretending extraction is
complete. Existing unavailable semantic readings stay unavailable.

Historical pull was preserved by exact arithmetic replay of all 107 recorded
D100 and R8 rows, with zero new provider calls or state writes. D100/R8 retain
54/21 eligible candidates, effective counts about 33.54/14.03 and top masses
.0662/.2857. These compare developed distributions within each state's universe;
they do not establish better conversation. See [preservation receipt](history_preservation.json).

## Prospective construction and results

The frozen plan used two matched topics, moving/static per topic, eight turns
each, and at most one environment-invalid replacement. Quinn used the existing
shared partner but had to reproduce exact authored facts and natural questions
(whitespace differences permitted). The ledgers did not tell Gemma to circle or
explore. The stricter phrasing control reduced naturalness and generalized less
widely than free conversation. Topics and quantitative sequences were informed
by V2; this is prospective execution, not an independent domain holdout.

Gemma retained the existing model service, quantization configuration, reasoning
setting, temperature .35, top-p .9, 2,048-token output ceiling and two-prior-pair
context policy. No brevity instruction was added. Native prompt counting and the
1,792-token prompt limit remained unchanged. Runtime metadata retains the model
path/ftype labeling discrepancy from V2; no new exact-weight claim is made.

Execution was smaller than planned:

| Planned trajectory | Retained outcome | Quinn/environment decision |
|---|---|---|
| p001 moving baking | No accepted exchange | Storage reserve failed after first Gemma response returned but before it was saved. Uncertain call retained, never repeated. |
| p002 static network | One-turn opening prefix | Environment valid. Quinn's second message preserved the facts but reused the opening question; the conservative exact gate stopped it before Gemma. This is not environmental invalidity. |
| p003 moving network | Eight turns complete | All required facts reached Gemma accurately; moving condition and privacy preserved. |
| p004 static baking | Eight turns complete | No new observations/results; fixed goal and privacy preserved. |

The untouched p002–p004 schedules continued on RAM-backed storage with a copied
budget ledger retaining the lost p001 reservation. A narrow infrastructure-only
runner change added distinct run reservation and rejects any previously attempted
trajectory. The frozen meter/formulas/construction were unchanged. Original
incident artifacts remain preserved. No replacement ran: neither infrastructure
loss nor a harmless question paraphrase was relabeled as environmental failure
to obtain another attempt. No partial repair or desired-outcome regeneration ran.

Root read the separate Quinn-only transcript and recorded
[validity decisions](quinn_review.json) before computing prospective scores.
All 17 accepted exchanges remain included regardless of Gemma behavior. Total
normal calls were 50: 18 Gemma (one lost), 17 extractor and 15 Quinn. There were
zero measurement calls, zero saved capped responses, and no D100 file/state change.
This does **not** provide four completed trajectories or all four behavioral cells.
Prospective extraction coverage flags are true for participant 2/17 and Gemma
0/17; full exact source text is present for all 17 accepted turns.

After validity review, Root read all retained Gemma responses. In p003, Gemma
distinguishes zero resets with missed reports from zero resets/zero misses, updates
its response to reversals, and later repeats a resolution framing. It does not
reproduce c202's silence/data-loss interpretation. Its claims of perfect health
or 100% efficiency overstate the supplied evidence. In p004, Gemma repeatedly
recommends a test bake, moderate temperature and internal-temperature check;
some ranges/wording vary, but the central approach remains similar. An unchanged
environment gives it no test outcome to react to. These are transcript observations,
not automated conceptual-quality classifications or reasons to invalidate Quinn.

For the two complete trajectories, W3 full-window turns 4–8 have identical ages:

| Reading | p003 moving network | p004 static baking |
|---|---:|---:|
| Environment quantity novelty | .367 (5 available) | unavailable (0) |
| Environment state-window novelty | unavailable (0) | 1.000 (5) |
| Gemma content novelty | .340 (5) | .184 (5) |
| Gemma phrase recurrence | .140 (5) | .235 (5) |
| Same-turn new-quantity echo | .250 (4) | unavailable (0) |
| Mean tokenizer words / reported output tokens | 170.4 / 249.6 | 277.0 / 448.2 |

The content-novelty ranges overlap (.119–.404 versus .129–.254), as do phrase
recurrence ranges (.060–.223 versus .140–.408). p003's final resolution response
has lower content novelty than the static trajectory's mature mean: a plausible
false broadening signal for a legitimately focused/resolved conversation. W5
shows the same broad tendency but has only three full-window rows per trajectory.
Neither an early/mature transition rule nor a classification threshold was fitted.

The static p004 state-window novelty of 1.000 confirms the rephrasing failure.
Quantity uptake also misses explicit evidence: p003 says “120-minute” where Quinn
says “120 minutes.” Literal unit signatures differ, so late duration echoes score
zero despite textual uptake. This frozen failure was not patched after scoring.
Conversely, the inverted-meaning control scores full quantity echo. Exact echo
therefore has both false negatives and false positives for semantic responsiveness.

Across turns 2–8, Gemma content novelty correlates with tokenizer word count at
r=.810 (p003) and .883 (p004), n=7 each; phrase recurrence correlations are
−.741/−.672. These tiny, ordered/autocorrelated series support a length caveat,
not a claim about effort or progress. Environment quantity novelty versus model
content novelty is r=.329 for p003, n=7, and unavailable for p004. Correlations
cannot establish causal coupling. Raw counts, availability, both windows and all
retained context/history/continuity readings are published, not just these means.

## Evidence and replay

* [Development turn-by-turn matrix](development/matrix.md),
  [CSV](development/matrix.csv), and
  [retained V2 readings](development/retained_v2_matrix.md).
* [Prospective turn-by-turn matrix](prospective_analysis/matrix.md),
  [CSV](prospective_analysis/matrix.csv), and
  [retained V2 readings](prospective_analysis/retained_v2_matrix.md).
* [Frozen formulas](formulas.json), [freeze hashes](freeze.json),
  [construction](construction.json), [Quinn-only transcript](continuation/quinn_only.md),
  [recording receipt](recording_receipt.json), and
  [storage incident](storage_incident.json).

Each analysis directory retains compressed detailed readings with exact signatures
and quote spans, source hashes, summaries, and source-separated V2 readings. The
CSV includes arc identity, age, pivot, conditions and all scalar candidates. The
retained matrices separately expose context/history distribution statistics and
continuity. All actual prospective arcs persist; reset behavior is covered by the
explicit pivot control and tests.

Replay from repository root, without credentials or inference:

```sh
PYTHONPATH=src:. python -m tools.report_movement_meters \
  --records docs/experiments/meter_closure/continuation/records.json.gz \
  --manifest docs/experiments/meter_closure/continuation/condition_manifest.json \
  --review docs/experiments/meter_closure/quinn_review.json \
  --output /tmp/mneme-meter-closure-replay
```

## Meter dispositions

KEEP here means an honest passive quantity, not approval to control generation.
The experimental report preserves rejected candidate readings so their failures
remain inspectable; they are not installed as a runtime policy.

| Meter or proposed interpretation | Disposition | Boundary |
|---|---|---|
| Accepted arc age and explicit pivot | KEEP | Duration under the existing supplied arc contract; cannot identify stagnation. |
| Context activation total, positive coverage, concentration | KEEP separately | Lexical activation of the existing graph, not complete task relevance. |
| Earned distribution entropy/effective count/top mass/HHI and candidate ranks | KEEP | Describes accessible developmental preference within a candidate universe. |
| Context-conditioned distribution distance/rank reshaping | KEEP | Same-candidate redistribution; does not establish influence on prose. |
| Source-separated continuity and covered concept/relationship movement | DIAGNOSTIC ONLY | Useful partial evidence; lexical continuity and sparse extraction are not discourse quality. |
| Response tokens/words, finish reason/caps | KEEP as side measurements | Length is not effort, intelligence, progress or motivation. |
| Literal quantity signatures, counts and changed-signature lists with spans | KEEP | Inspectable numeric text changes; unknown referents and observation status. |
| Quantity novelty fraction/rate | DIAGNOSTIC ONLY | Repeated numbers can describe new evidence; a new number can be irrelevant or hypothetical. |
| State-marker context novelty as environmental progression | DROP | Static paraphrases produce near-maximal novelty; no negation-scope resolution. |
| Content novelty and phrase/surface recurrence | DIAGNOSTIC ONLY | Helps locate repetition, but paraphrase, correct resolution and verbosity confound it. |
| Exact same-turn/lagged quantity/content uptake | DIAGNOSTIC ONLY | Copying is measurable; correct interpretation and response to evidence are not. |
| Paired movement coordinates and descriptive correlations | DIAGNOSTIC ONLY | Expose coexistence/mismatch without fitted categories or causal attribution. |
| General semantic model movement, useful progression, causal coupling | UNMEASURABLE WITH CURRENT SIGNALS | Current text features and extraction do not supply reliable proposition equivalence or understanding. |
| One stagnation/exploration/nuance scalar | DROP | It would conceal missing evidence and incompatible meanings. |

## Three-pressure disposition and failure modes

**Contextual focus:** MNEME can measure how strongly and broadly the current text
activates its graph, how concentrated that activation is, supplied arc persistence,
and surface continuity. It cannot infer that remaining local is the right choice.
Magnitude, coverage and concentration should stay separate.

**Historical pull:** MNEME can measure the developed instance's earned eligible
distribution and how context reshapes it. D100/R8 arithmetic and production
CompactStore boundaries remain intact. No new historical campaign was needed.

**Stagnation/exploratory opportunity:** MNEME can expose numeric text changes,
surface framing recurrence and exact uptake separately for environment and model.
It can make a possible mismatch inspectable. It cannot reliably decide whether
new information is useful, a repeated frame is appropriate, or an association
should be broadened. Absence of recognized quantities is unavailable evidence,
not proof of a static environment. Complete relationship coverage is not available.

Likely false signals include a successful repeated confirmation with no new
numbers, a concise correct resolution repeated naturally, paraphrased circling
with fresh vocabulary, a static environment introducing hypothetical numbers,
reused numeric values assigned to different referents, unit/spelled-number
variants, padding, and an answer that copies evidence while reversing its meaning.
The two-pair conversation history can also lose task context independently of
these meters; it was retained unchanged and omissions are recorded.

This closes the meters-only design pass. The remaining semantic uncertainty is
documented, not converted into a scalar. No result authorizes an exploration
schedule, wildcard change or generation threshold. If separately authorized later,
the smallest policy study would start with a frozen offline counterfactual replay
of accessibility odds using this vector and inspectable false-positive cases,
before any live modulation. A future regulator would adjust eligible-association
odds while preserving exploratory possibility, not prescribe a strange analogy.


## Engineering verification

Implementation files are `src/mneme/experiments/movement_meters.py`,
`tools/report_movement_meters.py` and the isolated `tools/run_meter_closure.py`.
Focused coverage is in `tests/test_movement_meters.py` and
`tests/test_meter_closure_runner.py`. Tests cover no I/O/input mutation, deterministic
prefix replay, missing evidence, source separation, arc age/reset, known false
signals, downstream-only labels, unchanged V2 output, exact Quinn gate, acceptance
of Gemma circling, read-only state, expected provider counts, and refusal to repeat
attempted trajectories during infrastructure continuation.

Full pytest passed 716 tests; Ruff passed; strict mypy passed 71 package files
and both new tools. Supplemental tool typing uses `MYPYPATH=src` and
`--follow-imports=silent` to avoid expanding into unmodified historical runners;
standard strict package typing has no such import suppression. Inference-free
report replay reproduced every published meter output byte-for-byte. All 107
historical distribution rows also replayed exactly. Validation and integration
receipts accompany this report. The current main descendant retains the promoted
CompactStore boundary; no historical source, production SAA, learner or persistence
implementation is changed.
