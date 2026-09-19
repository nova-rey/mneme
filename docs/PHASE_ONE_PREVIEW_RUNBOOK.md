# MNEME Phase One graph-wrapper preview runbook

This preview compares fixed readouts against a published P0.2 checkpoint. It
does not learn, update associations, or write to the developmental lineage.

Create a new research store with the explicit development policy, then create
and publish the checkpoint through the existing state CLI. Keep the checkpoint
file private when it contains conversation content.

```bash
mneme --store private/subject.sqlite3 instance create --development-enabled
mneme --store private/subject.sqlite3 identity adopt --host fake
mneme --store private/subject.sqlite3 checkpoint create <instance-id> \
  --output private/subject.checkpoint.sqlite3
```

Prepare probes as a JSON array containing `probe_ordinal` and model-visible
`messages`, for example:

```json
[
  {"probe_ordinal": 0, "messages": [{"role": "user", "content": "Explain VRAM"}]},
  {"probe_ordinal": 1, "messages": [{"role": "user", "content": "Unrelated probe"}]}
]
```

Run the matched frozen treatments with the network-free host:

```bash
mneme experiment compare private/subject.checkpoint.sqlite3 \
  --probes private/probes.json --host fake --repetitions 2
```

The comparator executes `no_memory`, `lexical`, and fixed `graph` treatments
against the same probe coordinates. It opens the checkpoint read-only, records
before/after file and logical-state digests, and refuses to continue if the
checkpoint changes. Use `mneme experiment run inspect --verify` and the
existing artifact inspection commands for prepared-run provenance. Comparison
artifacts can be written through `run_matched_comparison(..., artifact_dir=...)`
and are private working evidence unless explicitly sanitized for publication.

Graph route candidates in an extraction are optional evidence that one source
explicitly grouped edges. Accepted directed edges are also searched
deterministically at publication time, within the approved three-edge and
bounded-route limits, so a path can span separate developmental experiences.
Search preserves edge direction, source evidence, eligibility, and canonical
ordering; it never invents a missing edge or relies on administrative IDs.

The same gate driver now supports the approved bounded live path. Start only
from `p1.1` with `--host gemma-deepinfra --live-budget phase-one-v1`; it runs
the complete P1.1→P1.2→P1.3 schedule in one private workspace, reserves every
call before dispatch, and stops after a required failure. A live workspace
contains `live_summary.json`, the developmental store, the P1.2 checkpoint,
and the P1.3 comparison artifacts. The CLI never resumes a partial live
workspace automatically or regenerates an uncertain provider call.

Interpret exact and normalized matches, lexical overlap, and response lengths
as descriptive no-learning variation. They do not establish personality,
individuality, or causal developmental differentiation. Hosted Gemma sampling
remains provider-managed; do not describe a live run as deterministic unless
the declared host capability and seed contract support that claim.

## Live-gate review evidence

The concise receipt is not sufficient for a human review of a live extraction
or route failure. After each live gate, generate a sanitized review bundle from
the persisted run records before deciding whether the fixture, model output,
extractor, resolver, or graph policy is responsible. Preserve the exact
model-visible developmental input and accepted host response, the exact source
slots supplied to the extractor, and the exact extractor template with every
constrained vocabulary and structural limit.

For every initial and permitted repair call, include the returned result,
validation status and errors. Then include accepted concepts and relationships,
canonical evidence spans, alias/resolution decisions, the published graph
snapshot, and each route candidate with its acceptance or rejection reason.
Include the tested software SHA, gate/run coordinates, artifact digests, usage,
and an explicit redaction statement. The bundle must be sufficient to replay
the inspection path:

```text
developmental input
  -> host response
  -> extractor input
  -> extractor output
  -> validation/resolution
  -> graph state
  -> route decision
```

Keep credentials, authorization headers, environment dumps, unrelated private
conversation content, and provider metadata that may contain secrets out of
the bundle. Public receipts may remain concise, and historical receipts must
not be rewritten; the review bundle is a separate sanitized evidence artifact.
