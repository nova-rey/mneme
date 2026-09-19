# MNEME — Developmental Dynamics Amendment

## Continuity, plasticity, consolidation, and corrective feedback

**Date:** 2026-09-19  
**Status:** Design amendment for Phase One and later developmental mechanisms  
**Relationship to current specification:** Supplements the current *MNEME — Model Instance Development Through Earned Association* specification. It does not replace Phase Zero architecture or its accepted experimental controls.  
**Scope:** Formalizes the developmental implications of the discussion following Phase Zero closure. It is a design commitment and research hypothesis, not a report of demonstrated behavior.

---

## 1. Purpose

Phase Zero established a laboratory in which a frozen host model can be wrapped by durable lineage, accepted history, checkpoints, forks, controlled experiments, isolated evaluation, and a measured no-learning baseline.

The next phase introduces the first causal feedback from an instance's history into its future behavior.

This amendment defines the developmental behavior that this feedback mechanism should be capable of expressing.

The central requirement is:

> **Development should leave residue without freezing the instance in time. Later experience should matter without simply replacing earlier development. Corrective environmental feedback should alter future expression without automatically erasing the underlying associations that produced it.**

MNEME is not intended to optimize an instance toward a user's preferences, nor to force all instances toward a designer-approved personality. It is intended to permit persistent, history-dependent tendencies to emerge while preserving continued plasticity.

---

## 2. Development is accumulation, not replacement

A developing instance should not behave as though every recent interaction overwrites its past.

A useful analogy is regional dialect development.

An individual raised for many years in Texas may acquire deeply established linguistic habits. Moving to Boston does not immediately replace those habits with Boston speech. Continued exposure may gradually introduce new pronunciation, vocabulary, rhythm, or conversational habits. Some earlier tendencies may weaken; some remain strong; some combine with later influences.

The resulting behavior can reflect both developmental periods.

For MNEME, this implies that developmental state should support:

- persistence of well-established associations;
- continuing acquisition of new associations;
- gradual shifts in relative influence;
- coexistence of old and new tendencies;
- competition among associations;
- context-dependent expression;
- change without wholesale replacement.

An instance should neither be permanently trapped by early development nor behave as a pure reflection of its most recent environment.

This tension can be summarized as:

> **continuity ↔ plasticity**

Too much continuity produces developmental lock-in. Too much plasticity produces an instance with little persistent individuality.

The appropriate balance is an empirical question.

---

## 3. Association strength is not one scalar concept

Phase One should not assume that every developmental property can be represented by a single value such as:

`association.weight += feedback`

At minimum, the design should preserve the conceptual distinction among several dimensions, even if early implementations use simpler approximations.

### 3.1 Strength

How established is the association in the instance's developmental history?

### 3.2 Recency

How recently has the association been encountered, traversed, or expressed?

### 3.3 Frequency

How often has it occurred?

Frequency alone must not imply importance.

### 3.4 Independence of evidence

Did the association recur across genuinely distinct experiences, or did MNEME itself repeatedly reactivate the same route?

Repeated MNEME-induced recurrence must not masquerade as repeated independent evidence.

### 3.5 Consolidation / developmental age

Has the association persisted across a substantial span of the instance's history?

Early or long-lived associations may become deeply consolidated. Whether developmental age should directly change learning dynamics is an experimental question, but the architecture should not make such investigation impossible.

### 3.6 Activation / accessibility

Given the present context, how readily does the association become available?

### 3.7 Expression tendency

If an association becomes active, how strongly should it influence observable output?

### 3.8 Contextual appropriateness

In what contexts has expressing this association been encouraged, tolerated, irrelevant, or explicitly discouraged?

These dimensions need not all become independent stored numbers in the first implementation. They define distinctions the learner must not accidentally collapse.

---

## 4. Recurrence and temporal reinforcement

Repeated experience should matter.

A route encountered repeatedly within a developmental period may gain influence faster than a route encountered once. Recurrence across longer periods may provide different evidence than a short burst of repetition.

The learner should therefore be capable of representing temporal effects such as:

- repeated exposure within a bounded time or revision window;
- recurrence across independent contexts;
- long-term persistence;
- periods without reinforcement;
- later reactivation.

However, short-term repetition must not automatically create permanent dominance.

A temporary fixation, novelty, game, running joke, or narrow task period may produce intense recurrence without becoming a lifelong characteristic.

This creates a distinction between:

> **short-term activation pressure**

and

> **long-term consolidation**

The exact functions governing these effects are not fixed by this amendment. They must be inspectable, bounded, and experimentally tunable.

---

## 5. Corrective feedback is developmental evidence

Developmental evidence can act in more than one direction.

Explicit environmental feedback such as:

> “Please stop doing that.”

or:

> “You keep bringing every explanation back to the same analogy.”

is strong evidence that a recurring behavior is intruding into contexts where it is not wanted or useful.

MNEME should take explicit corrective feedback seriously.

This is not a requirement to “punish” or “bully” a model. It is a requirement to represent environmental consequences.

Crucially, corrective feedback should not automatically erase the underlying conceptual association.

For example, an instance may have a well-established association between ecosystems and software architecture. If repeated ecosystem analogies become intrusive and a conversational partner explicitly asks the instance to stop using them constantly, the appropriate developmental change may primarily concern **expression and contextual gating**, not deletion of the association itself.

Thus:

```text
strong underlying association
        ≠
must express association whenever activated
```

Corrective feedback may reduce:

- expression tendency;
- intrusion into unrelated contexts;
- activation under particular contextual conditions;
- confidence that a route is appropriate for outward use.

It need not reduce the underlying historical association by the same amount.

---

## 6. Silence is not negative feedback; approval is not the objective

MNEME must not infer a simplistic reward model from ordinary conversation.

No laugh after a joke is not necessarily rejection.

A user changing the subject is not necessarily disapproval.

A user failing to praise an answer is not negative evidence.

Likewise, explicit positive feedback is meaningful but does not make user approval the objective function.

Statements such as:

> “That analogy was useful.”

can provide evidence that a route was effective in that context.

They should not produce:

> “The user likes this; maximize it globally.”

The instance remains the object of development. Human reactions are environmental events and consequences, not the definition of the personality MNEME should create.

---

## 7. Provenance of reinforcement is mandatory

The developmental learner must distinguish why a route recurred.

At minimum, future evidence should be capable of differentiating:

1. **External/environmental exposure** — a concept or behavior was introduced or reinforced by the environment.
2. **Model-origin recurrence** — the frozen host spontaneously generated or traversed the tendency.
3. **MNEME-influenced recurrence** — the existing developmental state increased the likelihood of the tendency appearing.
4. **Explicit positive feedback** — the environment directly encouraged some aspect of the behavior.
5. **Explicit corrective feedback** — the environment directly discouraged some aspect of the behavior.

This distinction is necessary to prevent self-reinforcement fraud.

A route that appeared once and was then repeatedly injected by MNEME must not accumulate the same evidence as a route that independently reappeared across many experiences.

The developmental loop is allowed to amplify tendencies. That amplification must remain attributable.

---

## 8. Strong or unusual tendencies are not automatically failures

MNEME is intended to permit spontaneous differentiation.

Therefore the system must not contain a hidden normalization rule equivalent to:

> “If an instance becomes too weird, make it average again.”

An instance may legitimately develop a strong interest, unusual analogy preference, recurring humor style, formal conversational manner, or other distinctive tendency.

The goal is not to prevent strong tendencies.

The goal is to distinguish:

- tendencies that became established through developmental history;
- tendencies that are contextually useful or harmless;
- tendencies whose expression has become intrusive;
- artifacts produced primarily by MNEME repeatedly reinforcing its own influence.

A strange but genuinely developed tendency is a valid experimental outcome.

A runaway feedback artifact is not equivalent evidence of individuality.

---

## 9. Developmental change may be asymmetric across time

The architecture should permit investigation of whether developmental plasticity changes over an instance's lifetime.

Possible hypotheses include:

- early associations consolidate more deeply;
- later associations remain capable of modifying established tendencies;
- long-established associations decay more slowly;
- recent environmental changes overlay rather than erase earlier development.

None of these is assumed true.

MNEME should not imitate human neurodevelopment merely because the analogy is attractive.

The requirement is narrower:

> **Do not design the learning representation so rigidly that developmental age, consolidation, and changing plasticity cannot later be tested.**

---

## 10. Phase One implications

Phase One should begin with an explicit, inspectable association system rather than immediately writing a neural field.

The initial learner should be able to:

- derive association evidence from accepted episodes;
- preserve evidence provenance;
- track recurrence and temporal information;
- distinguish independent recurrence from MNEME-induced recurrence;
- represent positive and corrective environmental feedback;
- separate association persistence from expression/gating pressure;
- allow associations to weaken in influence without deleting their provenance;
- keep learning bounded and reversible;
- expose why an association or expression tendency changed.

Initial influence may remain textual/graph-based so that causal effects can be inspected directly.

The eventual neural Earned Association Field remains a later compilation/influence backend.

---

## 11. Required failure-mode tests

Phase One designs should explicitly test at least the following developmental cases.

### 11.1 Temporary fixation

A tendency recurs intensely for a short developmental period and then disappears from the environment.

Expected property: it may become temporarily accessible without necessarily becoming permanently dominant.

### 11.2 Long-term environmental transition

An instance develops under Environment A and later spends substantial time in Environment B.

Expected property: B can influence future behavior without instantly deleting A; composite tendencies are possible.

### 11.3 Explicit corrective feedback

A strong recurring association begins to intrude into inappropriate contexts and receives explicit corrective feedback.

Expected property: inappropriate expression decreases without requiring deletion of the underlying association.

### 11.4 Positive contextual feedback

A route receives explicit positive feedback in a particular context.

Expected property: appropriateness in related contexts may increase without globally maximizing the route.

### 11.5 MNEME-induced recurrence

MNEME nudges a route, the model expresses it, and that expression appears again in subsequent history.

Expected property: the system does not count every downstream recurrence as independent evidence.

### 11.6 Genuine strong tendency

A tendency independently recurs across many experiences and contexts without corrective evidence.

Expected property: MNEME is allowed to consolidate it strongly, even if the resulting behavior is unusual.

---

## 12. Evaluation implications

Future experiments must measure more than whether two instances produce different text.

Relevant developmental measurements may eventually include:

- persistence after reinforcement stops;
- rate of acquisition;
- rate of attenuation;
- response to environmental transition;
- response to explicit correction;
- context specificity;
- intrusion rate;
- reactivation after dormancy;
- independence from explicit memory recall;
- provenance of observed influence.

The Phase Zero no-learning baseline remains the null condition for ordinary host variation.

Developmental effects must exceed or structurally differ from that baseline before they are interpreted as evidence of MNEME-induced differentiation.

---

## 13. Design principle

The desired developmental behavior can be summarized as:

> **History should matter, but not all history should matter equally forever. Repetition should strengthen tendencies without automatically making temporary fixation permanent. Later environments should modify earlier development without simply overwriting it. Explicit corrective feedback should shape expression without automatically erasing underlying associations. MNEME's own influence must never be mistaken for independent evidence that the influence was deserved.**

The target is not stability alone and not adaptability alone.

The target is **persistent individuality under continued development**.

---

## 14. Impact on the repository roadmap

This amendment should be treated as normative design context for Phase One and later learner/compiler work.

It does **not** reopen or invalidate Phase Zero.

Phase Zero remains the known-good pre-development laboratory tagged `mneme-phase-zero`.

Phase One planning should explicitly address:

- the developmental evidence model;
- association-strength versus expression/gating state;
- temporal recurrence and consolidation;
- corrective feedback;
- reinforcement provenance;
- bounded learning and attenuation;
- tests for temporary fixation, environmental transition, correction, and self-reinforcement.

No implementation should reduce the developmental rule to an unexplained single scalar reinforcement update without demonstrating that the distinctions in this amendment are preserved elsewhere.

The exact mathematical learning rules remain open research questions to be resolved through transparent prototypes and controlled experiments.
