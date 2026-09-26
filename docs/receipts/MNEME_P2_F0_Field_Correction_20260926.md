# MNEME Phase Two F0 field correction receipt

Date: 2026-09-26  
Implementation: `f0-graph-pressure-v2-background`  
Historical implementation preserved: `f0-graph-pressure-v1`

This correction keeps the completed F0 v1 run and its evidence immutable. The
new version separates the field into two auditable components:

* **Background developmental pressure** is a weak bounded contribution from
  eligible earned graph state. It remains available after a topic change and
  is zero on cold start or when no eligible graph edge exists.
* **Contextual activation pressure** is derived from conservative local lexical
  activation and amplifies the relevant graph neighborhood. It does not decide
  whether developmental state exists.

Pressure is propagated through the earned directed graph with the existing
maximum depth, attenuation, contributor cap, and total budget. Weak eligible
pressure remains in the audit trace even when it is below the host rendering
floor. If no contextual contributor clears that floor, the strongest positive
background contributor is rendered once within the compact conceptual payload.
The payload contains labels and relationship framings only; graph IDs,
provenance, learner values, and treatment labels remain audit-only.

The prior `minimum_pressure` setting is retained for configuration compatibility.
In v2 it no longer removes weak pressure from the developmental field; the
separate `render_pressure_floor` controls normal payload pruning. This prevents
context mismatch from collapsing a nonempty history into an exactly zero field.

All contributors are deduplicated by edge using the strongest deterministic
path. Quarantined or ineligible edges remain explicit zero-pressure records and
cannot be selected or rendered. Corrective consequence only reduces existing
strength and cannot create pressure.

Optional exploration is explicitly versioned and off by default. With
`exploration="on"`, a separate caller-supplied `field_seed` performs one
weighted choice among already eligible positive-pressure background candidates;
it can replace at most one contributor slot and is bounded by
`exploration_budget`. It cannot create state, bypass quarantine, or override
permissions. Same field seed and configuration replay identically.

Focused validation in `tests/test_field_pressure.py` covers cold start,
off-topic nonzero background pressure, contextual dominance, quarantine,
bounded competition, v1 compatibility, deterministic replay, and weighted
exploration seed handling.
