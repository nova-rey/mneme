# MNEME Introspection Round Two Live Gemma Qualification

**Status: BLOCKED_HOST_UNAVAILABLE**

This receipt records the authorized live qualification implementation and its
current external blocker. No P3-INTROSPECT-100 developmental run was rerun and
no Phase Four work was started.

## Implementation

Commit `c915c1db5ad0a4639073f166b59a804d132ede17` adds the versioned
`p3-introspection-v3-live-round-two` contract:

1. Round One sends the completed arc and SAA exposures to local Gemma for
   unconstrained prose reflection.
2. Round Two sends that reflection plus a numbered target answer bank to a
   bounded filing form.
3. Python resolves target numbers to canonical identities, validates effects,
   evidence, ranges, deduplicates proposals, and applies bounded state changes.
4. A malformed primary filing can use one minimal-form fallback; a second
   failure abstains safely. Ordinary learning remains paused.

The qualification harness is
[`tools/qualify_introspection_live_round_two.py`](../../tools/qualify_introspection_live_round_two.py).
It implements six live-tested levels, preserves every model output, records
latency/token/provenance fields, separates first-attempt from eventual validity,
and runs the requested 100-review torture phase after level selection.

## Exact intended local model

- Model: `google/gemma-4-E4B-it`
- Host: `rey@100.115.208.48` (`brokeass-msi`)
- GGUF: `/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`
- Runtime: `/home/rey/src/llama.cpp/build-cuda/bin/llama-cli`
- Context: 4096; GPU layers: `all`; reasoning: `off`

## Blocker

At the qualification attempt, Tailscale reported `brokeass-msi` offline and
SSH to `rey@100.115.208.48` timed out. The model file and runtime therefore
could not be health-probed or invoked. Live call count is **0**. There are no
live Gemma outputs, no screening rates, no selected interface, and no valid
live torture result in this receipt. Synthetic/offline parser tests are not
being substituted for those measurements.

## Offline validation completed

- Focused introspection tests: **27 passed**.
- Full repository tests: **576 passed**.
- Ruff: passed.
- Strict mypy for `src/mneme`: passed.
- Wheel build: passed.
- Fresh-install import smoke: passed.
- CI: [run 37010463446](https://github.com/nova-rey/mneme/actions/runs/37010463446), passed.
- Historical P3 evidence: untouched.

## Resume command

After the MSI is powered and reachable, run from the repository root:

```bash
PYTHONPATH=src python3 tools/qualify_introspection_live_round_two.py \
  --fixtures 8 \
  --torture-reviews 100 \
  --seed 20026100 \
  --destination docs/receipts/MNEME_Introspection_Round_Two_Live_Gemma_Qualification_20261002.json
```

The command must be run against the real local Gemma host. It must not be
replaced by a hosted model or synthetic output. Once it completes, this report
must be superseded by the live metrics report containing the actual model
outputs, chosen level, fallback measurements, and end-to-end adjustment proof.
