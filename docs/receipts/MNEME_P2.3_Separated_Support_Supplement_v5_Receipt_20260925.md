# MNEME P2.3 separated-support supplemental run v5 receipt

## Disposition

**Terminal result: NOT_DEMONSTRATED.** This was one new prospective trajectory after the role-perspective and empty-Interloper correction. It completed without an empty participant output, but no qualifying canonical association accumulated separated support and no consolidation transition occurred. The existing P2.3 `COMPLETED_INADEQUATE` disposition remains unchanged.

## Frozen execution

- run: `p23-adequacy-balcony-v5-20260925`
- experiment: `p2.3-separated-support-adequacy-20260925`
- Interloper policy/contract: revision 3 / contract revision 3
- extraction: `relationships-v1`
- turns: 12
- accepted developmental episodes: 12
- trustworthy interpretations: 12/12
- environment failures: 0; recovery attempts: 0
- consolidation transitions: 0
- historical P2.3 evidence: preserved

## Call accounting

| role | returned calls | total tokens | finish reasons |
|---|---:|---:|---|
| development | 12 | 15496 | length: 8, stop: 4 |
| extraction | 12 | 13014 | stop: 12 |
| partner | 12 | 23412 | stop: 12 |
| **total** | **36** | **51922** | provider usage recorded where supplied |

The two language-model roles were DeepInfra hosted models: Qwen for the Interloper and Gemma for development. The relationships-v1 extraction path returned the bounded empty relationship object for each episode; its FakeHost/test-path usage is therefore not treated as a hosted-model token claim. No credential or authorization metadata is included here.

## Role-perspective audit

The run was dispatched after commit `7a65b933c6579dbd3a274f902d9539c58f08fcbf`, which uses explicit perspective renderers. Gemma receives Interloper text as `user` and its own prior output as `assistant`; Qwen receives Gemma text as `user` and its own prior Interloper text as `assistant`, with the newest Gemma response appended once as the final user message. Offline exact-message-array tests and CI passed before this run. Historical role-malformed runs remain unchanged.

## Scientific interpretation

The run provides a functioning, perspective-correct, non-empty conversational trajectory with complete interpretation coverage. It did not demonstrate the narrow separated-support/consolidation adequacy objective. No further trajectory was sampled. The result is negative/inconclusive at the small-sample scope; it does not claim absence of developmental consolidation generally.

Readable exact transcript: [`docs/experiments/contingent-conversation/P2.3_Separated_Support_Supplement_v5_Transcript_20260925.md`](../experiments/contingent-conversation/P2.3_Separated_Support_Supplement_v5_Transcript_20260925.md). Private authoritative run artifacts remain in `/tmp/mneme-p23-adequacy-20260925-v5` and are not committed.
