# Native reasoning control evidence

Read-only Library review of pinned llama.cpp revision
`4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`, 2026-10-02:

* [Request precedence](https://github.com/ggml-org/llama.cpp/blob/4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0/tools/server/server-common.cpp#L1319): request thinking flag overrides service default, then effort:none disables thinking. Remove that OFF flag rather than invent an unsupported Gemma effort level.
* [Separated output parser](https://github.com/ggml-org/llama.cpp/blob/4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0/tools/server/README.md#L1318): deepseek exposes reasoning_content separately; none emits raw content.
* [Total generation budget](https://github.com/ggml-org/llama.cpp/blob/4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0/tools/server/server-context.cpp#L457) includes reasoning. Fixed2048 total is required to permit the treatment. No separate reasoning budget or forced termination is introduced.
* [Usage metadata](https://github.com/ggml-org/llama.cpp/blob/4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0/tools/server/server-task.cpp#L365) reports aggregate completion tokens; unavailable reasoning-token breakdown stays null.

Live API before execution exactly matches prior model path/alias, ftype, build,
chat template, total slots and default generation settings. Same-day prior physical
GGUF SHA256 is `79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`.
Fresh remote file hashing was unavailable (SSH authentication rejected); this is
continuity evidence, not a fresh physical checksum claim. No runtime mutation.
