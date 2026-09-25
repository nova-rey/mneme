# P2.3 separated-support supplement v3 — final audit

- **Run:** `p23-adequacy-balcony-v3-20260925`
- **Contract:** `p2.3-separated-support-adequacy / revision 2`
- **Disposition:** **INVALID**
- **Scientific meaning:** The fixed 12-turn adequacy schedule was not assessable. This is not a negative consolidation result and does not alter the historical P2.3 `COMPLETED_INADEQUATE` disposition.

## Preflight and role boundary

The run was created from the pushed revision-2 contract. The serialized role audit is preserved in [the role-preflight JSON](MNEME_P2.3_Separated_Support_Supplement_v3_Role_Preflight_20260925.json). It asserts:

- Gemma request: Interloper/user → Gemma/assistant;
- Qwen request: Gemma/user → Interloper/assistant;
- Qwen-only private executive state includes the current practical circumstance;
- no research framing is sent to Gemma.

No historical run was regenerated.

## Returned calls and usage

There were **22 returned provider calls**:

| Role | Calls | Input tokens | Output tokens | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| Interloper (Qwen) | 10 | 17,237 | 256 | 17,493 |
| Development response (Gemma) | 6 | 4,228 | 2,221 | 6,449 |
| relationships-v1 extraction (Gemma) | 6 | 5,103 | 30 | 5,133 |
| **Total** | **22** | **26,568** | **2,507** | **29,075** |

Provider cost was not supplied. No assessor, evaluation, or learner calls were dispatched. No retry or resampling occurred after the stop.

## Chronological disposition

- Turns 0–2: three accepted Interloper/Gemma developmental episodes; all three extraction results were valid empty `relationships-v1` residues. No canonical edges were admitted.
- Turn 3: the Interloper result was blank; it was persisted and rejected before history admission.
- Turns 4–6: three more accepted developmental episodes; all three extraction results were valid empty residues. No canonical edges were admitted.
- Turns 7–9: three consecutive blank Interloper results; each was persisted and rejected before history admission.

The predeclared stop rule therefore fired at three consecutive missing participant turns. The schedule stopped before turns 10–11, so the separated-opportunity structure needed to test consolidation was unavailable.

## Learner and consolidation audit

- Accepted developmental episodes: 6
- Valid extractions: 6
- Admitted concepts/relationships: 0
- Assessor calls: 0
- Learner traces: 0
- Consolidation transitions: 0
- Developmental-state writes from evaluation: none (no evaluation was reached)

The absence of learner activity is a consequence of the invalid environment run, not evidence that the live consolidation mechanism cannot occur.

## Evidence

The exact readable conversation is preserved in [the v3 transcript](../experiments/contingent-conversation/P2.3_Separated_Support_Supplement_v3_Transcript_20260925.md). Raw provider requests/results, reservations, extraction records, and the machine-readable runner report remain in the private run artifact at `/tmp/mneme-p23-adequacy-20260925-v3`; their hashes and lifecycle state are recorded by the run manifest. The historical P2.3 pilot, v1 HTTP-429 dispatch, and v2 invalid trajectory remain unchanged.

P2.3 remains **WAITING** on the existing adequacy review. Phase Two is not complete, and no Phase Three work began.
