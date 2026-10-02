# Source and evidence boundary

The prior passive closure remains in `docs/experiments/meter_closure`; its pure
movement and pressure meters expose exact source text, accepted identities,
caller-declared arcs, pre-response fields and length metadata. They do not provide
comprehensive semantic equivalence. The new experiment does not alter them.

`tools/run_p23_cross_thread.py::RemoteLlamaHost` uses the resident OpenAI-compatible
endpoint and forwards seed, temperature and top-p, retaining usage and client
wall time. It drops additional sampler/cache controls and native timings. A new
isolated diagnostic transport therefore preserves full raw JSON; the production
host is unchanged. The selector reads only exact participant/Gemma text from
accepted records. It never reads SAA-bearing request context into the assessment.

The concurrent seed investigation is indexed by main commit `4cbd5c6` and
`docs/operations/MNEME_Local_Gemma_Determinism_Operations_Note_20261002.md`.
Its local diagnostic receipts report repeated resident fixed-seed output matching
5/5 with `cache_prompt=false`, while cached/full-prefix paths differed. They did
not test greedy decoding. We use explicit documented stochastic settings and
perform our own duplicate tests on the larger qualification windows. No global
runtime default is changed.

Prior diagnostic receipt hashes (not rewritten here):

* json: `1821aa956e0d081b9c9dfab32514bc50bde791e30e24ed01edbc021ebd256b1e`.
* md: `f2a05bae862d214b0d29f67ef61634727585d219736ca23ad14da6f26f903971`.

Read-only inspection of pinned llama.cpp source confirms chat-response top-level
`timings` fields in `tools/server/server-task.cpp:414–458`, and documented
`prompt_ms`, `predicted_ms`, prompt/generated/cache token counts. Missing native
timings remain unavailable. The service runs reasoning off; requests also send
`reasoning_effort:none` and `chat_template_kwargs.enable_thinking:false`.

The resident model path is `gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`; the prior diagnostic
records GGUF SHA `79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`.
The filename says UD-Q2_K_XL while server ftype says Q4_0. Runtime build is
`b1-4b1a27f` (commit `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`), context4096,
RTX3060 Laptop6GiB. The new non-inference health/props snapshot agrees; weight
identity beyond the retained local diagnostic hash is not re-inferred from a name.

Shared-host cache is a possible observer effect. Conditional Phase C runs all
conversations first, then assesses eligible recorded prefixes. Thus micro calls
cannot change a later response in the measured conversations through cache state.
This tests latency feasibility, not asynchronous production scheduling.

The old fixtures named concise-resolution are not clean convergence ground truth
at age5: V2 still says not fixed/remains unresolved then; the closure fixture pairs
not fixed with an unsupported “Resolved.” We retain this contradiction boundary
instead of silently relabeling a later non-cadence turn. Clean resolution examples
are authored and frozen in Phase A.
