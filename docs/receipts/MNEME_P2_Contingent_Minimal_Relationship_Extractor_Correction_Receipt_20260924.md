# MNEME Phase Two contingent minimal relationship extractor correction

**Status:** OFFLINE VALIDATED — live continuation pending

This receipt records the bounded replacement of the rich-language `residue-v5`
model-facing extraction form with the versioned `relationships-v1` contract.
Historical turns, accepted dialogue, and failed `residue-v5` attempts remain
unchanged.

The new provider-facing request asks only for a raw JSON object containing at
most six concise relationship proposals. Each proposal supplies `from`,
`relation`, `to`, `source`, and an exact quotation. Empty `relationships` is a
valid result. The model does not construct concept keys, offsets, confidence,
routes, provenance, or other administrative residue fields.

Deterministic software converts valid proposals into the existing canonical
residue, applies the existing source-grounding and admission boundary, maps
only the approved bounded relationship aliases, rejects malformed or
unsupported items individually, deduplicates deterministically, and records
capacity omissions. No route candidate is required; accepted graph edges are
still routed by the existing bounded graph search.

The raw provider result remains immutable in the interpretation attempt. The
derived residue and normalization/admission decisions are published in the
extraction artifact. Retrospective recovery operations use a distinct
operation ID and extractor version and cannot rewrite historical failures.

## Offline evidence

- Full pytest: **399 passed**.
- Ruff: **passed**.
- Strict mypy: **passed**.
- Provider calls: **none**.
- The existing rich-language and historical failure fixtures remain present;
  new fixtures cover the minimal request, empty output, item-level rejection,
  exact source binding, and the six-proposal capacity boundary.

The preserved contingent run remains paused at its historical review boundary
until the new instrument is applied to eligible failed interpretations and the
continuation is executed under its existing bounded authority.
