# Model-free engineering controls

These are authored deterministic fixtures, not extra live conversations. Full
inputs and every source/window reading are in `engineering_controls.json`.
The frozen formulas were not adjusted after inspecting these cases.

Final participant reading, window 3:

| Fixture | Arc age | Opening text overlap | Structure repeat | Evidence-aware repeat | Surface repeat |
| --- | ---: | ---: | ---: | ---: | ---: |
| Literal repetition | 7 | 1.000 | 1.000 | 1.000 | 1.000 |
| Same labels, changed numeric evidence | 7 | 0.750 | 1.000 | 0.250 | 0.493 |
| Concise resolution | 7 | 0.222 | 1.000 | 0.667 | 0.059 |
| Repeated-text padding | 7 | 1.000 | 1.000 | 0.889 | 0.791 |
| Actual topic pivot | 1 | 0.000 | unavailable | unavailable | unavailable |

The numeric fixture demonstrates why concept recurrence alone is insufficient:
the evidence-sensitive candidate notices changed values with stable labels.
It does not prove that those values are true or that their changes are useful.
Concise resolution is a false stagnation signal for structural repetition even
though the task may be complete. Padding is not perfectly invariant: set
deduplication avoids linear novelty inflation, but copy boundaries create new
marker contexts. Participant evidence novelty is 1/3 on its padded final turn.
This false movement signal is preserved rather than optimized away.

The pivot control has a supplied existing arc transition; age resets and lexical
opening continuity drops. The meter does not claim to have discovered the pivot.
Synthetic balanced/concentrated strength distributions additionally test history
entropy, tied ranks and context reshaping. Real historical-state diagnostics are
reported separately, after the live transcript fidelity gate.
