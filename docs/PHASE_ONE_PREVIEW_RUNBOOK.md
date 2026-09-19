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

Interpret exact and normalized matches, lexical overlap, and response lengths
as descriptive no-learning variation. They do not establish personality,
individuality, or causal developmental differentiation. Hosted Gemma sampling
remains provider-managed; do not describe a live run as deterministic unless
the declared host capability and seed contract support that claim.
