# Local Gemma determinism operations note

**Recorded 2026-10-02.** The local `google/gemma-4-E4B-it` stack may use
llama.cpp prompt caching during ordinary conversational and developmental
inference. Exact byte-level replay is not required for that workload.

Any controlled A/B coordinate whose interpretation depends on matching the
prompt, GGUF/quantization, generation seed, samplers, runtime, MNEME/SAA state,
or reasoning setting **must disable prompt-cache reuse**. Send
`cache_prompt=false` to the server, or use the pinned CLI/server equivalent
(`--no-cache-prompt`). Keep the Gemma generation seed separate from the SAA
`field_seed` and control both independently.

The October 2 diagnostic classification is
`LLAMA_CPP_PROMPT_CACHE_BATCH_PATH_LIMITATION`. With caching enabled, the
resident server can process the first request through a full prompt path and
later requests through a cached-prefix path. Those paths may use different
batch shapes and produced different seeded outputs. With caching disabled,
repeated CUDA stochastic generation was byte-identical under the tested
configuration. The generation seed was forwarded and functioning correctly;
CUDA itself was reproducible in the no-cache test.

Before dispatching sensitive matched-seed work:

1. Disable prompt caching.
2. Freeze the intended prompt, model, sampler, runtime, MNEME/SAA state, and
   seeds.
3. Submit one identical duplicate coordinate.
4. Confirm byte-identical output bytes.
5. Stop and diagnose if the duplicate differs; do not attribute later
   differences to the treatment.

Reasoning ON/OFF studies must verify replay within each condition before
interpreting differences between conditions. No global service setting is
implied by this note.

See the [human-readable diagnostic receipt](../receipts/MNEME_Local_Gemma_Determinism_Diagnostic_20261002.md)
and its [machine-readable measurements](../receipts/MNEME_Local_Gemma_Determinism_Diagnostic_20261002.json).
