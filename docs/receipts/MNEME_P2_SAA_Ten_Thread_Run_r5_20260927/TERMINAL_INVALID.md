# SAA ten-thread r5 terminal disposition

`INVALID_ASSESSMENT_VALIDATION`

The recovered MSI passed health checks and r5 completed four developmental threads (48 Gemma developmental coordinates). It stopped at `assess-T04-7` because the pinned local DeBERTa assessor returned a semantically invalid row: `candidate:e-194abb5b998ce5ee8bf23578` declared `corresponding_source_slots` for a non-present result.

The raw request, provider result, validation error, accepted conversations, and all ledgers are preserved in this bundle. The failure exposed a bounded runner/publication-handling defect: the live path attempted `plan.publish(None)` after an assessment validation failure, while the publication adapter only accepts resolved tuples. No learner credit was awarded from this failed coordinate, and no Thread 10 or behavioral result was produced.

This is an invalid instrumentation attempt, not a scientific SAA result. Historical r4 and prior F0/r6/r7 evidence remain unchanged.
