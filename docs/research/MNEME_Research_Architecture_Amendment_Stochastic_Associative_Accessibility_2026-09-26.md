# MNEME --- Research Architecture Amendment

## Stochastic Associative Accessibility and Consequence-Shaped Geometry

**Document ID:** RA-SAA-2026-09-26\
**Revision:** 1\
**Date:** 2026-09-26\
**Status:** Owner-requested guiding research and architecture amendment\
**Relationship:** Additive to the governing MNEME specification,
Developmental Dynamics, History-Shaped Influence, and Associative
Deformation Field amendments.\
**Purpose:** Define a research model for how developmental history may
shape which associations become accessible, how activation spreads
through learned neighborhoods, and how consequences reshape those
pathways.

> **RNG provides the possibility of surprise. Learned topology makes the
> surprise belong to this particular instance.**

## 1. Research question

MNEME is not intended merely to retrieve the most semantically relevant
stored association. The project asks whether accumulated experience can
change **what is likely to occur to an otherwise frozen model**,
including associations whose usefulness becomes apparent only after they
become accessible.

Human associative experience motivates this design question but is not
evidence that the same mechanism will work in a language model. The
mechanism proposed here is therefore an experimentally testable
computational approximation, not a claim about human cognition.

## 2. Weighted-lottery model

A useful metaphor is a simplified slot-machine pay table. Imagine many
possible outcomes, with common outcomes represented more heavily and
rare outcomes represented lightly. A random draw selects one position.

For MNEME, replace payouts with eligible learned associations or
conceptual neighborhoods:

``` text
developmental state
        +
current context
        ↓
temporary weighted association distribution
        ↓
seeded stochastic draw
        ↓
an association/neighborhood becomes salient
```

The implementation need not literally duplicate entries in a list. The
governing property is:

> **Selection is stochastic, but the probability distribution is
> history-shaped.**

## 3. Randomness is not individuality

Pure randomness is not individuality. MNEME becomes interesting when
developmental history changes the distribution over possible activation.

Given the same frozen host, prompt, host-generation seed, and field-RNG
seed, two differently developed instances may map the same random draw
onto different associations because their histories created different
effective pay tables.

> **Experience changes what a random event means because experience
> changed the pay table.**

This is a candidate operational definition of history-shaped associative
individuality.

## 4. Developmental weight and current relevance are different

At least two forces should be distinguished.

**Developmental weight** asks how strongly an association or
neighborhood has become established for this instance through
experience.

**Contextual relevance** asks how strongly the current situation favors
that association now.

A deeply developed but currently distant association may retain a small
probability. A weakly developed but highly relevant association may
receive a strong temporary boost. Strong history plus strong relevance
may dominate. Weak history plus weak relevance may remain a long shot
without necessarily becoming impossible.

Relevance therefore modifies the lottery; it does not define whether
developmental history exists.

## 5. Novel situations flatten contextual preference

In familiar territory, current context can produce a peaked
distribution:

``` text
A ███████████████████
B ███████
C ███
D █
```

In genuinely unfamiliar territory, context supplies less evidence for
preferring one learned neighborhood:

``` text
A ██████
B █████
C ████
D ███
```

The distribution is flatter, not necessarily uniform. Developmental
priors still matter.

> **As contextual certainty decreases, developmental priors become
> relatively more influential.**

This replaces the relevance-gated conclusion "nothing matches, therefore
MNEME contributes nothing."

## 6. Relevance may be discovered after activation

An association can become useful only after entering consideration.

The system should therefore preserve the possibility that a weak or
initially odd association becomes accessible first, after which an
analogy, intermediate concept, or framing reveals why it matters.

MNEME must not require proof of downstream usefulness before every
association is allowed into consideration. This is a central reason to
investigate bounded stochastic accessibility.

## 7. Nexi and learned geometry

A **nexus** represents a concept, thought-like unit, or learned
conceptual region.

A **link** represents learned associative affinity or traversability:
how readily activation of one region makes another accessible for this
developed instance.

Example:

``` text
Instance A:
RNG ═════ casino ═════ slot machines ═════ pay tables
 │
 └── dice ── RPGs

Instance B:
RNG ═════ dice ═════ RPGs ═════ probability
 │
 └── casino ── slots
```

The frozen host may already know every concept shown. MNEME is not
relearning those concepts. It is learning that **for this instance**,
some routes between them have become unusually easy to traverse.

## 8. Weighted landing, then local neighborhood activation

Do not model associative thought as repeated unrestricted global random
jumps.

Instead:

1.  Context and developmental state define a weighted accessibility
    distribution.
2.  A bounded stochastic draw selects an initial associative landing.
3.  That nexus becomes a temporary local center of activation.
4.  Activation spreads preferentially through strong learned links.
5.  Weak/distant links receive less propagated activation.
6.  The resulting neighborhood can influence host generation.
7.  Activation decays unless reinforced.

``` text
context + developmental priors
            ↓
weighted stochastic landing
            ↓
local nexus activates
            ↓
learned topology shapes spread
            ↓
temporary active neighborhood
            ↓
bounded host influence
```

The lottery determines **where attention lands**. Learned topology
determines **what becomes easy to reach once it lands there**.

## 9. World-map / dart interpretation

The same mechanism can be pictured as a world map. A weighted draw
throws a dart. The landing region becomes locally important; nearby
roads and cities become clearer.

A mature developmental history changes both:

-   where the dart tends to land;
-   which roads are wide, narrow, blocked, or well traveled afterward.

The entire map does not become equally active.

## 10. Activation decays

A strong neighborhood must not permanently capture the model.

Temporary activation should decay unless reinforced by current context,
external re-entry, continued relevance, or later developmental evidence.

This gives the system a natural way to leave a topic without making
every return impossible. External re-entry can immediately reactivate a
neighborhood; model self-repetition alone should not manufacture
developmental importance.

## 11. Consequences reshape the geometry

Accessibility alone is incomplete. MNEME should learn from what happened
after an association became active.

If an unusual casino analogy surfaces during potato farming and receives
clear negative consequence evidence, MNEME should not conclude "casinos
are globally bad." It should learn something closer to:

> **From this neighborhood, this route was not productive.**

That route becomes less likely from similar contexts.

If an unexpected potatoes → limited space → vertical gardening route
produces useful engagement, that route may strengthen.

MNEME therefore learns both:

-   what associations exist;
-   which routes have historically been worth following **from where**.

## 12. Consequence is contextual, not a global reward

Do not reduce consequence to:

``` text
casino = bad
vertical gardening = good
```

The same association can be poor in one context and useful in another:

``` text
casino framing × potato cultivation
    → poor consequence

casino/probability framing × commodity uncertainty
    → potentially useful consequence
```

Mature associative geometry should become more nuanced, not merely more
suppressive.

## 13. Multi-resolution / fractal neighborhoods

Repeatedly coactivated, strongly connected nexi may eventually behave
like larger conceptual regions.

At low resolution:

``` text
potatoes ═════ limited growing space ═════ vertical gardening
```

At higher resolution:

``` text
SPACE-EFFICIENT CULTIVATION
    ↔ resource scarcity
    ↔ automation
    ↔ hydroponics
    ↔ urban infrastructure
```

This suggests a future scaling direction in which the graph can be
traversed at multiple resolutions rather than evaluating every atomic
edge on every turn.

This amendment does not mandate immediate clustering or hierarchy
implementation.

## 14. Experience changes effective distance

Repeated successful traversal may make nexi effectively closer. Repeated
poor traversal may make them farther apart in the relevant context.

"Distance" is conceptual and may later correspond to transition
probability, edge strength, attenuation, neighborhood membership,
routing cost, or another representation.

Do not prematurely freeze the metaphor into one mathematical encoding.

> **Development changes the ease with which activation moves between
> conceptual regions.**

## 15. Developmental maturity as learned selectivity

A young MNEME has sparse evidence. Its distributions may therefore be
flatter and its associative excursions more erratic.

With experience:

-   productive routes become easier;
-   repeatedly poor routes become less likely from relevant contexts;
-   contextual distinctions become richer;
-   neighborhoods become more structured.

A more experienced instance may therefore become less arbitrarily
erratic **not because randomness disappeared, but because experience
increasingly shapes the distribution from which randomness samples.**

## 16. "Annoying kid" behavior can be developmental

New experiences may temporarily become unusually accessible.

That should be measured rather than automatically engineered away.

If the fixation proves unhelpful across contexts, consequence-shaped
learning should reduce its reach. If it repeatedly proves useful, it may
legitimately become characteristic.

> **Temporary fixation can be developmental. Permanent indiscriminate
> fixation is a failure mode.**

Do not solve every fixation with a universal cooldown before testing
whether development itself can reshape it.

## 17. Accessibility is not mandatory expression

Winning the associative lottery does not require an association to
appear in the final response.

``` text
association becomes accessible
        ↓
neighborhood influences available framing
        ↓
host may use it, transform it, connect it, or ignore it
```

The purpose is to alter what becomes available to influence generation,
not to force random callbacks.

## 18. No false history

Stochastic exploration operates only over legitimate eligible
developmental state.

``` text
no developmental history
    → no history-derived lottery
```

Once history exists:

``` text
eligible history
    → weighted accessibility can operate
```

Randomness selects from earned state. It never fabricates
autobiographical experience.

## 19. First inspectable computational approximation

A practical non-neural implementation can proceed in stages.

### A --- Active context

Build a bounded representation of the current conversational/problem
neighborhood.

### B --- Temporary accessibility weights

For eligible developmental nexi/neighborhoods, combine available signals
such as:

-   developmental weight;
-   contextual relevance;
-   current accessibility;
-   consequence-shaped contextual affinity.

Avoid a hard relevance gate.

### C --- Bounded normalization

Convert effective weights into a valid weighted sampling distribution.

### D --- Seeded associative landing

Use a dedicated field RNG to select an initial association or
neighborhood.

### E --- Local propagation

Spread activation through a bounded number of strongly connected links,
attenuating with weak edge strength and distance.

### F --- Temporary active neighborhood

Produce a small auditable representation of the activated region.

### G --- Host influence

Compile the region into the existing text-mediated influence backend
without exposing raw graph labels, provenance, scores, or experiment
metadata.

### H --- Consequence update

After interaction, use independently valid consequence evidence to
strengthen, weaken, contextualize, or leave unchanged the traversed
pathways.

## 20. Separate random streams

Research instrumentation should distinguish:

**Host-generation RNG** --- controls stochastic language generation.

**Field-accessibility RNG** --- controls stochastic developmental
accessibility.

These should be independently seedable.

This enables:

``` text
same host
same prompt
same host seed
same field seed
different developmental history
```

If the associative landing differs, the difference can be traced to
developmental state rather than a different random input.

Administrative metadata must never silently seed either stream.

## 21. Exploration budget

The mechanism must remain bounded.

Candidate controls include:

-   maximum stochastic landings per generation;
-   maximum propagation depth;
-   attenuation;
-   minimum eligible developmental weight;
-   total pressure budget;
-   maximum active-neighborhood size;
-   activation decay.

Calibrate boundedness before behavioral measurement. Do not increase
exploration after seeing a boring result.

## 22. Consequence evidence remains provenance-aware

The model's own output cannot certify that its association was good.

Developmental consequence should rely on approved evidence such as
external participant response, later externally supported
success/failure, explicit correction, legitimate re-entry, or other
authorized provenance.

Self-repetition must not manufacture success.

## 23. Weakening is not deletion

Poor consequence should normally alter probability rather than erase
history.

A weak route can occasionally remain accessible. This preserves
plasticity and permits context-specific rehabilitation.

Distinguish:

``` text
unlikely
```

from:

``` text
forbidden
```

Quarantine, policy, deletion, and other hard controls remain separate.

## 24. Strengthening can create characteristic neighborhoods

Repeated successful traversal may transform a rare surprising route into
a characteristic tendency:

``` text
rare associative route
    ↓
successful consequence
    ↓
higher future accessibility
    ↓
repeated coactivation
    ↓
strong neighborhood
    ↓
characteristic tendency
```

This is a candidate path from isolated experience to stable
individuality without changing base-model weights.

## 25. Relationship to the Associative Deformation Field

The deformation-field amendment proposed:

> **The web changes the shape of the sheet.**

This amendment adds a candidate dynamic:

> **Weighted stochastic accessibility determines where the web is
> tugged; learned topology determines how the tug propagates;
> consequence reshapes the web afterward.**

Together:

``` text
developmental history
        ↓
history-shaped weighted distribution
        ↓
seeded associative landing
        ↓
local weighted propagation
        ↓
temporary conceptual neighborhood
        ↓
bounded deformation of host behavior
        ↓
external consequence
        ↓
updated contextual geometry
```

## 26. Relationship to the current F0 renderer

The current F0 experiment demonstrated that a bounded abstract influence
can alter paired Gemma outputs, but a renderer that collapses varied
internal field states into one generic sentence cannot test whether
**different developmental geometries produce different characteristic
pressures**.

The next implementation should therefore preserve more of the direction
and composition of the activated neighborhood while continuing to
prevent:

-   raw graph-label leakage;
-   autobiographical memory commands;
-   provenance leakage;
-   explicit instructions to make a predetermined analogy.

The renderer should communicate a temporary conceptual tendency, not
dump the graph and not reduce every field state to "geography exists."

## 27. Critical sibling experiment

A particularly important future experiment is:

``` text
Sibling A:
    base Gemma + developmental history A

Sibling B:
    same base Gemma + developmental history B

Control:
    same base Gemma + no MNEME influence
```

Then hold constant:

-   novel probe;
-   host-generation seed;
-   field-RNG seed;
-   model/runtime configuration.

Observe:

-   which nexus/neighborhood wins the accessibility draw;
-   how activation propagates;
-   what bounded influence reaches Gemma;
-   whether outputs diverge in history-characteristic ways.

Removal/restoration should test whether the divergence follows MNEME
state.

The desired evidence is not merely that outputs differ.

The stronger result is:

> **Different experiences changed what became accessible under otherwise
> matched conditions.**

## 28. Failure modes

### RNG dominates history

If different seeds matter more than developmental state, the mechanism
has become noise.

### Relevance dominates RNG completely

If only the obvious nearest semantic neighbor can ever win, the system
has collapsed back into retrieval.

### One neighborhood captures everything

If a strong region continually reactivates regardless of
consequence/context, activation/decay or consequence learning is
inadequate.

### Bad consequence globally lobotomizes a concept

Negative evidence should normally reshape contextual routing, not erase
a concept everywhere.

### The renderer dictates the answer

Field influence must bias possibilities, not hand Gemma a required
conclusion.

### Self-reinforcement creates fake maturity

Model repetition cannot independently thicken its own pathways without
appropriate evidence.

### Randomness fabricates history

Impossible. Exploration operates only over earned state.

## 29. Research claims this amendment does not make

This amendment does not claim:

-   human cognition literally uses this algorithm;
-   stochastic associative accessibility will produce personality;
-   current graph nodes are equivalent to human thoughts;
-   graph distance equals neural distance;
-   useful connections will dominate;
-   maturity necessarily improves task performance;
-   neural intervention is required now.

It defines an experimentally useful approximation of a target
phenomenon.

## 30. Governing principles

> **Do not require an association to prove its usefulness before it is
> allowed to occur to the instance.**

> **Context changes the odds. History defines the prior landscape. RNG
> permits surprise.**

> **Once attention lands, learned topology determines what becomes
> easier to reach nearby.**

> **Consequences teach the instance which of its own associative routes
> are worth following from where.**

> **Random weirdness is noise. History-shaped weirdness is data.**

> **The objective is not to make every thought relevant. It is to make
> what occurs to the instance depend, probabilistically and audibly, on
> what that instance has experienced.**
