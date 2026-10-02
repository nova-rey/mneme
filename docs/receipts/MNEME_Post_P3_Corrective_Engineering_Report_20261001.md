# MNEME post-P3 corrective engineering report

**Date:** 2026-10-01  
**Historical base:** `ff414cd4d4c86ff418a3db16a4fdc79fae2c40d0`  
**Scope:** bounded implementation and targeted validation only. Historical P3 evidence was not rewritten and the 100-thread experiment was not rerun.

## Result

The three requested failure classes now have bounded corrections and focused validation. SAA’s weighted lottery was preserved; its misleading landing provenance was corrected. The persistence correction is an explicit compact mode and has not silently replaced the historical SQLite runtime.

## Introspection

P3 failed because Gemma had to reproduce opaque target aliases. The new `p3-introspection-v2-answer-bank` contract presents short numbered choices; Python resolves the selected ordinal to the canonical association and performs schema, evidence, range, and deduplication checks. Legacy v1 ledgers remain readable. A bounded JSON suffix repair handles mechanically truncated objects without relaxing semantic validation.

The eight-fixture qualification compared four bounded strategies. Alias answer-bank, numbered answer-bank, and fill-in JSON achieved 100% parse/schema/target-resolution and semantic-preservation rates on the offline corpus; the two-stage line format parsed 62.5%. The numbered answer bank was selected because it removes opaque-ID clerical work while keeping one model call and deterministic persistence. Positive, negative, mixed, neutral/abstention, duplicate, and SAA-odds-change fixtures now exercise actual state delivery. Qualification evidence is [the machine-readable receipt](MNEME_Post_P3_Introspection_Qualification_20261001.json).

The archived local-Gemma qualification/smoke artifacts remain separate evidence. This correction does not claim a new developmental study or perfect semantic judgment.

## Persistence

The pathological stores mixed current state with repeated unchanged learner updates, complete materialized graph revisions, learner snapshots, indexes, and full checkpoint copies. `CompactStore` separates current state, graph delta history, bounded learner journal, optional research telemetry, provenance digests, and atomic checkpoints with a free-space guard. Migration is copy-only.

The model-free stress harness completed 10,000, 100,000, and 1,000,000 events. The authoritative learner state stayed at 256 rows; bounded journal rows were 256, 256, and 2,560; checkpoint sizes were 176,128, 176,128, and 737,280 bytes. Every checkpoint digest matched live state, verification passed, and an interrupted transaction recovered the last committed value. A copied P3 r8 subject migrated with 212 concepts, 168 edges, 8 routes, and 165 learner values and passed verification.

The compact mode is available for subsequent migration work; historical databases and existing runtime semantics were not mutated.

## Binding and treatment health

Checkpoint 25 failed because child-only semantic-binding lookup could not resolve inherited canonical learner keys. Binding lookup now walks root-to-child ancestry and applies child-local bindings last, avoiding immutable row duplication. The health classifier distinguishes cold start, disabled/blocked policy, healthy delivery, binding mismatch, empty distribution, missing landing, zero pressure, and empty payload. The historical Thread 76 boundary remains unresolved and was not rewritten; future runs will fail at the first diagnosable stage.

## Lottery semantics

SAA v1 performs one seeded weighted draw over its final accessibility distribution. It does not use the auxiliary exploration-pool selector. The historical `exploration_selected=true` rate (1,459 of 1,463 successful landings) therefore represented unconditional trace labeling, not exploration-pool selection. Traces now identify weighted-distribution versus exploration-pool selection and contextual/background candidate class.

Synthetic checks produced a familiar distribution of e1=0.769231/e2=0.230769 with 1,568 e1 landings in 2,000 draws, versus a novel 0.5/0.5 distribution with 1,017 e1 landings. Same-seed replay and exploration-off distribution stability passed; the algorithm was not retuned.

## Validation and limits

The full suite passed **562 tests**; the focused correction suite passed **63 tests**. Ruff passed through the pinned-on-demand tool invocation, and strict mypy passed via `uvx --from mypy mypy src/mneme`. Wheel build and fresh-install import smoke passed. CI passed on GitHub for the published implementation (`36949414570`, head `d4b1e13`). No model experiment, Phase Four work, persistence redesign of the historical runtime, or historical receipt mutation is included.

Machine-readable counts and hashes are in [the JSON report](MNEME_Post_P3_Corrective_Engineering_Report_20261001.json).
