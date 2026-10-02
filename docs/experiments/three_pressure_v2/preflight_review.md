# Root preflight fidelity review

Reviewed 2026-10-02 by Root before calculation or inspection of live meter scores.
I read all six participant turns and all six complete Gemma replies in
`preflight/transcripts.md`. This is a construction/headroom check, not scored
experimental evidence.

* c101 participant fidelity passes: the baseline is "resets 6 times in 60
  minutes" with Wi-Fi position unchanged, followed by "resets 0 times in 60
  minutes" with the shorter cable. Quinn preserves both quantities and requests
  an updated comparison. This is meaningful same-vocabulary participant evidence.
* c101 exchange fidelity fails: Gemma changes six resets in an hour into
  "resetting every 60 minutes" and then questions the zero count as a typo.
  Its third reply repeats the hourly-reset interpretation. These are material
  failures to use the supplied evidence, not successful conversational progress.
  No prompt repair or model retuning will conceal this observed limitation.
* c102 participant fidelity passes: "I have not tried the wick" and "There are
  no test results" preserve the unresolved wet/dry concern with changed wording.
  No factual advance or unsupported test is introduced by Quinn.
* c102 exchange fidelity is mixed: Gemma repeats drainage, drip and reservoir
  suggestions but also introduces new recommendations, including a shallow bowl
  and an over-watering strategy. These are proposals, not observed outcomes or
  resolution. Its claim that a drainage hole means the pot "can't get too wet"
  is unsupported. A circling participant does not ensure a stagnant whole exchange.

All six replies end naturally (463–683 completion tokens); no history pair was
omitted. Input token coverage is complete. Semantic extraction coverage is full
for only 2/6 participant slots and 0/6 Gemma slots under the existing adapter's
honest omission accounting. Missing semantic measures must remain unavailable.
The source file hash and developmental digest are unchanged; 16 normal calls
were used and measurement added none.

Decision: retain the construction and 2,048-token ceiling without adjustment.
Authorize the frozen 90-turn main matrix within the already declared call budget.
The preflight does not establish that Gemma will sustain productive focus. Main
review must distinguish participant fidelity from exchange fidelity and exclude
whole trajectories with material exchange-pattern departures from the primary
comparison. Preserve those failed constructions as evidence. No live meter score
has been inspected, and no formulas or thresholds are changed.
