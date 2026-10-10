# Isolated MI1 llama.cpp candidate patch

This is a research-only patch against upstream llama.cpp commit
`4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`. It is not a production build or
production default. It implements the MI1 attached-bank attention path and
local encoder/query-capture helpers used by the isolated MI1 feasibility test.

To reconstruct the candidate, check out the pinned upstream commit, extract `source-bundle.tar.gz`; apply `tracked.patch`, then extract
`untracked-files.tar.gz` at the repository root. Verify the archive against
`SHA256SUMS`. The exact model/runtime smoke receipt is
stored outside Git at `/home/nyx/mneme-artifacts/phase4-mi1/native/`; the
compact validation receipt SHA-256 is
`fceceb7d3d45c0ffc45d7ae4dc98abf05e93d97de11f2d28b51274bd8e037544` (see the experiment freeze for the complete digest).

This source bundle contains no model weights, built binaries, or MNEME state.
