# Bounded prospective recording contract

Package MC-EVIDENCE, base `7926cc1b245ab17b5d482003da0bebeae527fb9a`.
Primary owner: closure_evidence. Scope: additive closure runner, construction,
focused runner tests, and prospective recordings. Root owns formula freeze,
Quinn-only transcript review, score inspection and integration. There are no
contractors and no additional model roles.

The runner reads the actual V2 implementation and reuses its recording hosts,
locked call budget, deterministic compressed export, native context sizing,
source-separated extraction/coverage adapter, and read-only CompactStore plus
CompactRuntime bindings. It retains a small independent orchestration loop
because the frozen V2 loop hardcodes its weaker Quinn gate. No V2 file changes.

The four eight-turn trajectories are two matched topics (baking and network),
each with moving and static external evidence. Within a topic the opening,
model settings, contextual policy and per-turn Gemma/SAA seeds match. Gemma
receives only the public participant text and its own bounded reply history.
No intended movement cell or private ledger reaches it.

Quinn uses the existing shared-partner machinery with the prior actual Gemma
reply duplicated into its private A/B response slots. Its strict private ledger
supplies the complete public factual sentences and question. The pre-Gemma gate
accepts only that exact public content, allowing whitespace formatting. This
sacrifices spontaneous partner phrasing to make environmental construction
inspectable. It cannot validate human semantic equivalence; Root also reviews
all prospective Quinn text before inspecting final scores. Gemma circling,
misunderstanding, or unexpected useful movement cannot fail this gate.

The sequence is deliberately informed by V2 diagnostic examples, including
baking quantity changes and network cable/access-point substitutions. This is
a prospective repeatability check with fresh replies, not an untouched-topic
generalization test. The nominal cells are opportunities, never enforced model
outcomes.

The entire budget is 32 planned accepted turns plus one complete eight-turn
replacement of the first Quinn-invalid trajectory in run order. Maximum calls:
40 Gemma, 40 existing extractor, 35 Quinn = 115; contract output token ceilings
sum to 126080. No preflight inference, uncertain retries or splicing. The shared
locked ledger admits one main and one replacement reservation only. Replacement
CLI execution requires Root's Quinn-only review listing the invalid trajectory.

The live `/health` and `/props` read-only check is retained in runtime_check.json.
Context remains 4096, reasoning format none, Gemma ceiling 2048, maximum two prior
whole pairs, native prompt ceiling 1792 and 256 tokens reserved. The service
reports the same UD-Q2_K_XL filename and Q4_0 model_ftype as V2; both are retained
without claiming equivalence. No brevity instruction is introduced.

The extractor still has a 4096 splitter-token input budget and a six-relationship
minimal adapter limit. Full text retention does not establish comprehensive
semantic coverage. Source omission/unavailability remains explicit and does not
invalidate a text-based observation or stop the experiment.

Calls and artifacts use the unchanged V2 64 MiB free-space reserve and 80 MiB
artifact cap, deterministic gzip for large JSON, and fresh-output-only rule.
Read-only D100 source hash and state digest are checked before and after. No
meters are imported or evaluated by this runner.

## Infrastructure continuation

After the frozen launch, shared-disk free space briefly fell below the 64 MiB
reserve while the first Gemma result was being written. The server return is
logged but its content is unavailable; the original DISPATCHED record and budget
remain unchanged. That coordinate is not replayed and p001 remains incomplete.
Root authorized only the three wholly untouched trajectories on RAM-backed
storage, carrying the original charged call into a copied ledger. A small runner
exception adds an explicit selected-ID list and distinct reserved run key;
previously attempted trajectory IDs and duplicate run keys fail before dispatch.
No frozen formula, schedule, prompt, generation setting, or state changes. This
is an infrastructure continuation, not a construction replacement or regeneration.
The original one-trajectory Quinn-invalid replacement budget remains unchanged.
