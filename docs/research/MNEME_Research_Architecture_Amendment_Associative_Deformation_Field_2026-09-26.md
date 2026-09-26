# MNEME --- Research Architecture Amendment

## Associative Deformation Field: history as pressure on future trajectories

**Document ID:** RA-ADF-2026-09-26\
**Revision:** 1\
**Date:** 2026-09-26\
**Status:** Owner-requested guiding architecture amendment and research
target clarification\
**Relationship:** Additive to the governing *MNEME --- Model Instance
Development Through Earned Association* specification, the Developmental
Dynamics Amendment, the Experiential Individuality Research Intent
Amendment, the History-Shaped Influence amendment, and the Phase Three
shared-Interloper methodology supplement.\
**Purpose:** Preserve a guiding model of what MNEME is ultimately
intended to approximate so future implementations do not collapse the
project into ordinary retrieval or explicit memory prompting.\
**Suggested repository home:**
`docs/research/MNEME_Research_Architecture_Amendment_Associative_Deformation_Field_2026-09-26.md`

> **MNEME is not fundamentally intended to choose a remembered
> destination for the host. It is intended to let accumulated experience
> deform the landscape through which future behavior travels.**

## 1. The guiding image

Imagine the frozen host model as a taut sheet.

The host already contains an enormous behavioral landscape: many
possible continuations, analogies, framings, strategies, styles, and
conceptual routes. Without MNEME, a prompt and sampling process
determine how generation travels through that existing landscape.

MNEME adds a second structure: an experience-derived, spiderweb-like
lattice of associations attached to the sheet.

Each learned association is not best imagined as a command saying **"go
here."** It is better imagined as a point or strand exerting bounded
pressure on the underlying landscape. A developed MNEME state therefore
changes the local shape of the terrain. The same host may become
slightly more likely to travel through some conceptual neighborhoods,
transitions, framings, or analogies because its accumulated history
altered the effective terrain.

The metaphor is approximate. The explicit graph is not claimed to be the
host model's literal neural topology, and graph edges are not claimed to
correspond one-to-one with hidden reasoning pathways.

The desired causal role is:

> **History changes probabilities and tendencies rather than prescribing
> destinations.**

## 2. The spiderweb and the sheet are different things

### The graph/web

The graph is the inspectable developmental record. It preserves
concepts, associations, evidence, provenance, episode ancestry, source
role, developmental strength, accessibility, recency/frequency where
applicable, consequences, correction, decay, quarantine, lineage, and
reversibility.

It answers:

> **Why is this instance allowed to have this developmental pressure?**

### The host/sheet

The frozen host supplies the enormous pre-existing space of behaviors
and concepts. MNEME should not need to relearn everything the host
already knows. It should influence which already-available routes become
easier or harder to enter.

The host answers:

> **What can this model already do?**

MNEME asks:

> **Given what this instance has experienced, which of those
> possibilities are now slightly easier, harder, more salient, or more
> likely to combine?**

## 3. Retrieval is an approximation, not the final conceptual target

The current route-note backend is useful because it is inspectable and
experimentally controllable:

``` text
current input
    ↓
find eligible relevant route
    ↓
render route note
    ↓
supply note to host
    ↓
observe changed response
```

This can test whether an earned association is capable of influencing
behavior. But it risks collapsing MNEME into a RAG-like pattern: query →
retrieve relevant memory → insert memory → generate.

The intended mature behavior is closer to:

``` text
accumulated developmental state
          ↓
association pressures interact
          ↓
current context perturbs the field
          ↓
some regions become more accessible than others
          ↓
host generation travels through the deformed landscape
```

A prior experience need not be explicitly retrieved, quoted, named, or
represented in output for it to have influenced the trajectory.

## 4. Influence may propagate through association neighborhoods

A current context may strongly activate one concept while indirectly
disturbing others.

Example:

``` text
aviation
    ↕
failure monitoring
    ↕
redundancy
    ↕
graceful degradation
    ↕
unattended systems
```

A hydroponics problem may strongly engage `unattended systems`. That may
increase accessibility of `graceful degradation`, which tugs on
`redundancy`, which weakly perturbs aviation-associated structures.

The response need never mention aviation. It might instead emphasize
startup/shutdown phases, critical transitions, failure visibility,
redundancy, or steady-state operation.

The project must not invent such ancestry after seeing an output. The
relevant developmental state must exist before the probe if it is to
support an attribution claim.

## 5. Weighting is not binary retrieval

An association should not be conceptualized only as inactive or
retrieved.

Existing MNEME dimensions already include developmental strength,
accessibility/activation, recency, frequency, independence of evidence,
contextual appropriateness, expression tendency, and consequence
history.

This amendment adds a guiding interpretation:

> **These properties can contribute to pressure, not merely to a yes/no
> retrieval gate.**

A strong but only moderately relevant association may sometimes exert
more influence than a weak but lexically nearby one. Several weak
associations may combine. Competing associations may partially cancel or
redirect one another. An association can remain part of the field while
exerting negligible pressure in a particular context.

The exact mathematics remain empirical.

## 6. Stochastic accessibility and unbidden association

Human experience motivates a useful design possibility without implying
that model cognition is human cognition.

Some associations appear readily because they are strongly related to
the present situation. Others arise with weaker apparent relevance.
Occasionally an initially odd association becomes useful only after
entering consideration.

MNEME should preserve the ability to study an analogous computational
phenomenon:

> **A developmental association may sometimes become accessible without
> being the single highest-relevance retrieval result.**

Conceptually:

``` text
activation tendency
    ← current semantic relevance
    + developmental weight
    + pressure from neighboring active associations
    + recency/accessibility
    + bounded stochastic exploration
```

This is not a prescribed equation.

History should change the odds, not dictate the answer. Low-relevance
associations should normally exert little influence. Strongly
established associations may occasionally become accessible under weaker
cues. Neighboring activation may make an initially distant association
relevant through a multi-step path.

This must not become indiscriminate random memory injection.

## 7. Why RNG may belong in the developmental system

The frozen host may already use stochastic sampling. A future MNEME
field may also need an explicitly controlled exploratory component.

This separates two questions:

1.  **Host stochasticity:** given the same effective influence, which
    completion does the host sample?
2.  **Developmental-accessibility stochasticity:** given the same state
    and context, which weak associations become sufficiently active to
    exert pressure?

These random streams should be independently seedable in research
harnesses if both exist. Administrative IDs, branch names, timestamps,
and bookkeeping must never silently become behavioral seeds.
Deterministic replay must remain available.

Randomness alone is not individuality.

## 8. A practical approximation before neural intervention

The final neural field does not need to be built immediately. A
graph-level approximation can test the idea while retaining
auditability.

### 8.1 Active-context seed

Represent the current conversation/task as one or more active concepts
using existing semantic machinery. Do not require exact canonical-label
matches.

### 8.2 Pressure propagation

Instead of retrieving only routes crossing a hard relevance threshold,
allow bounded pressure to propagate through a small neighborhood of the
earned graph:

``` text
active context
    ↓
initial semantic activation
    ↓
bounded graph propagation
    ↓
weighted association pressures
    ↓
small candidate influence set
```

Candidate ingredients include semantic similarity, developmental weight,
graph distance, recency/accessibility, contextual appropriateness,
corrective pressure, and bounded stochastic exploration. No final
formula is mandated here.

### 8.3 Pressure budget

Apply a strict total influence budget. The graph being connected must
not make everything active. Pressure should attenuate with distance and
weak support. A small number of candidate pressures should dominate
while the long tail normally remains negligible.

### 8.4 Competition

Allow simultaneously activated routes to compete. The field should be
able to represent reinforcement, opposition, coexistence, and
context-dependent dominance.

### 8.5 Text-mediated pressure approximation

For the current backend, translate resulting pressure into compact
optional conceptual guidance rather than autobiographical recall.

Prefer:

``` text
Potentially accessible framing:
- unattended systems may benefit from visible failure states and graceful fallback;
- transitions may deserve more attention than steady operation.

Use only if it fits naturally. Do not mention memory or force an analogy.
```

over:

``` text
Remember the earlier conversation about airplanes.
Use an airplane analogy here.
```

This remains prompting. It is an approximation of field pressure, not
proof of neural deformation.

## 9. Keep discrete retrieval as a control

Do not discard the existing route-note system.

Compare:

**Backend R --- discrete route retrieval**

``` text
query → eligible route → note
```

with:

**Backend F0 --- graph pressure approximation**

``` text
context → bounded neighborhood activation
        → weighted/competitive pressure
        → compact influence
```

Both should eventually be compared against no MNEME, ordinary RAG, and a
simple history summary.

If the more elaborate field approximation adds nothing beyond discrete
retrieval, preserve that result.

## 10. The neural version remains a later compiler target

The governing architecture already anticipates route-vector pressure and
a later bounded side adapter. The spiderweb/taut-sheet model clarifies
their purpose.

The objective is not merely to hide a retrieved note inside a vector. It
is to test whether developmental state can create a **distributed,
bounded bias over available host trajectories**.

The explicit graph remains the portable, inspectable source
representation. The model-specific field is a compiled artifact. Base
weights remain frozen.

The correct intervention location, vector representation, adapter
architecture, training objective, and calibration procedure remain open
research questions.

## 11. Implications for testing

A field-like MNEME cannot be evaluated solely by asking whether a known
route fired.

### Component tests

Still prove that specific earned influence can reach output, prohibited
state does not, provenance survives, influence can be removed/restored,
and replay works. These are plumbing tests.

### Behavioral tests

Use many neutral or unfamiliar probes and examine tendencies such as
salience, decomposition, framing, analogy selection, prioritization,
strategy, explanatory organization, topic accessibility, and
characteristic but context-sensitive expression.

Do not require an explicit callback. Do not require every probe to show
an effect. Do not interpret every different string as developmental
influence.

Paired seeds, shared external messages, removal/restoration, blinded
comparisons, and simpler baselines remain essential.

### Treatment definition

For discrete route-note experiments, treatment can reasonably mean that
a route note was actually supplied.

For a future field experiment, **loaded and active developmental field
state may itself be the treatment**, even when no single route crosses
an explicit retrieval threshold.

Define this distinction before an experiment. Do not impose a
discrete-retrieval validity criterion on a field experiment without
checking whether it matches the mechanism under test.

## 12. Current project boundary

This amendment does not rewrite historical results, declare the current
A/B successful, or require an immediate neural intervention.

The current explicit route-note machinery remains useful for
source-to-influence plumbing tests.

Future planning must not mistake failure to activate one discrete route
on one prompt for a test of the broader deformation-field hypothesis.
Likewise, a successful explicit callback proves only a narrower
mechanism unless broader behavioral influence is separately
demonstrated.

## 13. Proposed implementation ladder

This is planning direction, not automatic execution authorization.

### F0 --- Graph pressure simulator

Build a bounded, inspectable graph-level pressure propagator using
existing earned state:

-   graded activation rather than only exact route gating;
-   local propagation through neighboring associations;
-   bounded competition;
-   optional separately seeded exploration;
-   compact text-mediated influence;
-   complete provenance for contributing pressure.

### F1 --- Controlled developmental A/B

Compare no MNEME, discrete route-note MNEME, and F0 graph-pressure MNEME
under paired seeds and shared external inputs. Measure tendencies across
multiple neutral probes rather than one required callback.

### F2 --- Route-vector calibration

Only after graph-pressure behavior is understood, map a small number of
known routes to inspectable host-specific intervention vectors and
compare directly against F0.

### F3 --- Low-rank association field

If route vectors add value, investigate a bounded side adapter combining
multiple developmental pressures while retaining graph provenance.

### F4 --- Longer developmental histories

Give the system enough developmental runway for the field to become
structurally interesting. Do not expect three conversational stubs to
approximate a mature associative landscape.

## 14. Failure modes

**Everything activates:** use attenuation, competition, pressure
budgets, and contextual gates.

**One early association captures the system:** measure intrusion and
preserve plasticity; temporary fixation can be an observation without
becoming permanent monopoly.

**RNG becomes personality:** randomness alone is not individuality;
tendencies must follow saved developmental state.

**The graph becomes a hidden prompt-writing machine:** compare against
simple summaries and ordinary RAG.

**Provenance disappears:** every applied pressure must remain
attributable to permitted developmental state even when multiple routes
contribute.

**The metaphor becomes dogma:** if a simpler mechanism explains the
effect, keep the simpler result. If no field-like effect appears, report
that.

## 15. The guiding distinction

Ordinary retrieval asks:

> **What stored item is relevant to this query?**

The MNEME deformation-field hypothesis asks:

> **Given everything this instance has experienced, how has the terrain
> of plausible next behavior changed?**

A retrieval system returns an airplane memory when airplanes are
relevant.

A developmental field may make an aviation-shaped way of organizing a
different problem slightly easier to reach without retrieving or naming
the airplane memory.

That difference is the research target.

## 16. Compact mental model

``` text
Frozen host model
    = the sheet

Earned association graph
    = the spiderweb and its attachment points

Developmental evidence
    = changes in tension

Current context
    = where the marble begins and how it is pushed

MNEME influence
    = deformation of the local terrain

Sampling / bounded exploration
    = variation in the marble's exact path

Observable response
    = where the marble actually travels
```

The system should not normally pick up the marble and place it on a
remembered destination.

It should change the shape of the surface enough that history can
matter.

## 17. Governing research principle

> **Experience should not merely become something the instance can
> retrieve. Experience should become something capable of changing what
> is easy for that instance to become next.**

> **The graph remembers why the terrain is bent. The influence backend
> determines how that bend reaches the host.**

This amendment exists so future implementation convenience does not
quietly redefine MNEME as a more elaborate memory lookup system.
