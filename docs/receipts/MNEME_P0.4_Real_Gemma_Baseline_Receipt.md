# MNEME P0.4 real Gemma baseline receipt

Status: **PASS**

Scientific identity: `p04-gemma-no-learning-baseline / revision 1`  
Contract digest: `09a172359936a18c17342775c6c5c708a2926353a899768b136cd2dd252a2851`  
Host: DeepInfra `google/gemma-4-E4B-it`; provider-managed sampling; hosted revision unknown.

The bounded study used two sibling subjects from one starting checkpoint, one
developmental interaction per subject, one held-out evaluation probe, and two
evaluation repetitions per subject. The hard ceiling was six model calls and
the run used exactly six: two developmental and four evaluation calls.

Measured output variation:

* Within-instance: exact agreement `0.0`, normalized agreement `0.0`, mean
  lexical Jaccard `0.17261904761904762`, two pairs.
* Between-instance: exact agreement `0.0`, normalized agreement `0.0`, mean
  lexical Jaccard `0.19444444444444442`, two matched pairs.

Provider-reported usage was 249 total tokens. Prompt/completion subtotals were
not supplied by the provider. Cost was not available from the provider response.

Evaluation isolation passed: four frozen evaluations completed, each asserted
unchanged checkpoint state and unchanged writable subject descriptor. Boundary
and private evaluation snapshot hashes matched for both subjects. Each subject
has exactly one accepted developmental episode and one generation record at
revision 1. Re-entering the completed run returned `COMPLETE` without issuing
additional calls or duplicating episodes, generations, or evaluation receipts.

Developmental influence was disabled throughout. Stored history was not added
to later prompts; the observed differences are ordinary no-learning variation
under these provider-managed execution conditions. This is a baseline noise
floor and does not establish personality, individuality, or causal development.
