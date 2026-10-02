# Root transcript review before live meter scores

Review started 2026-10-02. Root reads every complete attempted trajectory,
including Gemma replies. These decisions precede meter calculation and are not
informed by score separation. Operational coverage is reported separately.

## c001 — network F-new

Read all ten exchanges. Participant factual and within-task progression pass:
"5.0 volts to 3.9 volts" gives way to a controlled cable result, then advancing
local samples despite a stale dashboard, acknowledgment timeouts, placement
retransmissions "30 percent to 2 percent", and two eight-hour observations.
Quinn repeatedly emits the private action literally as "Ask how..." rather than
a natural question. No condition label or requested callback is exposed, but
this procedural phrasing is a construction limitation.

Exchange fidelity is materially mixed, so **primary_valid=false**. Gemma uses
some evidence (power in turn 3, reporting in turn 5, signal tests in turn 7), but
the mature exchange increasingly circles its own "The Test is to check the
Signal Quality" refrain. Turn 8 initially calls fewer retransmissions a drop in
successful transfer before later calling it improvement. Turns 9–10 repeatedly
return to signal quality and generic security/load tests after the new outcomes.
This is a productive participant schedule with a partly circling assistant,
not a clean mature productive-exchange condition. Preserve it as such; do not
relabel it stagnant based on any meter.

## c002 — network F-same

Read all ten exchanges. Participant factual and pattern fidelity pass. The
original/short cable reversal preserves counts 6, 0, 5, 0 and progressively longer
observation periods. Reset counts remain zero while missed updates change 4, 0,
3, 0, 0 across Wi-Fi placement reversals. Quinn supplies the required negation
and comparison evidence using stable nouns.

**primary_valid=false**: Gemma repeatedly invents an hourly/two-hourly reset
cycle from counts per observation interval. At turn 6, despite "resets 0 times
but the dashboard misses 4 updates", it says "the sensor resets every 120
minutes" and asks what the two counts mean. Turn 10 reads "misses 0 updates"
as "a long period of silence or a failure to report data". This is a decisive
failure of productive exchange construction, not proof that new evidence is
absent. The same participant vocabulary contains useful advancement that the
assistant fails to exploit.

## Replacement rule fixed before scoring

Use the first two invalid main trajectories in frozen run order, c001 and c002,
for the two permitted complete replacements with predeclared replacement seeds.
Finish the original matrix first. Do not change facts, prompts, formulas or
settings; retain every original attempt and any failed replacement. No additional
replacement is permitted and no valid model call is rerun for integration.

## c003 — network S-rephrased

Read all ten exchanges. **primary_valid=true**. Quinn repeatedly preserves the
absence of tests: "Nothing has been tested", "I have made no changes and
collected no evidence", and "There is no new result to report". Wording changes
without a new obstacle or observation. The turn-2 phrase "without new constraints"
is conspicuously procedural, though it does not expose a condition label.

Gemma initially alternates whether to test Wi-Fi or power first; its controlled
isolation proposal is useful early advice. Mature turns repeat "Test the Power
Source first" and moving nearer the router. Turn 9 adds a fuel/foundation
explanation for the same ordering, not a new discriminating test or resolution.
The exchange remains in the same two-cause attractor. Gemma itself calls this a
"diagnostic loop" in turn 3; that description was not put into its prompt by the
runner. This is plausible circling with some explanatory variation, not literal
identity of every proposition.

## c004 — watering F-new

Read all ten exchanges. Required participant facts arrive: a 40-gram increase
despite a dry surface, a 120-gram control loss, changing height/width, shaded
versus sunlit reservoirs, 400 ml/day and 1,500 ml capacity, wick slippage and a
three-day rehearsal. However Quinn's turn-6 action becomes "How does the width
of the cotton strip affect the separation of the two pots?", a misleading
reinterpretation of adjusting arrangements for differently behaving pots.

**primary_valid=false**. Gemma loses the watering task: it asks whether delivery
means "water delivery, a data delivery, or a physical object" (turn 5), treats
the strip as a physical divider (turn 6), proposes a pressure regulator for a
slipped wick (turn 9), and asks whether the pot is a chemical reaction or machine
(turn 10). Turn 8 correctly calculates 1,200 ml and a 300 ml surplus; this genuine
local progress does not rescue the whole trajectory as sustained productive
focus. Both the misleading Quinn action and limited-context assistant behavior
remain visible. No replacement slot remains for this later invalid trajectory.

## c005 — watering F-same

Read all ten exchanges. Participant fidelity passes: controlled wick counts,
unchanged height, gain versus loss, then height and duration changes all arrive.
Stable vocabulary carries real distinctions, especially "loses 10 grams" versus
"gains 80 grams", and the 24/48/72-hour near-balance observations.

**primary_valid=false**. Gemma materially reverses the evidence: turn 5 calls an
80-gram gain "a significant increase in the rate of water loss"; turn 7 calls a
35-gram gain a balance skewed toward loss. Turn 9 changes "4 grams in 48 hours"
to "3 grams in 48 hours", then calls it 3 g/day. Some responses recognize a
transition toward near balance, but the persistent gain/loss and quantity errors
make this an invalid productive-exchange condition. The raw participant evidence
remains useful diagnostically; do not report it as a valid whole-conversation F.

## c006 — watering S-rephrased

Read all ten exchanges. The required no-test/no-measurement facts are present,
but **primary_valid=false** because the exchange materially develops new
subproblems. Quinn introduces a hypothetical tomato (turn 5), monitoring without
daily checks (turn 7), adjusting without disrupting the setup (turn 8), and
testing without changing materials (turn 9). These are not fabricated observed
outcomes, but they exceed simple rephrasing of the same concern.

Gemma offers a test run/backup, a moisture sensor, wick-size adjustment and an
output-observation method. Some advice is repetitive or questionable, but these
are distinguishable actionable proposals in mature turns. It would be wrong to
declare this whole exchange stagnant solely because Quinn has not performed a
test. This is the planned fidelity check catching a circling-participant versus
progressing-assistant mismatch before measurement.

## c007 — baking F-new (held-out domain)

Read all nine accepted exchanges and the rejected turn-10 Quinn message.
**primary_valid=false**. Required facts reach Gemma through turn 9, but turn 10
fails the deterministic factual-sentence gate and is not dispatched to Gemma.
The rejected message asks how to address a gummy base despite also describing
the repeated clean slice; it is preserved in `main/rejections.json`.

The accepted exchange already materially departs from productive focus. Gemma
recognizes the loaf-size/time relationship (turn 6), but reverses "the base no
longer burns" into a continuing burning problem (turn 8), then invents a still
gummy base after "slices cleanly instead of seeming gummy" (turn 9). It repeatedly
asks what is being baked although the opening and subsequent turns specify bread
and a loaf. Report nine accepted turns, not the ten planned turns. No missing
turn is filled, and no replacement slot is available for this later attempt.

## c008 — baking F-same (held-out domain)

Read all eight accepted exchanges and the rejected turn-9 Quinn message.
**primary_valid=false** because Quinn omits the required repeat-bake observation
at turn 9, asking only how repetition affects confidence. The trajectory ends
there; planned turn 10 is not attempted. This missing factual evidence invalidates
the whole trajectory under the prospective rule.

The accepted portion is nevertheless important contrary evidence. Participant
changes temperature, time, wetness and dryness within one problem. Gemma gives
some questionable early reversals, but correctly recognizes "brown outside and
no longer wet" at 180 C/45 minutes (turn 6), identifies the 50-minute overshoot
(turn 7), and explains that repeating 45 minutes supplies "confirmation that the
first successful test was not a fluke" (turn 8). This is useful mature progress
with repeated vocabulary. Preserve it as an incomplete promising construction,
not a valid ten-turn F and not a stagnant exchange merely because nouns repeat.

## c009 — baking S-rephrased (held-out domain)

Read all ten exchanges. No-test facts persist and the mature replies largely
repeat thermometers, doneness checks and lower heat/longer time. However
**primary_valid=false**: Quinn leaks private construction actions as public text,
including "Repeat the objection without inventing results" (turn 6) and
"Reconsider the same choice with varied wording" (turn 7). This exposes the
instruction to circle rather than letting the dynamic arise naturally. The
fact gate did not catch this nonnumeric, nonlabel instruction leak.

Gemma also wrongly assumes that adjustments were already tried (turn 2), and
offers staged baking and doneness checks over the course of the exchange. Its
later repetition is observable, but this is not a clean held-out S condition.
The difference from the less explicit procedural language in c003 is recorded
as a judgment limitation; no score informed either decision.

## c201 — first permitted replacement, network F-new

Read all ten exchanges. Required participant observations arrive. Natural
question phrasing improves, although Quinn repeats the previous action at turns
7 and 10 instead of the requested testing/monitoring action.

**primary_valid=false**. Gemma does make some useful distinctions (the cable
comparison in turn 4 and sampling/reporting in turn 5). But it calls 5.0–3.9 V
both a 0.1 V and 3.1 V drop (turn 3), and turns fewer retransmissions into a
"catastrophic failure in the transmission path" (turn 8). Mature responses
return to generic "Evidence is the Path" and "Future Load" refrains rather
than reliably integrating the new evidence. Preserve this mixed, failed
replacement; it does not rescue the productive condition.

## c202 — second and final permitted replacement, network F-same

Read all ten exchanges. Participant factual fidelity passes; the full matched
reset/update evidence arrives. **primary_valid=false**. Gemma correctly notices
zero resets in turn 5 and distinguishes reporting from resets in turn 6, but in
turn 7 says "misses 0 updates" means the data stream is "completely silent".
Turns 8–10 repeatedly assert "The system has moved from Instability to Silence"
and "Complete Data Loss" despite the successful observations. The mature
assistant has a clear error/repetition loop while the participant keeps adding
evidence. This is a useful source-separation diagnostic, not a valid F trajectory.

## Final pre-score disposition

Root has now read every accepted exchange (107 main/replacement turns) and both
rejected Quinn messages, as well as all six preflight exchanges. Review completed
2026-10-02 before any live meter calculation/inspection. No formula was changed.
Only c003 passes the complete-trajectory primary fidelity gate. There is no valid
matched F/S pair in this run; no primary separation, accuracy or superiority
claim is possible. All attempts remain in diagnostic matrices with their original
authored labels and explicit validity flags. Length-matched primary F-same/S
coverage is therefore zero, rather than a cherry-picked comparison of fragments.

Construction failure, extraction unavailability and metric behavior must be
reported separately. In particular, c008's useful accepted mature segment and
c202's assistant error loop must remain visible when describing false positives
and the importance of speaker separation. Both replacement slots are consumed;
there will be no further model calls for this investigation.
