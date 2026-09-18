# MNEME P0.2 real-Gemma acceptance receipt

Date: 2026-09-18
Store: fresh temporary P0.2 SQLite store
Operation: `55555555-5555-4555-8555-555555555555`

The bounded real-host demonstration completed through the P0.2 durable lifecycle:

- one request was prepared, generated outside the SQLite write transaction, persisted,
  and accepted;
- the accepted lineage revision is `1`;
- returned model: `google/gemma-4-E4B-it`;
- returned provider: `DeepInfra`;
- the persisted host fingerprint records the OpenAI-compatible DeepInfra execution path
  and correctly leaves the hosted model revision unknown;
- the store reopened read-only with the accepted episode intact and `PRAGMA foreign_key_check`
  and state verification clean;
- the sanitized machine-readable receipt is `artifacts/p02-real-gemma-receipt.json`;
- the credential, authorization headers, and raw conversation/output are absent from the
  receipt and from Git.

This receipt proves durable association of one real Gemma generation with a lineage. It
does not claim hosted/local exact-weight equivalence or any behavioral individuality result.
