# MNEME P3 post-run diagnostic audit

**Disposition:** read-only audit of preserved `p3-introspect-100-20261001-r23` evidence. No runtime, database, receipt, result, or experiment was changed; no conversations or readouts were rerun.

## Executive findings

- **Checkpoint 25:** SAA was enabled and the checkpoint contained active concepts and learner state, but every I/N readout had an empty accessibility distribution, no landing ticket, zero pressure, and an empty payload. The direct state audit found a fork/binding mismatch: positive learner keys were canonical, while the current child graph’s local keys were only partially mapped through the child’s own `semantic_bindings`. This is the supported root cause. The renderer and RNG were not reached.
- **Developmental continuity:** persisted field traces show treatment on most accepted coordinates, with legitimate cold-start zeros at Thread 1. T25 has the same binding-related zero pattern; T76 has another boundary zero pattern whose exact cause is unresolved. Seventy-four rows have no separate field trace and are reported as trace gaps, not silently counted as zero treatment.
- **Persistence:** the large stores were dominated by append-only learner history and repeated full graph snapshots. At I-25, 56,093 of 56,534 learner updates were `unchanged`; 115,100 learner-value rows represented 437 distinct edge keys. At I-100, graph tables still held 510,727 concept rows for 1,601 distinct keys and 501,497 edge rows for 1,707 keys. The compacted I/N-75 stores were 165/184 MB; after resuming, I/N reached 440/495 MB by Thread 100.
- **Introspection:** all 100 reviews produced zero accepted adjustments. The first 75 were malformed; raw receipts show natural-language reviews followed by repairs that still used unsupplied target aliases or the wrong proposal shape. Later rows are empty no-change/no-target records; the compact ledger does not preserve enough raw output to prove semantic no-change for every row.
- **Scientific boundary:** P3 does not provide interpretable evidence for an introspection effect. I/N divergence is consistent with SAA-mediated adaptive history, but not with accepted introspection treatment.

## 1. Checkpoint-25 treatment failure

The readable checkpoint artifact contains 24 I and 24 N rows. For all 48: `field_enabled=true`, active concepts were present, `accessibility_distribution=[]`, `selected_landing=null`, `landing_ticket=null`, `total_pressure=0`, and `payload=""`. All 24 I/N paired outputs were identical. V is intentionally field-free.

The read-only SQLite audit found the following:

| lineage | current child graph edges | child binding rows | graph→learner key hits | mapped graph keys with positive learner state | positive learner keys not reachable from graph |
|---|---:|---:|---:|---:|---:|
| I | 441 | 31 | 14 | 0 | 53 |
| N | 509 | 32 | 17 | 0 | 67 |

The current learner state was not empty: I-25 had 56,534 learner values and N-25 had 63,206. The graph snapshots were populated and active concepts existed. The field implementation first filters graph edges through learner strength; with no positive canonical key reachable from the materialized child graph, it returns the empty field result before drawing the RNG ticket. This explains the empty distribution and `landing_ticket=null`. It is therefore not a renderer threshold, not an RNG miss, and not a cold-start readout.

The best-supported implementation explanation is that the forked child’s semantic-binding map did not inherit the parent binding map used to resolve canonical learner keys. That is an inference from the preserved rows plus the current `_learner_key_map` query, which is scoped to the pinned child instance. No correction was made.

## 2. Developmental treatment continuity

Each lineage has 800 developmental coordinates (100 threads × 8 turns). The public field trace contains 1,526 persisted rows and 74 explicit `NO_SEPARATE_FIELD_TRACE_PERSISTED` rows. Among persisted rows, I has 730 nonzero distribution/landing/pressure/payload rows and 32 explicit zero rows; N has 733 and 31. The full per-thread table, including gaps, is in the JSON artifact.

The longest persisted zero streak is eight turns for both lineages at T001, T025, and T076. T001 is the expected cold-start interval. T025 matches the checkpoint binding failure. T076 is a second boundary interval; its precise cause is unresolved from the compact evidence. Missing rows at T075, T087, T089, T095, T096, and T100 are trace gaps, not evidence of zero treatment.

The corrected runner’s field gate checks only SAA readouts, held-out probes, and `SAA_ON`/`SAA_RESTORED` removal rows. It requires `field_enabled` and positive `total_pressure`, while explicitly excluding developmental traces and `SAA_OFF`. That gate can therefore allow many developmental zero coordinates to pass unnoticed and did not flag the checkpoint-25 readout artifact. The earliest useful invariant would have been a per-coordinate post-eligibility field-health check combined with a child graph/binding completeness check; this is a recommendation only.

## 3. Persistence growth

The measured pre-compaction Thread-75 receipt reports I=1,095,016,448 bytes and N=1,230,663,680 bytes. Its dominant physical tables were learner updates (I 498,712,576; N 561,078,272), learner snapshots (I 179,666,944; N 203,358,208), and learner values (I 156,057,600; N 175,058,944). Copy-only compaction produced I=165,036,032 and N=183,562,240 bytes while preserving the current logical state and replay checks recorded in the storage-recovery receipt.

The table-level evidence explains the multiplication:

- `learner_updates` is append-only and stores operation/application identity, opportunity, edge/context, delta, reason, and full `before_json`/`after_json`. At I-25, 56,093 rows were recorded as `unchanged`; this is telemetry/history, not distinct current state.
- `learner_values` records a materialized value per historical update. I-25 contains 115,100 rows over 437 distinct edge keys and one context; it is not one current row per edge.
- `learner_snapshots` repeats full `configuration_json` state snapshots. I-25 has 260 rows; I-50 has 447. Their JSON grows with the graph, which explains the 180–203 MB pre75 contribution.
- Graph publication copied complete immutable concept/edge rows into each snapshot. I-25 has 50,541 concept rows for 510 unique keys and 41,206 edge rows for 444 unique keys. I-100 has 510,727/1,601 and 501,497/1,707 respectively. Routes are also repeated.
- Checkpoint backups, live stores, staging directories, and archives multiply the physical footprint beyond a single database. SQLite page statistics show compact snapshots with 4,096-byte pages and zero freelist pages; the storage-recovery receipt records the later disk-full interruption during removal after compaction.

After compaction, Threads 76–100 added 275,345,408 bytes to I and 311,627,776 bytes to N, about 11.0 and 12.5 MB per thread. This is much smaller than the pre-compaction state but still shows the graph-snapshot and ongoing learner-history growth mechanisms continuing.

### Production persistence requirements suggested by this failure

1. Separate current materialized learner state from append-only research telemetry.
2. Make historical update retention explicit and independently addressable.
3. Avoid full graph row copies for unchanged revisions; use deltas, structural sharing, or revision references.
4. Bound or externalize full learner snapshots; store content-addressed state once.
5. Make checkpoint policy distinguish live state, required scientific checkpoints, and archival evidence.
6. Make disk-capacity checks account for temporary backup/staging peaks before starting a checkpoint.
7. Require row-count/byte-growth telemetry by table and revision.
8. Preserve replay/provenance digests when compacting, without requiring redundant physical copies.

## 4. Introspection treatment failure

The public history contains 100 reviews: 75 `ABSTAINED_MALFORMED`, 4 `ABSTAINED_NO_TARGETS`, 21 `ABSTAINED_NO_CHANGE`, and zero accepted adjustments, accessibility adjustments, or expression adjustments.

The parser requires a JSON object with an `assessments` list. Each item must use an exact packet-supplied `target_alias`, finite association/expression effects, confidence, a valid evidence basis, and supplied evidence references. The acceptor gives `INSUFFICIENT` no credit and rejects abstentions, duplicates, zero-cost proposals, and proposals whose aliases do not resolve.

The first 75 reviews are therefore a treatment failure, not successful abstention. Raw receipts show the model returning long natural-language summaries or direct conversational answers. The formatting repair did run; representative receipts contain a `repair` field. The repair often returned fenced JSON with invented aliases such as `process_vs_destination`, `Robustness`, or `feedback`, and in an earlier repair used `numeric_effect`/`assessment_list` rather than the required fields. The parser consequently reported errors such as `reflection result is not JSON; reflection target alias is not supplied`. In the sampled r11 raw receipts, 50/51 failures reported the unsupplied-alias error and one reported a non-JSON error. These samples support a repeated schema/target-contract failure, while the compact public ledger does not preserve raw output for every one of the 75 rows.

Later rows have no accepted proposals. The four no-target rows are consistent with arcs having no recorded exposure/target; the preserved r23 review `p3-100-arc-00` explicitly has `exposures=[]`, a synthetic `edge_key="none"` target, `raw=null`, and `ABSTAINED_NO_TARGETS`. The 21 no-change rows have empty proposals in the public ledger. Whether each represents a genuine semantic no-change decision or an unrecorded empty/invalid model response is unresolved from the compact evidence. No actionable accepted proposal is directly evidenced.

Because introspection delivered zero accepted state changes, P3 cannot measure introspection’s causal effect. I/N differences must be analyzed as SAA/ordinary adaptive-lineage differences; they cannot be credited to introspection.

## 5. SAA lottery operation

Across accepted developmental evidence, most persisted coordinates show the intended sequence: active concepts, a nonempty history-shaped distribution, a field seed, a selected landing, bounded local contributions, nonzero pressure, and a rendered payload. Epoch summaries are in the JSON artifact. Early (T1–25) has 360 such rows, middle (T26–75) 777, and late (T76–100) 326; missing traces account for 0, 16, and 58 rows respectively, with explicit persisted zero rows making up the balance.

Mean candidate-set sizes rose from 18.3 early to 45.2 middle, then 27.8 late. Unique selected landings were 47, 108, and 56, with top-landing shares 11.1%, 8.4%, and 23.0%. Mean fixed-scale flatness was 0.769, 0.860, and 0.797; mean fixed-scale novelty was 0.195, 0.070, and 0.025. These are descriptive traces, not a clean causal validation of novelty flattening. The selected contribution was explicitly marked `exploration_selected=true` in 1,459 of 1,463 landed rows; four selected rows lacked a matching contribution record. The implementation’s trace does not provide a clean independent contextual-versus-background attribution for every landing.

The lottery became richer in candidate count and landing diversity through the middle of development, while late traces are incomplete and more concentrated. That supports operation of the mechanism, but the evidence is insufficient to claim that familiar contexts reliably peaked and novel contexts reliably flattened the distribution independently of graph growth, boundary failures, and missing late traces.

## 6. I/N divergence without introspection

Three directly readable examples show the same participant input and matched Gemma seed producing different selected SAA landings, abstract payloads, and outputs:

1. T3 turn 0: I landed on a `depends_on` edge and received “Outcomes may depend on the conditions that support them”; N landed on a `part_of` edge and received “A component may matter as part of a larger system.” Their outputs differ in follow-up wording.
2. T5 turn 0: I received a downstream-effects framing while N received a conditions/support framing; the matched responses differ in what they ask the participant to decide first.
3. T6 turn 1: I received a barrier/reduction framing while N received a resource-preservation framing; their otherwise matched cooking responses diverge in emphasis.

These are observed paired differences. The further chain—different output → different extraction/admission → changed graph/learner state → later distribution—is supported at run level by diverging checkpoint graph counts/digests (for example I/N at checkpoint 10: 234/253 edges; checkpoint 25: 441/509) and by later differing landing distributions, but the compact row-level artifacts do not encode a complete causal join for each example. That portion is therefore an inference, not a proven counterfactual.

Checkpoint 25 is an unintended control: once the broken child binding path yielded no field payload to either lineage, matched seeds and identical visible prompts produced identical I/N outputs for all 24 probes, despite their stored graph states already differing.

## Disposition

**Observed:** SAA was active and auditable on most accepted developmental coordinates; checkpoint 25 specifically failed to deliver treatment through a binding/eligibility path; learner/graph persistence multiplied historical material; introspection accepted zero adjustments.

**Inferred:** I/N divergence is consistent with SAA-mediated developmental feedback, not introspection.

**Unresolved:** exact causes for all missing late field traces; whether every no-change review was a genuine semantic no-change; whether the observed descriptive lottery statistics establish the intended novelty law.

This is a diagnostic publication only. No fixes, reruns, Phase Four work, or historical reclassification were performed.

## Evidence

The machine-readable tables and source paths supporting every section are in [`MNEME_P3_Postrun_Diagnostic_Audit_20261001.json`](MNEME_P3_Postrun_Diagnostic_Audit_20261001.json). The report reuses the published readable transcripts, traces, checkpoint summaries, introspection ledger, and the local-only SQLite snapshots; no binary evidence is added.
