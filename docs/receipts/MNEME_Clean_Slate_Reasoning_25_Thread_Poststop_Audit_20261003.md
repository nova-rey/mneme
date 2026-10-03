# Clean-slate reasoning ON/OFF 25-thread post-stop audit

**Disposition: STOPPED — no replacement developmental run authorized or launched.**

This is a read-only audit of the preserved primary run `mneme-reasoning-25-20261003`, attempt 8. Threads 1–25 were not rerun. The subsequent attempt 9 is preserved as `INVALID_REPLACEMENT_STOPPED_BY_OWNER` and contributes no experience or comparison evidence.

## Executive finding

- **Observed:** the OFF and ON thread-25 CompactStore specimens and their thread-10/thread-25 checkpoints exist outside volatile memory, have stable SHA-256 digests, and pass `CompactStore.verify()` (empty error lists). Their graph, learner, SAA configuration, and storage telemetry are readable.
- **Observed:** the terminal behavioral/readout evidence did not survive the late failure. The primary root contains no developmental transcript, per-coordinate SAA trace, extraction/assessment record, introspection review, call log, frozen readout output, or removal/restoration output.
- **Conclusion:** the developmental specimens are preserved genuine state, but the intended thread-25 behavioral comparison is scientifically incomplete and cannot be completed from the surviving artifacts without new model calls. No such calls were made.
- **Owner boundary:** any future readout-only or replacement developmental call requires explicit owner authorization. This audit does not authorize one.

## Primary specimen inventory

| Artifact | Bytes | SHA-256 | State digest | Verify | Key rows |
|---|---:|---|---|---|---|
| `newborn-ancestor.compact.sqlite3` | 77,824 | `1c12207ec3ed84323ebe774fea1d83e9876b4c154cb811418697e6caa808c03c` | `50e49c1773fcbad9d48630d8bec4407c8af031e1702b847ffa9a88b560f606bf` | `[]` | edges 0, nodes 0, learner 0, revisions 0, telemetry 0 |
| `checkpoints/thread-010-OFF.compact.sqlite3` | 270,336 | `5ea322917f596d9ff29e0f6aee355b16389e144a94601870c75e69e1243d8de4` | `c6eafcec836513ea3cec2253220392680f078e0c4b4e76c2808647a0caacc3e4` | `[]` | edges 48, nodes 53, learner 48, revisions 18, telemetry 10 |
| `checkpoints/thread-010-ON.compact.sqlite3` | 147,456 | `258aa0ec5400bd2622e2b44a6d5151f38703bb4fccc91e9ebe8b218d61025065` | `982aea131b599473584ab0b61d96ac8933cd2c6ce16fa313f21563e1318d8a24` | `[]` | edges 13, nodes 20, learner 13, revisions 7, telemetry 10 |
| `checkpoints/thread-025-OFF.compact.sqlite3` | 491,520 | `006206cc999e8fe7cfde2ef5eab732e352582863069718848006b1fa5367cf1b` | `b4ae234e54430bfc0e02e97a1a3fda11a719ff9874cdececcab10cc428f523ce` | `[]` | edges 96, nodes 119, learner 96, revisions 41, telemetry 25 |
| `checkpoints/thread-025-ON.compact.sqlite3` | 262,144 | `2f94d54f796f2b19390d1e5c13e3a23e283ac89a78129f9fce9c858e00e82b05` | `91f1818d2f6d40a5a1e92151afc185ff208c0e5d161cd4d136bd1988b08762f3` | `[]` | edges 37, nodes 56, learner 37, revisions 20, telemetry 25 |
| `OFF-live.compact.sqlite3` | 491,520 | `ed79d4302fd4d188e918a1f3f140f64eeb0dead47aac4dec29c6dce886bc66a4` | `b4ae234e54430bfc0e02e97a1a3fda11a719ff9874cdececcab10cc428f523ce` | `[]` | edges 96, nodes 119, learner 96, revisions 41, telemetry 25 |
| `ON-live.compact.sqlite3` | 262,144 | `8f8428636e0873322833c90cfce8141a3a3eeb3a1d5ee7f2fab4832d0f53fd83` | `91f1818d2f6d40a5a1e92151afc185ff208c0e5d161cd4d136bd1988b08762f3` | `[]` | edges 37, nodes 56, learner 37, revisions 20, telemetry 25 |

The progress manifest records the original pre-move paths for the checkpoint files. Those paths are stale; the current paths above are the resolved copies. The hashes and state digests still match the preserved files.

### Durable state checks

- OFF-25: 96 graph edges, 119 graph nodes, 96 routes, 96 learner-state rows, 41 graph revisions, 97 learner-journal rows, 25 bounded storage-telemetry rows.
- ON-25: 37 graph edges, 56 graph nodes, 37 routes, 37 learner-state rows, 20 graph revisions, 37 learner-journal rows, 25 bounded storage-telemetry rows.
- `provenance_refs` is empty in both compact databases. The state is readable, but the detailed experimental provenance was not persisted there.
- A fixed-probe read-only SAA reconstruction succeeds for both checkpoints: nonempty distribution, selected landing, nonzero pressure, nonempty payload, and health status `healthy`. This proves current state can drive the deterministic field machinery; it does not recreate the lost historical prompts or model outputs.

## What survived outside volatile memory

**Survived:** newborn ancestor, OFF/ON live databases, thread-10 and thread-25 checkpoint databases, progress/invalid receipts, SHA/state digests, compact graph/learner state, metadata, and per-thread storage telemetry embedded in the stores.

**Did not survive:** accepted participant/Gemma transcripts; shared-Interloper messages; field distributions, landings, neighborhoods, pressures, and payloads for each developmental coordinate; GLiNER extraction and local assessor records; introspection reflections and filings; request/response call metadata and outputs; complete prompt/seed records; frozen readout outputs; removal/restoration outputs; and a terminal comparison report.

The compact `research_telemetry` rows are storage metrics only. They do not contain the conversation or SAA evidence needed to join a response to its developmental cause.

## Why the thread-25 comparison cannot be completed

The intended comparison requires at least one durable matched OFF/ON readout pair with exact probe, ordinary context, generation seed, field seed, SAA trace/payload, and nonempty model outputs. It also requires enough developmental trace to establish how the two states were reached and to interpret any difference. The ON readout failed with `finish_reason=length` and empty final content before the in-memory result bundle was written; the preceding in-memory OFF rows and all developmental arrays were lost with the process. The preserved databases cannot reconstruct them.

Running new readout calls against the untouched checkpoints could create new observations, but those would be a new prospective readout and would not recover the missing historical comparison. No calls from attempt 9 are used or counted after the owner stop; that preserved attempt remains excluded.

Therefore the correct classification is **incomplete/invalid terminal comparison evidence**, not a scientific negative and not a retroactive invalidation of the genuine OFF-25/ON-25 developmental states.

## Lineage identity limitation

The copied live/checkpoint databases retain ancestor metadata (`instance.branch=ANCESTOR`, `reasoning_condition=ANCESTOR`) even though their filenames, state digests, and progress entries distinguish OFF and ON. This is an observed runner provenance defect. It does not alter the graph/learner rows, but it weakens branch identity in the persisted metadata and is another reason the run cannot serve as a clean terminal comparison receipt.

## Preserved invalid attempts

| Attempt | Disposition | Cause | Experience counted |
|---:|---|---|---:|
| 1 | `INVALID_RUNNER_GLINER_PAYLOAD_BOUNDARY` | The new runner passed the resident RemoteGlinerHost minimal relationships payload to parse_gliner_relations, which expects raw relation_extraction. No accepted graph/learner publication occurred. | 0 |
| 2 | `INVALID_RUNNER_NLI_ALIGNMENT` | The new runner's strict observation-to-NLI score alignment raised because the returned score tuple was longer than the candidate observation tuple. The partial branch stores are preserved; no thread-25 interpretation is made. | 0 |
| 3 | `INVALID_ON_INTROSPECTION_EMPTY` | The ON Gemma resident endpoint returned an empty content field during the required introspection filing call. The run passed deterministic OFF/ON duplicate preflight and reached the first developmental coordinate, but no thread was completed and no thread-25 interpretation is made. | 0 |
| 4 | `INVALID_ON_INTROSPECTION_EMPTY_R2` | The reasoning-enabled ON filing response still exhausted the 2048-token allowance on a longer real reflection/target packet and returned empty final content. The run passed deterministic preflight and completed thread 1, but did not complete thread 2 and is not behavioral evidence. | 0 |
| 5 | `INVALID_OPERATOR_STOP_DURING_ON_FILING` | The run was stopped after increasing the ON server to 8192 context and 4096 output allowance revealed that a real ON filing call can spend several minutes in native reasoning. No thread-25 interpretation is made and no developmental experience is counted. | 0 |
| 6 | `INVALID_ON_FILING_LENGTH_4096` | With ON context 8192 and max_tokens 4096, a real filing response consumed all 4096 completion tokens (finish_reason=length; reasoning_bytes=14472) before emitting final content. The run completed thread 1 only and is not behavioral evidence. | 0 |
| 7 | `INVALID_THREAD10_CHECKPOINT_DISK_FULL` | Development completed through thread 10, but CompactStore's atomic checkpoint free-space guard refused the required checkpoint because the local /home/nyx filesystem had only about 4 MB free. No thread-25 interpretation is made; this attempt is not scientific evidence. | 0 |
| 8 | `INVALID_READOUT_EMPTY_ARTIFACT_LOSS` | All 25 developmental threads completed and thread-25 checkpoints were created, but the ON frozen readout used a 256-token reasoning allowance and returned finish_reason=length with empty final content. The runner also had not yet durably streamed in-memory transcript/call evidence before this late failure, so no terminal comparison report is claimed. | 0 |
| 9 | `INVALID_REPLACEMENT_STOPPED_BY_OWNER` | Replacement launch was stopped immediately on owner instruction. It is not a replacement scientific run and contributes no developmental experience or comparison evidence. | 0 |

All nine attempts remain separate. Attempt 8 is the only preserved root containing completed thread-25 state. Attempt 9 was stopped by owner instruction and is excluded.

## Prospective evidence-persistence correction

The isolated runner now writes `development-evidence.json` atomically at every completed thread. Each record contains the transcripts, field traces, extraction/assessment records, introspection reviews, storage metrics, and call records accumulated through that boundary. A temporary file is replaced only after serialization succeeds, so a later readout failure cannot erase completed developmental evidence. Readout requests also use the host envelope and retain finish/usage/reasoning diagnostics when content is empty.

This correction is prospective only. It was not applied retroactively to attempt 8, and it has not been used to launch a replacement run.

## Final stop condition

No developmental threads were rerun. No replacement run was launched after the stop. The preserved OFF-25 and ON-25 specimens remain untouched and available for a later owner-authorized readout or continuation decision. This audit stops here.

Machine-readable companion: `MNEME_Clean_Slate_Reasoning_25_Thread_Poststop_Audit_20261003.json`.
