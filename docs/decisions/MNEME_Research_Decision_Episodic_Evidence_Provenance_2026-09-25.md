# MNEME — Research Decision Note
## Conversational Episodes, Re-entry Provenance, and Developmental Evidence

**Date:** 2026-09-25  
**Status:** Research/architecture decision for future reference.  
**Relationship:** Additive to the MNEME Model Instance Development specification and Developmental Dynamics amendment. This note records the rationale behind the Phase Two episodic-evidence correction; it does not replace historical receipts or retroactively change prior experimental results.

## Decision in one sentence

> **Turns are messages; episodes are experiences. External recurrence can provide new environmental evidence, while model-origin recurrence can reveal a developing tendency without being allowed to certify itself as independent environmental support.**

## 1. Why this distinction is needed

A conversational relationship may be discussed across several consecutive turns without representing several independent developmental experiences.

For example, a user may describe a basil-watering problem, the model may suggest a cloth wick, the user may discuss trying it, and the model may elaborate for several turns. Treating every mention of `wick → maintains → moisture` as a new independent observation would artificially amplify one conversational event.

The intended unit is therefore a **conversational episode or arc**: a semantically continuous encounter containing potentially many turns, observations, proposals, and outcomes.

When the conversation genuinely pivots elsewhere, that episode closes or becomes inactive. If the same relationship later re-enters the conversation, the system should record not only that it returned but **why it returned and who reintroduced it**.

## 2. Evidence roles inside one episode

User/environment evidence and model-generated evidence remain distinct even when they concern the same relationship.

Example:

```text
Gemma:
"A cloth wick might keep the soil damp."

Later, Qwen/user role:
"I tried it. The soil stayed damp all weekend."
```

The first statement is a model-origin proposal or expression.

The second is external outcome evidence about that proposal. It must not be discarded merely because it occurred in the same conversational arc.

Likewise:

```text
"That idea sucked. My basil died."
```

is negative external outcome evidence. It can weaken, contextualize, or otherwise affect the existing association under the consequence rules without being treated as absence or as independent proof of an opposite factual relationship.

Thus one episode may contain:

- external observations;
- model-origin proposals;
- external positive or negative outcomes;
- dependent recurrence;
- corrections;
- unresolved or conflicting evidence.

These are different evidentiary roles, not interchangeable repetitions.

## 3. Re-entry after a topic pivot

After an episode closes, recurrence is classified partly by **re-entry initiator**.

### External/user-initiated re-entry

If the user independently brings an old subject back after the conversation has moved elsewhere, the old relationship is eligible to become a new external episodic recurrence.

Example:

```text
Basil discussion ends.
Conversation moves to travel.

Later user:
"Oh, by the way, that wick kept the basil alive all weekend."
```

There is no general cooldown against this evidence. The environment has independently made the old association relevant again.

Subject to ordinary grounding, semantic resolution, and provenance checks, it may provide separated external support.

### Model-initiated re-entry

If the user has moved on and the model immediately drags the old association back into the new topic, the recurrence should be recorded but must not become fresh independent environmental support.

Example:

```text
User:
"I'm trying to pack light for this trip."

Gemma:
"That reminds me of simplifying your basil-watering setup..."
```

This may be scientifically interesting evidence that basil has become unusually salient to the developing instance. It is not evidence that the environment independently taught basil again.

## 4. Model-origin refractory handling

A small explicit refractory/debounce window applies to **model-origin re-entry**, not to the association itself and not to independently initiated user evidence.

The initial engineering rule is two completed conversational rounds after a genuine topic pivot.

During this window, a Gemma-origin return to the recently closed semantic neighborhood is:

- recorded as present;
- attributed to the model;
- linked to the prior episode;
- marked as re-entry;
- awarded no new independent/model-origin developmental credit for that recurrence.

This prevents a self-reinforcement loop in which recent salience causes the model to mention an association, the mention is counted as new support, and that support makes the association still more likely to recur.

The two-round value is an explicit initial control parameter, not a claim about a natural psychological constant.

## 5. User evidence is not blocked by the refractory window

The model-origin refractory rule must never suppress genuinely new external evidence.

If the user independently returns to basil one turn after the pivot, that evidence is processed normally even though Gemma itself would still be inside its model-origin refractory window.

The conceptual rule is:

> **The environment is always allowed to make an old experience relevant again. The developing model is not allowed to manufacture independent evidence for its own freshly salient obsession.**

## 6. Preserve ancestry when the model causes the return

A second loophole must also be avoided.

If Gemma reintroduces basil and the user merely answers:

```text
Gemma:
"That reminds me of your basil."

User:
"Yeah, the basil is doing fine."
```

then the re-entry remains model-initiated. The user's reply does not retroactively turn the topic return into an independently initiated external recurrence.

However, genuinely new outcome information contained in the reply remains external evidence and should be preserved according to its meaning.

The system therefore needs to distinguish:

- who reopened the semantic episode;
- who supplied each observation within it;
- whether the user supplied genuinely new outcome metadata;
- whether a recurrence was externally initiated, model initiated, or MNEME induced.

## 7. Later spontaneous model recurrence can still matter

The refractory mechanism is not a permanent prohibition on model-origin developmental evidence.

After genuine semantic separation, a later spontaneous model return to an old association may be evidence that the tendency has become endogenously accessible.

That remains **model-origin evidence**, not external confirmation, and should receive only the bounded treatment appropriate to model-origin recurrence.

This distinction is intentional:

> “The environment keeps bringing this back”

and

> “This instance keeps bringing this back on its own”

are different developmental phenomena.

The latter may be exactly the kind of emerging idiosyncrasy MNEME is intended to observe.

## 8. Minimal episodic abstraction

The resulting conceptual pipeline is:

```text
raw conversational turns
        ↓
conversational episodes/arcs
        ↓
source-role observations and outcomes
        ↓
cross-episode recurrence + re-entry ancestry
        ↓
MNEME associative/developmental state
```

An episode representation should minimally preserve:

- episode identity for bookkeeping;
- start/end conversational coordinates;
- semantic/topic neighborhood;
- initiation/source role;
- observations and outcomes occurring within it;
- links to related earlier episodes;
- closure/pivot reason;
- re-entry initiator when an old neighborhood returns.

Administrative episode identifiers must not themselves influence model behavior or route ranking.

## 9. What this changes conceptually

This decision rejects two bad extremes:

### Count every mention

This would let one five-turn discussion masquerade as five independent developmental experiences and create runaway self-reinforcement.

### Discard everything related to current input

This would make genuine environmental learning impossible. A conversational partner's report that a suggestion worked or failed is still meaningful environmental evidence even though the model participated in the same arc.

Instead:

> **An episode tells us what happened during one encounter. Cross-episode recurrence tells us that something came back. Provenance tells us why it came back.**

## 10. Relationship to individuality research

A model repeatedly returning to a recently salient association can itself be an important observation.

The system should not suppress or erase that behavior merely because it is annoying, overrepresented, or not independently confirmed. A young developmental state may temporarily develop a disproportionate fascination with one conceptual neighborhood.

The research requirement is to keep the accounting honest:

- model obsession is not environmental confirmation;
- MNEME reinjection is not spontaneous recurrence;
- user-initiated recurrence is not model-origin recurrence;
- user feedback about an earlier model proposal is not disposable echo.

This permits MNEME to study emerging characteristic tendencies without allowing those tendencies to forge their own evidence.

## 11. Current scope

This note records the decision and rationale. It does not:

- retroactively change historical Phase Two receipts;
- declare any previous zero-credit observation incorrect;
- establish that two rounds is the final refractory interval;
- require a large discourse-analysis subsystem;
- authorize Phase Three;
- claim that conversational episodes correspond to human psychological episodes.

Historical evidence should be re-audited only through explicit versioned rebuild/superseding-interpretation procedures.

## Decision record

**Adopt:** conversational episode/arc as the developmental encounter abstraction above raw turns.

**Adopt:** separate evidentiary roles for user/environment observations, model-origin observations, outcomes, and MNEME-induced recurrence.

**Adopt:** no debounce against independently user-initiated recurrence after a topic pivot.

**Adopt:** an initial two-round refractory window for model-origin re-entry after a genuine pivot; record the recurrence but award no fresh credit during that window.

**Adopt:** preserve re-entry ancestry when the user responds to a model-initiated callback.

**Adopt:** allow later spontaneous model recurrence to become bounded model-origin developmental evidence after genuine separation.

**Preserve:** strong or unusual tendencies as legitimate observations rather than automatically normalizing them away.

---

> **If the user brings basil back, the environment brought basil back. If Gemma brings basil back, record the obsession—but do not let the obsession certify itself.**
