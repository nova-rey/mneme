# P2 contingent post-correction live stop

**Disposition:** STOPPED — POST-CORRECTION INTERPRETATION TOLERANCE  
**Study:** `contingent-conversation-interloper-20260924`  
**Run:** `contingent-live-20260924`  
**Provider calls in this continuation:** 12  
**Cumulative returned calls:** 77  
**Provider cost:** unavailable

## Coordinate and preservation

The run resumed from the durable review marker at interactive turn 9. Turns
0–8 were reconstructed from their accepted reservations and were not
redispatched. The private schema-8 subject stores were explicitly migrated to
schema 9 before dispatch, with private backups retained under the run's
`migration-backups-20260924/` directory. The first resume command stopped at
that deterministic preflight with zero provider calls; the retry used the same
turn-9 coordinate.

The historical segment remains unchanged:

- accepted interactive turns: 9;
- trustworthy interpretations: 6;
- terminal missing measurements: 3;
- historical success rate: 6/9 (66.7%);
- historical stop reason: `interpretation_success_rate_below_75_percent`.

## Corrected continuation

Turns 9, 10, and 11 each produced an accepted Gemma developmental response.
For each turn, the initial residue call and its one permitted repair were
returned with length-terminated, unparsable JSON. No evidence-reviewer or
assessor call was dispatched for these failed extractions. Each turn therefore
remains `measurement_unknown / interpretation_unavailable`, with no admitted
candidate associations, learner credit, absence inference, or consolidation.

The post-correction segment is recorded separately:

- attempted turns: 3;
- trustworthy interpretations: 0;
- terminal missing measurements: 3;
- extraction failures: 3;
- assessment failures: 0;
- post-correction success rate: 0/3 (0%);
- consecutive post-correction failures: 3;
- stop reason: `three_consecutive_interpretation_failures`.

The full cumulative branch counters are 12 accepted turns, 6 trustworthy
interpretations, and 6 terminal missing measurements. The post-correction
stop is a new instrumentation stop under the reviewed tolerance rule; it does
not reclassify the historical 6/9 result.

## Call accounting

The 12 new returned calls were:

| Role | Calls | Input tokens | Output tokens | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| Interloper | 3 | 6,233 | 545 | 6,778 |
| Development response | 3 | 4,316 | 763 | 5,079 |
| Development extraction | 6 | 12,540 | 6,144 | 18,684 |
| **Total** | **12** | **23,089** | **7,452** | **30,541** |

The continuation used the existing Gemma developing/extraction host and Qwen
interloper host bindings. No open-loop developmental calls, assessments,
evaluation readouts, or new experimental conditions were started.

## Evidence

- Exact readable turns 9–11: [post-correction transcript](MNEME_P2_Contingent_PostCorrection_Transcript_20260924.md).
- Historical turns 0–8: [historical transcript](MNEME_P2_Contingent_Conversation_Transcript_20260924.md).
- Raw private reservations, provider results, and extraction attempts remain
  under `/tmp/mneme-contingent-live-20260924/` and are authoritative.
- The run is durably `PAUSED` at interactive turn 11. P2.3 remains
  `COMPLETED_INADEQUATE`; no Phase Three work began.

