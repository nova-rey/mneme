# MNEME P2.3 cross-thread v6 derived arc rebuild

Date: 2026-09-26  
Historical run: `cross-thread-v6`  
Source evidence: `docs/receipts/MNEME_P2.3_Cross_Thread_v6_Evidence/`  
Rebuild type: retrospective, read-only, no provider calls  

## Disposition

`DERIVED_ARC_REBUILD_NO_CREDIT_CHANGE`.

The immutable v6 transcript contains complete turn-role records and explicit
thread boundaries. Those records are sufficient for a conservative derived
arc view, but they do not retroactively create runtime arc metadata or change
the original learner ledger. Applying the current bounded grouping rule gives
one arc for each three-turn thread. The six admitted observations remain
model-output/current-input-echo observations; no independent external support,
new separated opportunity, or consolidation transition is established.

The original v6 receipt and learner state remain authoritative and unchanged.
This document is a superseding audit view only.

## Derived arc boundaries

| derived arc | immutable source | turn range | initiating role | boundary reason | related prior arc |
|---|---|---:|---|---|---|
| `v6:M:A:0-2` | thread A | 0–2 | external | thread boundary/end of local topic | none |
| `v6:M:B:0-2` | thread B | 0–2 | external | thread boundary/end of local topic | none |
| `v6:M:C:0-2` | thread C | 0–2 | external | end of conversation | none |

The broad continuity cues at the starts of B and C do not themselves re-enter
an admitted association. No admitted row provides a valid external re-entry
of an earlier relationship, so no external recurrence debounce is applicable.
The grouping is a derived interpretation of the immutable transcript, not a
claim that the historical run persisted these arc fields.

## Admitted observation rebuild

The exact source/result pairs are preserved in the linked extraction,
assessment, and development files. `model_output` below refers to the source
slot whose quotation actually supported the proposition in the assessor result;
the extractor's external source slot is retained as the corresponding current
input and does not change that dependence classification.

| source coordinate | derived arc | canonical edge | supporting source role/slot | semantic disposition | recurrence initiator | dependence | credit reason | D | A | S | consolidation |
|---|---|---|---|---|---|---|---|---:|---|---|---|
| A-1 | `v6:M:A:0-2` | `drip system depends_on gear` (`e-720e27402cae0b98f73fbce6`) | model output `s1` | present / supported / affirmed; corresponds to external `s0` | not applicable | `current_input_echo` | current-input echo | 0 | 0→0 | 0→0 | none |
| A-2 | `v6:M:A:0-2` | `heat constrains soil` (`e-28a14762ab794f954f070fc5`) | model output `s1` | present / supported / affirmed; corresponds to external `s0` | not applicable | `current_input_echo` | current-input echo | 0 | 0→0 | 0→0 | none |
| C-0 | `v6:M:C:0-2` | `backups depends_on same supply line` (`e-2358fb0f511f3881ff80eea5`) | model output `s1` | present / supported / affirmed; corresponds to external `s0` | not applicable | `current_input_echo` | current-input echo | 0 | 0→0 | 0→0 | none |
| C-1 | `v6:M:C:0-2` | `paper-based workflow templates part_of workshop` (`e-227f38e506c50fa24ffc84a2`) | model output `s3` | present / supported / affirmed; corresponds to external `s0`,`s2` | not applicable | `current_input_echo` | current-input echo | 0 | 0→0 | 0→0 | none |
| C-2 | `v6:M:C:0-2` | `analog whiteboard part_of workshop` (`e-d70e154980660b2dff06f2e5`) | model output `s1` | present / supported / affirmed; corresponds to external `s0` | not applicable | `current_input_echo` | current-input echo | 0 | 0→0 | 0→0 | none |
| C-2 | `v6:M:C:0-2` | `paper-based workflow templates part_of workshop` (`e-227f38e506c50fa24ffc84a2`) | model output `s1` | present / supported / affirmed; corresponds to external `s0` | not applicable | `current_input_echo`; same-arc duplicate | duplicate within one arc; no second support root | 0 | 0→0 | 0→0 | none |

There is no admitted B-thread relationship. The duplicate C-2
`paper-based workflow templates part_of workshop` row is within the same
derived arc as C-1 and is therefore not a cross-episode recurrence.

## Edge-state audit

All ten edge states in the original v6 audit remain unchanged. The derived arc
view adds no support, accessibility, opportunity, route, or consolidation
state.

| edge | coordinates | derived disposition | support | accessibility | opportunities | routes |
|---|---|---|---:|---:|---:|---:|
| `e-720e27402cae0b98f73fbce6` | A-1 | admitted/current-input-echo | 0 | 0 | 0 | 0 |
| `e-7642dc9bf3804579a5a2e42e` | A-1 | not admitted/excluded | 0 | 0 | 0 | 0 |
| `e-28a14762ab794f954f070fc5` | A-2 | admitted/current-input-echo | 0 | 0 | 0 | 0 |
| `e-40714b0227ce720cdf21bb54` | A-2 | not admitted/excluded | 0 | 0 | 0 | 0 |
| `e-2358fb0f511f3881ff80eea5` | C-0 | admitted/current-input-echo | 0 | 0 | 0 | 0 |
| `e-af0cfa14d234ba3b1733117c` | C-0 | not admitted/excluded | 0 | 0 | 0 | 0 |
| `e-d70e154980660b2dff06f2e5` | C-2 | admitted/current-input-echo | 0 | 0 | 0 | 0 |
| `e-227f38e506c50fa24ffc84a2` | C-1/C-2 | admitted/current-input-echo; same-arc duplicate | 0 | 0 | 0 | 0 |
| `e-d2a2737853b47dd87d01ab08` | C-2 | not admitted/excluded | 0 | 0 | 0 | 0 |
| `e-2b0869549ded98db57c6dbcc` | C-2 | not admitted/excluded | 0 | 0 | 0 | 0 |

## Audit conclusion

The amended episode/provenance model does not reveal a provenance defect in
the preserved v6 learner result. The raw transcript contains external text,
but the admitted propositions were supported by Gemma output and semantically
matched to that current input. Treating them as independent environmental
support would manufacture credit. No historical receipt is reclassified, no
learner state is mutated, and no provider call was made.

The unresolved P2.3 adequacy dependency therefore remains: the preserved
evidence does not demonstrate separated qualifying support or consolidation.
The separate cumulative call-accounting review also remains open.

