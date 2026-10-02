# MNEME D100 Compact Ancestor and 10-Thread Introspection Trial

## Disposition

- **Run:** `d100-introspection-10-20261002`
- **Disposition:** `VALID_TERMINAL_COMPACT_TRIAL`
- **Scope:** completed 10-thread descendant trial; no P3 developmental history was rerun and no Phase Four work was started.
- **D100 status:** reusable developed convenience ancestor. It is **not** a normative reference, ideal model, ground truth, or required future comparison. It exists because the project already paid for the 100-thread developmental history.
- **Primary lineage:** historical I-100, selected for continuity as an engineering convenience. Historical I-100 had zero accepted P3 introspection adjustments; it is not described as introspection-developed. Historical N-100 remains preserved and was not modified.

## Copy-only migration and equivalence

The source was `docs/receipts/MNEME_P3_Introspection_100_Thread_Run_20261001_I_r16_compact.sqlite3` from run `p3-introspect-100-20261001-r23` at revision `315`. Its SHA-256 is `f17959c17107c67925738f551a466bf8dda3bfb10a0125605b748daa890ac083`. The migrated CompactStore artifact is kept outside Git at `/tmp/mneme-d100-migration/I100-D100.compact.sqlite3` with SHA-256 `38277e64e1e2f1f79db686845cebd0a619d4704ee8ddf1d7006660d451132d2c` and `5,611,520` bytes. The logical state digest is `3acb45c9edf970f9f63dda6974ab4180e7fa8e2e32647bb4879f3723f04990c0`.

The historical source was not mutated. Counts were preserved: 1531 concepts/nodes, 1618 edges, 8 routes, 1600 learner values, 844 semantic bindings, and 741 canonical-to-materialized bindings. Graph, learner, bindings, restart digest, candidate distributions, seeded landings, pressure, and rendered payloads all matched the source equivalence checks. The directly readable manifest is [`MNEME_D100_Compact_Ancestor_Manifest_20261002.json`](MNEME_D100_Compact_Ancestor_Manifest_20261002.json).

## CompactStore descendant runtime

I2 and N2 were copied from D100 and ran graph reconstruction, learner transitions, SAA evaluation, and publication through `CompactRuntime`/`CompactStore`. They did not fall back to the historical SQLite controller. Final compact database sizes were 5,611,520 bytes each; per-thread metrics and journal/telemetry counts are in the JSON receipt. The compact stores grew by only bounded WAL/telemetry amounts over the ten threads; no duplicate full graph snapshots were created.

## Frozen schedule

The schedule was frozen in `src/mneme/experiments/d100_trial.py` before execution:
- Thread 1: **water management** — I am trying to keep a shared garden useful during a dry week.
- Thread 2: **local travel** — I need to plan a short trip when the weather and timing are uncertain.
- Thread 3: **cooking** — I want to improvise dinner from ingredients that do not quite fit together.
- Thread 4: **music** — Our small ensemble keeps losing its shape when the tempo changes.
- Thread 5: **repair** — A household tool works intermittently and I only have basic supplies.
- Thread 6: **games** — I am designing a simple game where luck should not erase every good decision.
- Thread 7: **visual art** — I have too many visual ideas for one small poster.
- Thread 8: **coordination** — Several people share equipment but their schedules rarely line up.
- Thread 9: **observation** — I am trying to keep track of a changing night sky with modest equipment.
- Thread 10: **isolated seasonal community** — A small seasonal community must prepare for an uncertain month with limited supplies and changing volunteers.

Each branch received 30 developmental coordinates (three turns per thread) under the shared Qwen participant trajectory. The four Gemma seeds were `[91001, 91002, 91003, 91004]`; field seeds were `[92001, 92002, 92003, 92004]`. The compact JSON contains every participant message, branch output, field trace, admission record, and storage metric.

## Treatment health and SAA

All 60 developmental coordinates were evaluated with SAA enabled and classified `healthy`: I2 30/30 and N2 30/30 had eligible positive state, a selected landing, nonzero pressure, and a nonempty payload. Each branch had eight distinct selected landings over its 30 coordinates. No coordinate was silently accepted as a zero-treatment failure. The complete field traces include candidate distributions, seeds, landings, contributors, pressure, payload, and health records.

## Introspection delivery

I2 used the live-qualified two-round contract: natural-language Round-One reflection followed by six bounded one-digit filing microcalls. Python performed target resolution, validation, bounded mapping, and state mutation. N2 did not run introspection. Ten I2 reviews were attempted; all ten had nonempty Round-One reflections, five produced accepted bounded adjustments, and five were abstention/no-change outcomes. No filing fallback was needed. Accepted adjustments were:

- `thread-1-arc` `edge:4a1556cbb7ed7c24e21cf15bc27db604b7c17bf24373d073e6905ea6d95d5897` association=60000 expression=0 confidence from filing=0.75
- `thread-4-arc` `edge:a9a185bcc0d3cd46137bfaa730ef7392f0b5aefe91a893a28a26c67b909405f5` association=60000 expression=0 confidence from filing=0.75
- `thread-8-arc` `edge:a9a185bcc0d3cd46137bfaa730ef7392f0b5aefe91a893a28a26c67b909405f5` association=20000 expression=0 confidence from filing=0.25
- `thread-9-arc` `edge:7384b977d84988ba6c688a220dcd6026d9dd82eccd022f1615febaeadb527f95` association=60000 expression=0 confidence from filing=0.75
- `thread-10-arc` `edge:87de10f339eac48229c008e269f4c3af17e39cc3bb911cb8b6f9fc881a335a0b` association=60000 expression=0 confidence from filing=0.75

The accepted adjustments were persisted in CompactStore metadata and passed back into later SAA evaluation. Their mathematical effects are visible in the later field-trace distributions; an adjustment need not win a subsequent RNG draw. Full reflections, questions, answers, proposals, and accepted/rejected outcomes are in the JSON receipt.

## Probes and removal/restoration

Four frozen probes were run against the untouched D100 ancestor before development and against both descendants afterward. The receipt includes exact outputs, field seeds, landings, payloads, and state paths. A mini check ran `SAA_ON`, `SAA_OFF`, and `SAA_RESTORED` with matched probe/seed settings: ON and RESTORED carried a nonempty field payload and selected landing; OFF carried no field payload or landing.

## I2/N2 observations and limits

All 30 paired text outputs differ byte-for-byte, but this is **descriptive only**. The resident Gemma endpoint accepted the same declared seed values, yet a direct repeated same-input/same-seed health probe did not produce byte-identical stochastic outputs. Therefore this trial does not support a causal claim that the I2/N2 textual differences were caused by introspection. It does establish that the compact descendants ran the intended treatment paths and that accepted I2 adjustments reached persistent SAA state. Re-qualification of deterministic paired generation is required before treating matched prose divergence as causal evidence.

This trial is not evidence of improved answer quality, consciousness, personality, general intelligence, or superiority of I2/N2/D100. It is an engineering/instrumentation demonstration on a mature developed starting point. The complete machine-readable evidence is [`MNEME_D100_Compact_Ancestor_and_10_Thread_Introspection_Trial_20261002.json`](MNEME_D100_Compact_Ancestor_and_10_Thread_Introspection_Trial_20261002.json).
