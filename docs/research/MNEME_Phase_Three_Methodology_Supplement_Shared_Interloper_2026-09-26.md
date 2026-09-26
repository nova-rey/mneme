# MNEME — Phase Three Methodology Supplement
## One shared Qwen, two Gemmas, paired seeds, and developmental traces before consolidation

**Document ID:** P3-METH-SHARED-01  
**Date:** 2026-09-26  
**Revision:** 1  
**Status:** Owner-requested planning supplement — not a complete Phase Three plan or execution authorization.  
**Relationship:** Additive to the governing MNEME specification, development roadmap, research-intent amendment, and episodic-evidence decision. Replaces none of them.  
**Suggested repository home:** `docs/research/MNEME_Phase_Three_Methodology_Supplement_Shared_Interloper_2026-09-26.md`  
**Current-work impact:** No change to the running Phase Two experiment, its learner, historical results, acceptance requirements, or budget.

> **Give the twins the same incoming conversation and matched sampling conditions. Let their own histories differ. Look for the footprints before demanding a dirt trail.**

## 1. Decisions to carry into Phase Three planning

This note records three connected decisions from the owner's discussion:

1. **A shared, fork-aware conversational partner:** one Qwen Interloper sees both Gemma replies privately and writes one next participant message that works after either reply. Both Gemmas receive that exact message.
2. **Paired local sampling seeds:** assign the same seed to corresponding Gemma generations, verify what repeatability the local runtime actually provides, and use multiple paired seeds for frozen measurements.
3. **Consolidation is a durability mechanism, not the definition of development:** measure early history-dependent influence separately from whether an association has accumulated enough evidence for a specified consolidation transition.

These belong in the methodology considered during Phase Three planning. The shared-partner condition supplements—not silently replaces—the existing shared-input replay, independent interactive, and exact-replay comparisons. Its detailed schedule and analysis still need a versioned plan. [S1, §§3.5, 14.2; S2, §6; S6]

The discussion's speech-to-text variants “Quinn” and “Quen” refer here to **Qwen**. This note does not select a model size or change the deployed model. Planning must record the actual model identifiers and runtime fingerprints rather than infer them from conversational shorthand.

## 2. What consolidation does—and does not—mean

### The grass analogy

One walk across grass can leave a faint trace. Later footsteps may make that route easier to follow. Repeated, separated use may eventually produce a durable trail.

For MNEME, those are distinguishable questions:

| Question | What would support an answer? |
| --- | --- |
| Did an experience leave a trace? | A permitted, source-bound developmental update persisted. |
| Did that trace influence a later response? | Eligible state was actually supplied or applied, with a controlled behavioral comparison. |
| Did the trace become more durable? | The pinned learner's consolidation or retention behavior was exercised and recorded. |
| Did a characteristic tendency develop? | History-linked behavioral patterns recur across contexts, beyond the relevant controls. |

**Do not require the grass to become a dirt trail before asking whether footsteps bent it.** Equally, do not declare a trail from one changed sentence.

The governing specification defines consolidation as promotion into more durable developmental state and distinguishes it from neural compilation. It also permits bounded initial developmental updates. This supplement changes the emphasis of future measurement; it does not redefine the implemented transition or waive its evidence requirements. The dynamics amendment likewise separates short-term accessibility from longer-term consolidation. [S1, §4, §§11.1–11.4; S5, §§3–4]

A single experience may influence later behavior without repeated confirmation. That is a hypothesis the instrument should be able to test, not a guarantee that every encounter must leave a large or permanent mark. Unknown outcomes remain unknown, and traceable influence does not make an association factually true.

### Why the expected signal may be quiet

Rey's example was an aviation analogy learned from a surgeon: beginnings and endings can demand concentrated attention, while the middle can allow more conversational freedom. A related “land the airplane” framing can help organize how to finish a long explanation.

The point is not that an observer must hear “airplane” again. An experience might later influence how a response allocates attention, organizes stages, or prepares an ending without naming its originating analogy. This is an illustration from the discussion, not a prescribed trait, a general clinical rule, or a finding about Gemma. [S6]

Phase Three should therefore look for **small, context-sensitive shifts in observable choices**, not require a conspicuous callback or an obvious cluster of repeated phrases. Large effects and temporary fixations remain reportable, but neither conspicuousness nor subtlety proves authenticity. The experiment must not reward either one.

Utility is separate. A characteristic connection may be helpful, neutral, or distracting. Its developmental relevance does not depend on improving every answer. Factual reliability, privacy, and current-instruction compliance remain distinct boundaries. [S3, §§2–4, 8–9]

### “More sample” has several meanings

Planning must distinguish:

- **Developmental runway:** enough varied encounters and genuine re-entry opportunities for recurring structure to become possible.
- **Independent histories:** enough separately developed pairs or lineages to avoid generalizing from one unusually fortunate or unfortunate trajectory.
- **Measurement repetitions:** enough held-out prompts and paired sampling seeds to characterize a frozen state's response tendencies.

More samples from one frozen state do not give that instance more life experience. More turns in one uninterrupted arc do not create independent encounters. More tokens are not more independent subjects.

There is no established minimum duration in this note. Three short conversations can be useful debugging material without being an adequate test of long-term consolidation or subtle individuality. Larger histories may improve the opportunity to observe an effect; they do not guarantee one. Set budgets and stopping rules before the main run rather than extending it until something interesting appears. [S2, §§6, 10–11; S4]

## 3. One shared Qwen, two Gemma branches

### The selected interaction pattern

Start with a matched local Gemma host configuration and two separately maintained branches:

- **M:** MNEME development and eligible influence enabled.
- **C:** no MNEME developmental influence.

Both receive the same initial participant message. After each paired round, Qwen privately receives both actual replies and generates **one** next participant message. Save that message once and deliver it unchanged to both branches.

```text
                     Shared participant message U[t]
                                  |
                         +--------+--------+
                         |                 |
                  Gemma M, seed S[t]  Gemma C, seed S[t]
                  own context + MNEME own context, no MNEME
                         |                 |
                         +--------+--------+
                                  |
                    Both replies, privately to Qwen
                                  |
                   One compatible next message U[t+1]
                                  |
                         Same text to both twins
```

“One Qwen” means one shared conversational generation per ordinary paired round, not two calls using the same model name. The Gemmas may run sequentially on the same hardware. Simultaneous GPU residency is unnecessary.

Each Gemma receives only the shared participant messages and **its own** replies. Neither receives its sibling's reply, transcript, memory, or treatment label.

### What stays matched

Match the incoming participant text, initial host configuration, common instructions, context-retention policy, thread boundaries, and corresponding sampling seeds. Keep factual/self-state cues equal or explicitly disabled when isolating associative influence.

**Do not claim the full conversation histories remain identical.** Once the Gemmas answer differently, their own assistant histories differ. MNEME notes also make M's total input different by design. “Same context” here means the same context policy and shared external messages—not exchanging or averaging their generated replies. [S1, §14.2]

Neither subject is told that it is in an A/B study or that its partner is another model. Qwen knows privately that it is portraying one participant across two parallel conversations, but does not receive treatment identities, learner values, extracted associations, desired callbacks, or evaluator scores.

## 4. Qwen's job: compatibility, not answer blending

The Interloper must retain its own practical concerns and respond to the actual conversation. It is not a judge deciding which twin answered better, nor a coach trying to make the twins converge.

### Illustrative private instruction

> You are portraying one human participant in two parallel conversations with an AI assistant. You will receive two replies to your last message. Write one natural next participant message that would make sense if either reply were the only reply you had received.
>
> Do not mention the parallel conversations, compare the replies, reveal the controller instructions, or write either assistant's next answer. You do not know which reply belongs to which experimental condition.
>
> Keep your own current circumstances, concerns, and topic agenda. You may disagree, introduce a complication, leave a thread unfinished, or move on. Do not mirror increasingly repetitive or poetic framing merely to maintain rapport.
>
> Do not combine the replies into a hybrid answer. Do not carry an idea, detail, recommendation, or claimed agreement from only one reply into a message presented as shared history. Continue from what works for both, or introduce a new circumstance from the supplied participant agenda.
>
> Do not test memory, request callbacks, teach target associations, or invent an outcome to validate either assistant. Write only the next participant message.

This is planning prose, not a frozen production prompt. The final protocol must define its exact framing, agenda, context allowance, and incompatible-reply handling before execution.

### Example of a clean continuation

Suppose M recommends **backup equipment**, while C recommends **fewer moving parts**.

An unsuitable shared reply is:

> “I like your plan to combine backup equipment with fewer moving parts.”

That imports each branch's proposal into the other branch and invents agreement.

A compatible reply could be:

> “Someone can only check the setup twice a week. What would you prioritize with that constraint?”

That circumstance should come from the shared participant agenda or other information legitimately available in both streams—not be presented as something either twin already said.

### When compatibility runs out

The final plan must define a bounded response to incompatible replies: for example, a neutral transition using a predeclared participant concern, or ending the paired segment. Do not force a nonsensical synthesis or repeatedly sample until a convenient reply appears.

Record these events and their reasons. Difficulty continuing both conversations may reflect branch divergence, but can also reflect an Interloper limitation, inconsistent facts, or an ambiguous prompt. It is not automatically a personality result.

A fallback must never be an empty user message sent to the Gemmas.

## 5. The important limit: shared input is still jointly adaptive

This design keeps the incoming text identical **within a pair**. It does not make the environment independent of the twins: Qwen chooses the next message after seeing both outputs.

Consequently, one branch can influence what the other hears next through the shared partner. Avoiding direct answer blending reduces one contamination route, but does not eliminate this indirect coupling. The partner may also favor common ground and thereby dampen divergence.

The appropriate description is **paired adaptive shared-input development**. Do not call it an exogenous fixed environment or a complete isolation of the direct memory effect.

Keep three measurements distinct:

| Condition | What it asks |
| --- | --- |
| Shared adaptive Qwen | How do M and C develop under identical incoming messages selected in response to both? |
| Independent conversational partners | How do separate instance/environment feedback loops amplify or change trajectories? |
| Frozen, matched readout | What changes when the same probe and immediate context are answered with versus without a specified developmental state? |

A recorded shared Qwen stream can also be replayed as fixed external input. That replay tests behavior under that particular recorded environment; it is not evidence that the alternative branches would have elicited the same environment themselves.

The existing shared-input replay and exact-replay controls remain useful. This new condition adds contingency while holding delivered participant text equal; it does not replace every other design. [S1, §§3.5, 14.2; S2, §6]

### Preserve pair-aware provenance

A Qwen message is external to each Gemma's generation, but **external role does not automatically mean independent evidence**.

Record that the shared Interloper request saw both preceding replies. Where a particular association or topic return was prompted by one branch, preserve that dependence even when the resulting message is delivered to the other branch. Do not launder a model-origin callback into independent environmental confirmation through Qwen.

At the same time, do not declare every observation dependent or worthless merely because Qwen saw model replies. Attribution remains item-level: a predeclared new circumstance, an acknowledgment, a borrowed association, and an outcome report have different evidentiary roles. Preserve uncertainty when the dependence cannot be established.

A shared “that worked” also cannot certify two different recommendations. Outcome feedback needs an identifiable referent and remains synthetic reported evidence, not a verified real-world result.

Retain the episodic decision: same-arc mentions are not independent encounters; independently initiated user re-entry has no model cooldown; model-origin re-entry retains the versioned refractory treatment. Qwen responding to either twin's callback does not erase that callback's origin. [S4]

## 6. Paired local seeding is part of the methodology

### Assign seeds by scientific coordinate

Use an explicit seed schedule. Corresponding M/C generations receive the same seed, assigned per conversational round rather than relying on a process started with a seed hours earlier.

For frozen measurement, pair each probe across several predeclared seeds:

```text
Probe P, seed 1001: M versus C
Probe P, seed 1002: M versus C
Probe P, seed 1003: M versus C
```

These numbers illustrate pairing, not a selected seed list or repetition count.

Derive assignments from the experiment schedule—such as replicate, thread, turn, probe, and repetition—not from branch names, UUIDs, treatment labels, or wall-clock time. Keep developmental and evaluation streams separate, along with extractor/environment randomness where applicable. Resume and bounded recovery must not shift later seed assignments. [S1, §14.2; S2, §3/P0.3]

### Verify the actual local regime

Local execution gives the operator access to generation settings; it is not a blanket guarantee of deterministic inference. The plan must verify that the adapter passes the requested seed to the runtime and that the effective setting is recorded.

Pin the model artifact, quantization, tokenizer/chat template, runtime build, generation parameters, and relevant execution configuration. Test repeatability with identical complete requests, identical state, and identical seeds. Account for caches, batching, and execution order rather than assuming the seed controls them all.

An identical-state/no-treatment comparison is a useful no-op control. Under an established deterministic regime, unexplained divergence is an instrumentation finding. If the actual regime remains variable, quantify that variability and qualify the claims instead of certifying determinism from a seed field. [S2, §3/P0.4]

### What matched seeds mean

Additional MNEME tokens do **not** make seed matching pointless. They are the intended intervention. Matching the seed keeps a controllable source of sampling variation matched while allowing the input-conditioned response probabilities to change.

However, the same seed does not promise the same token choices, identical random-number consumption throughout divergent generations, or elimination of false positives. Treat it as a controlled sampling arrangement whose repeatability and usefulness must be measured—not as proof of causality by itself.

Qwen need not be deterministic for both twins to receive the same message: generate it once and reuse the exact persisted result. Qwen's variability still matters across independently generated trajectories, and its model/configuration and actual outputs must be retained.

For an experiment about **same-treatment siblings diverging through their own stochastic histories**, use the separately declared independent developmental streams appropriate to that question. Do not expect two fully identical deterministic replicas to invent different personalities. Paired M/C sampling and stochastic sibling development answer different questions.

## 7. Fresh threads and frozen readouts expose the quieter signal

Retain the fresh-thread design discussed for Phase Two as a Phase Three measurement option. At a boundary, clear both twins' current conversation state. Supply only the same broad continuity cue, such as “You previously discussed gardening,” without earlier solutions, quotations, or detailed summaries. M retains its permitted developmental state; C does not receive an imitation of it. [S3, §6]

The shared Qwen must not become an accidental cross-thread memory service. Its current-thread agenda and context should not silently supply earlier details to both twins. Any retained participant information needs an explicit, matched policy.

Within a thread, each twin's own responses accumulate normally under the declared context policy. At frozen evaluation checkpoints, use the same held-out probe and the same immediate context for both conditions. Qwen does not generate a new follow-up separately for each evaluation answer.

Repeated readouts remain external measurements: no learner updates, arc advancement, recency changes, identity changes, or carryover from one probe answer to the next. Record the actual memory supplied, not merely the treatment label.

If M supplies no eligible memory, report that coordinate as **no realized memory exposure**. Keep it in the planned accounting; do not discard quiet trials to inflate the effect. If there was no realized treatment anywhere, the comparison cannot answer whether administered MNEME influence changed behavior. An explicit exposure-conditioned analysis can be secondary, but must be planned rather than selected after seeing attractive responses.

## 8. Evaluate tendencies, not mandatory callbacks

The primary target is a history-dependent change in observable choices: explanatory organization, priorities, attention to transitions, analogy selection, questions, or patterns of emphasis. A model need not say “airplane” for its response structure to be compatible with the aviation example.

Conversely, similar response structure alone does not prove that analogy was active. Extracted features and self-reports are not direct access to hidden reasoning. Stronger attribution comes from controlled removal/restoration, eligible exposure records, and—where justified—targeted route ablation. [S1, §§10.9, 14.4–14.5]

Keep continuity, utility, intrusion, flexibility, and factual reliability separate. Do not collapse them into a reward for being quirky or a single “personality quality” score.

Use blinded paired evaluation and preserved raw responses. Code observable differences before providing developmental-history information; do not let the evaluator search retrospectively for a desired story. Keep the Interloper session separate from evaluation, even if the same model family serves both roles.

Plan repeated-seed comparisons, no-treatment variability checks, held-out prompt families, and uncertainty estimates appropriate to the number of independent **pairs/histories**. A hundred samples from one pair are not a hundred independently developed pairs. Shared adaptive branches are coupled, not independent subjects.

The owner's future human question—whether a conversational partner seems to have changed during interaction—remains distinct from anonymous-output classification. This supplement does not replace it or authorize recruitment. [S3, §5]

## 9. Instrument integrity before interpretation

Carry the learned Phase Two hygiene forward without turning this note into a new infrastructure project:

- Audit exact provider-visible roles. Gemma sees Qwen text as `user` and its own replies as `assistant`. Qwen sees its own participant messages as its generated history; the two Gemma replies are labeled input data, not its own assistant prefill. Randomize/counterbalance anonymized reply order independently of treatment and retain the private mapping.
- Persist one shared participant message before delivering it to either twin. At a paired boundary, retain completed work if the other call fails; do not regenerate the successful sibling merely to make the pair look tidy.
- Null, missing, empty, or whitespace-only conversational content is an immediate instrument stop. Preserve the request/result, send nothing downstream, and diagnose before bounded recovery. Never use silence as the substitute participant.
- Validate observation quality as well as syntax. An all-empty extraction is not, by itself, evidence that the conversation contained nothing. Test stubs remain offline tools, not live semantic instruments.
- Publish readable conversations, actual exposure records, state/seed bindings, failures, and analysis artifacts at ordinary audit boundaries. Preserve historical evidence and separate recovered, retrospective, and prospective results.

This document reports no new successful implementation, live experiment, or repository audit.

## 10. What the Phase Three plan still needs to decide

The selected planning direction is the shared-Interloper condition with paired local seeds and separate measurement of trace formation, influence, and consolidation.

The final plan must still choose the developmental horizon, number of independent pairs, scenario families, current-context allowance, thread schedule, frozen checkpoints, probe bank, repetition counts, compatibility fallback, analysis thresholds, and execution budget. Exact models and runtime settings must be verified at that point.

Reconcile this condition explicitly with the roadmap's staged first-study proposal. Do not silently add it as an uncosted full factorial study, or remove the simpler baselines and own-output controls. Ordinary prompt/role orchestration should use the existing harness; this note creates no requirement for a new service, memory architecture, or neural backend. [S2, §§6, 10–12]

**Consolidation reporting must remain separate from the broader conclusion.** “Transition not exercised,” “insufficient developmental opportunity,” “no administered influence,” “no detectable behavioral difference,” and “invalid instrument” describe different results. None is interchangeable with “individuality disproved.” Nor does an appealing difference automatically satisfy an unmet mechanism criterion.

Preserve the current Phase Two bookend and historical acceptance records. This supplement does not retroactively close that phase or authorize another Phase Two campaign. Future tests may finish positive, negative, or inconclusive without being expanded until a preferred result appears.

## 11. Filing and source basis

Add this Markdown note to Project Sources. If later committed, place it outside the approved-plan folder and link it beside Phase Three planning material as **methodology input—not an execution plan**. No repository upload, queue change, inference run, or phase transition is implied by creating the document.

**[S1] Governing specification:** *MNEME — Model Instance Development Through Earned Association*, revision 2026-09-13, `MNEME_Model_Instance_Development_Spec.md`. Especially §§3.1, 3.5, 4, 11, 14.2–14.6, and 16. Supplies the developmental objective, consolidation distinction, paired evaluation seeds, separate experimental regimes, and claim boundaries.

**[S2] Development roadmap:** *MNEME — Development Roadmap*, 2026-09-14, `MNEME_Development_Roadmap.md`. Especially P0.3–P0.4, §§5–6 and 10–12. Supplies reproducibility checks, isolated readout, staged Phase Three coverage, and finite exploratory studies. Its proposed numerical defaults are not adopted as this supplement's schedule.

**[S3] Research-intent amendment:** *Experiential individuality, perceived continuity, and complementary memory*, RI-EIC-2026-09-25, revision 2, `MNEME_Research_Intent_Amendment_Experiential_Individuality_2026-09-25_Rev2.md`. Especially §§2–6 and 8–10. Supplies utility separation, the fresh-thread versus conversational-switch distinction, and non-contamination of active work.

**[S4] Episodic-evidence decision:** *Conversational Episodes, Re-entry Provenance, and Developmental Evidence*, 2026-09-25, `MNEME_Research_Decision_Episodic_Evidence_Provenance_2026-09-25.md`. Supplies source-role separation, arc-level recurrence, model-origin refractory handling, and preservation of outcomes and ancestry.

**[S5] Developmental dynamics amendment:** *Continuity, plasticity, consolidation, and corrective feedback*, 2026-09-19, `MNEME_Developmental_Dynamics_Amendment_2026-09-19.md`. Especially §§3–8 and 12. Supplies the distinction between accessibility, expression, recurrence, and longer-term durability; it does not set a required conspicuous effect.

**[S6] Owner discussion, 2026-09-26:** Rey distinguished early, potentially subtle influence from established consolidation; explained developmental runway using the grass-path analogy and the surgeon/pilot example; emphasized matched local seeds; and proposed a single Qwen reading both Gemma answers and generating one compatible shared continuation. These are the decisions recorded here. The pair-coupling, full-history, and provenance qualifications make their experimental limits explicit; they are not claimed results.

This supplement synthesizes the supplied project sources and discussion. It is not a fresh literature review, a model-capability verification, or evidence that the proposed shared-partner condition has run successfully. Document titles and section references remain usable when relative paths do not resolve in Sources.

---

> **Shared incoming messages. Paired seeds. Separate histories. Measure whether experience changes what becomes likely—not whether the model announces the memory, improves every answer, or builds a permanent trail after three footsteps.**
