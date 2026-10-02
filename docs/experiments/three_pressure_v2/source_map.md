# Current runtime evidence map

Inspected before implementation at `7a74a92cbd0c084d420a7da9444bd1258d660b4c`.
The first pilot at `71c4012` remains unchanged. The current checkout includes
CompactStore promotion and explicit legacy creation gates; this work does not
edit those implementations.

| Surface | Actual information and reuse |
| --- | --- |
| `development/episodes.py` | Existing tracker consumes caller topics, tolerates one tangent, and honors explicit pivots; declared arcs group adjacent supplied topics. Neither measures conversational quality. |
| `experiments/arc_measurements.py` | First-pilot set/field metrics are retained as baselines. V2 only supplies an observed accepted prefix, not future membership. |
| `development/field.py:_activation` | Conservative lexical concept-label matching. Existing `novelty` is graph matching, not conversation progress. |
| `development/field.py:_strength` | Existing earned strength is max(accessibility, support), reduced for negative consequence and floored at zero. |
| `compute_saa_field`, `_saa_distribution` | Eligibility excludes blocked/ineligible edges and requires positive strength; final weights multiply strength by contextual/background terms and accepted accessibility adjustment. No additive pressure percentages. |
| `FieldResult.to_dict()` | Context activations, distribution, components, landing, neighborhood, paths, expression adjustments. Eligible strengths and accessibility adjustments must be captured separately. |
| `development/introspection.py` | Accepted adjustments retain edge/context/deltas/provenance. Their frozen maps can be reported separately without making a new introspection call. |
| `state/persistence.py`, `compact_runtime.py` | CompactStore is the promoted default. `CompactStore(read_only=True)` and `CompactRuntime.graph()/learner()/evaluate_saa()` reuse canonical bindings and SAA without writes. |
| `experiments/shared_interloper.py` | Existing private Quinn concerns, public participant message, own-branch Gemma history. A private factual ledger extends that contract without exposing labels. |
| `memory/residue.py`, `tools/run_p23_cross_thread.py` | One existing GLiNER call can carry separate participant and Gemma source slots, then use the existing pure minimal conversion and validation path. No NLI or new extraction role is needed. |

The canonical normalization path is `convert_minimal_relationship_payload` then
`validate_residue(..., require_evidence_quotes=True)`. Preserve raw specialist
output, exact source slots, conversion decisions and validated spans.

Concept conversion uses `setdefault`: a concept appearing in both source slots
may retain only its first evidence entry. Source-specific concepts therefore also
come from endpoints of validated edges with matching source provenance. Edge IDs
include evidence/source information; recurrence compares existing normalized
endpoint labels and canonical relation type, not local IDs.

There are two independent coverage limits: the resident GLiNER endpoint accepts
`max_len=4096`, and the minimal adapter retains at most six relationship proposals
across both sources. The wrapper's existing metadata does not establish full
token coverage by itself. Do not infer source absence from adapter omissions.
The Gemma wrapper retains usage in raw metadata, even when its top-level token
usage field is null. Its fingerprint's context size requires checking against the
live server; preflight observed 4,096 context tokens.

## Available frozen historical states

| State | Source | Verified runtime view |
| --- | --- | --- |
| D100 | `/tmp/mneme-d100-migration/I100-D100.compact.sqlite3` | 1,531 concepts, 1,613 canonical edges, 54 positive eligible edges |
| R8 | `/home/nyx/mneme/docs/receipts/MNEME_P2_SAA_Ten_Thread_Run_r8_20260927/snapshots/SAA-developed.sqlite3` | 174 concepts, 134 canonical edges, 21 positive eligible edges |

D100 file SHA-256:
`38277e64e1e2f1f79db686845cebd0a619d4704ee8ddf1d7006660d451132d2c`.
R8 file SHA-256:
`122bdf3925ff3c50815bdf51958b34347890b12fd0083830a4df4cba92d2f753`.
They have genuinely different earned histories; R8 positive strengths include
4,000, 5,000, 8,000, 10,000, 20,000 and 80,000.

R8 needs no migration or writable descendant for this diagnostic: open
`SQLiteStore(read_only=True)`, construct the existing `ResponseController` with a
FakeHost, and use `_pin()`, `_field_graph()`, `_learner_state()` and `prepare()` in
observe mode. Never execute generation. Compare distributions within each
state's actual eligible universe using identical recorded inputs and field seeds.

Existing compact I2 and N2 descendants share D100's core state digest
`3acb45c9edf970f9f63dda6974ab4180e7fa8e2e32647bb4879f3723f04990c0`.
I2 has four accepted adjustment entries, but those files are not distinct earned
histories. Some historical filenames containing `compact` actually have the
legacy research schema; schema inspection takes precedence over names.

These findings are current source/read-only artifact evidence, not a reinterpretation
of historical experimental results. No historical writes or generation occurred
during this inspection.

## Arc and turn contract used here

The live runner supplies a constant broad domain topic to
`declared_conversation_arcs` over the accepted prefix. The current arc identity
comes from that existing declaration, not from a new semantic detector. Ordinals
and accepted-turn IDs are recorded separately from authored schedule positions;
rejected Quinn messages do not become accepted turns. `start_ordinal`, membership
and current ordinal are available, but the cheapest stable age here is the count
of observed accepted members of the current arc. Ordinal subtraction is unsafe
when ordinals have gaps. Reset occurs only when the existing arc identity changes.

This construction holds broad topic membership constant deliberately. Its absence
of live arc pivots is an experimental control, not evidence that MNEME detected
all conversations as one semantic arc. The offline pivot control tests reset and
continuity independently. Existing developmental runners can instead supply
chapter/topic labels; such labels describe their caller's grouping and must not
be mistaken for learned stagnation or for an independent quality assessment.

## Signal availability without additional inference

| Signal | Direct or derived | Availability and limit |
| --- | --- | --- |
| Arc ID, accepted ordinal, member IDs | Existing tracker output | Before next response; accepted-prefix age only if recording starts mid-arc |
| Exact participant text, recent messages | Existing conversation input | Before response; lexical continuity is not synonym-aware |
| Gemma text and finish/usage | Existing generation result | After response; a capped result is incomplete |
| Concept labels, relationship kinds and source spans | Existing extraction result | After extraction; absent/partial coverage is unavailable, not zero movement |
| New-set fractions, Jaccard, saturation, new structure per word | Pure derivation from covered source sets | Depends on every required rolling input; normalized labels and relation aliases reuse runtime rules |
| Quantities and generic conditional/negation/outcome fragments | Pure derivation from validated evidence quotes | Post-extraction; does not establish factual truth, entailment or useful progress |
| Word shingles and character grams | Pure derivation from exact text | Available without extraction; sensitive to phrasing and boilerplate |
| Positive activation mass, coverage and concentration | Existing field activations plus arithmetic | Pre-response; lexical stored-vocabulary fit, not task relevance |
| Earned strengths and eligibility | Existing canonical graph/learner and `_strength` | Pre-response; frozen history is expected to yield a constant baseline |
| Distribution entropy, effective count, top mass, TV/rank change | Existing eligible strengths and final SAA weights | Pre-response; no causal attribution to output and no additive pressure percentages |
| Winner, route and neighborhood reuse/overlap | Existing field trace across turns | Pre-response; lottery variation and graph sparsity confound interpretation |
| Distant eligible losers | Existing candidate identities/weights and contextual contribution | Eligibility and nonselection observable; no independent semantic-distance oracle |
| Actual problem resolution, equivalent paraphrases, helpfulness | Not supplied by these records | Requires human review or additional inference; neither is a new runtime meter here |

The frozen formulas explicitly retain each meter's timing and missing-value rule.
No computed signal is fed back into generation, selection, extraction or learning.
R8 is an isolated historical read-only research fixture; it is not a developmental
default or a bypass around the promoted CompactStore creation guardrails.

Here `semantic_coverage=true` means the recorded transport/parser/converter path
has no known omissions for that source, with valid provenance and complete text
input. It does not certify extractor recall or semantic completeness. Conversely,
a known omitted proposal invalidates a required source window conservatively;
the retained partial observations remain available in raw evidence for inspection.
The old pilot and its historical runner are frozen research artifacts. The active
V2 recording path uses promoted read-only CompactStore throughout and never
restores legacy SQLiteStore as a developmental default.
