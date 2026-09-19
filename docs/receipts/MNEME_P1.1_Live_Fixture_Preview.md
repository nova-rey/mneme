# MNEME P1.1 live fixture preview

This is the human sanity check for the next bounded live P1.1 attempt. It is
not an extraction answer key and it does not require Gemma to emit any of the
labels used in this preview. The live run must preserve the actual inputs,
responses, extraction records, resolution decisions, graph state, and route
decision in the review-bundle format described by the Phase One runbook.

Fixture file: `configs/p1.1-live-fixture.json`
Fixture identity: `p1.1-natural-bridge-v1`

## Developmental experience 1

**Input:**

> Checking the weather before our hike reminded us to pack a rain jacket.

**Expected relationship shape:** checking weather can lead to packing a rain
jacket. The exact concepts, kinds, and relationship label remain model output
and must be source-supported.

## Developmental experience 2

**Input:**

> A rain jacket keeps a sudden shower from ending the hike early.

**Expected relationship shape:** having a rain jacket can help a hike continue
through a sudden shower. The exact concepts, kinds, and relationship label
remain model output and must be source-supported.

## Intended bridge concept

The two experiences share the ordinary object **rain jacket**. The first
experience describes why it gets packed; the second describes what it does on
the hike. If the extractor represents that bridge equivalently and the two
accepted directed edges are eligible, deterministic graph search should be able
to discover a two-edge path across the separate interpretations. No explicit
`route_candidates` record is required.

## Why a connected route is reasonably supported

These are distinct inputs and distinct situations: preparation before a hike
and protection during a shower. They are connected by a concrete object and a
plausible ordinary cause/effect relation. The preview does not assert that
Gemma must choose `rain_jacket`, `packing`, or any other predetermined key; it
only explains why a human reviewer should consider a connected route
reasonable before the call is made.

## Review boundary

The fixture is intentionally small and bounded. It does not claim causal truth,
learning, personality, or individuality. A live failure must be classified
from the persisted source/result and graph evidence rather than repaired by
manufacturing aliases or forcing expected labels. For this P1.1 developmental
demonstration, extraction is supplied only the immutable external input for
each episode; the host response remains durably recorded as model output but
is not treated as independent developmental evidence for the fixture edges.
The integrated live runner applies the same external-evidence-only boundary to
P1.2 developmental interpretation calls; host responses remain available in
the durable ledger and traces for audit.
