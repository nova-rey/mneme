# SAA ten-thread run r6 — invalid terminal receipt

- Run: `p23-saa-ten-thread-20260927-r6`
- Disposition: `INVALID_ZERO_FIELD_PRESSURE`
- Historical evidence: preserved; no prior run was modified.
- Calls: 378 returned, 0 failed, 0 uncertain.
- Development gate: passed with 13 nonzero learned edges/neighborhoods.
- Execution reached Thread 10 readouts, held-out probes, and the bounded removal/restoration check.

The run is not a behavioral result. The runner's field-validity guard required every developmental field trace to have nonzero pressure. The first seven traces are legitimate cold-start coordinates before eligible developmental state existed; subsequent SAA readouts and removal/restoration `SAA_ON`/`SAA_RESTORED` traces had nonzero pressure. The `SAA_OFF` removal condition intentionally has no field. The guard was therefore over-broad. This receipt preserves the complete raw requests, responses, transcripts, traces, ledgers, and terminal report unchanged.
