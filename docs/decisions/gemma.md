# Canonical Gemma host decision

MNEME P0.1 now targets Google's instruction-tuned checkpoint `google/gemma-4-E4B-it` on
Hugging Face. The base `google/gemma-4-E4B` and `-it` repositories are distinct checkpoint
repositories with distinct histories. The `-it` repository includes Google's canonical
Gemma 4 chat template and is the appropriate conversational host. A provider, runtime,
quantization, device, and revision remain separate fingerprint fields.

Reference local checkpoint resolved 2026-09-17:

* repository: `google/gemma-4-E4B-it`
* immutable revision: `ee0ef6023621cff504d758262d4e04895a5af4a2`
* `model.safetensors` SHA-256/LFS OID: `cfbd3d2f1cd71bd471c37fe2bf8546d5028d41e5736f64e1ca6c6b8893125503`
* tokenizer and chat template are files in that same revision

The hosted qualification backend is DeepInfra model `google/gemma-4-E4B-it`. DeepInfra's
public model catalog exposes that name, chat tag, 131072 context length, and pricing, but
does not expose the underlying Google repository commit or weight digest. Therefore MNEME
records the relationship as same named upstream instruction-tuned model, with exact hosted
weight equivalence unknown and unverified.

The hosted implementation advertises text generation only. Its structured JSON checks are
prompt-following qualification cases, not native schema-constrained output: `response_format`
is not forwarded because native support has not been verified. Messages are rendered by
MNEME as `mneme_fallback_transcript_v1`; this is not Gemma's tokenizer chat template and
hosted/local conversational equivalence remains unestablished. Hugging Face remains an
alternate reference backend; DeepInfra is the selected inexpensive live-qualification path.

The exact immutable revision is recorded by `GemmaHost.fingerprint()` when the provider
returns it or when `MNEME_MODEL_REVISION` is configured. The default model ID is a mutable
branch reference, so a qualification artifact without a resolved revision is explicitly
non-reproducible at the exact-weight level. Gemma terms and access permissions must be
accepted at the model provider before downloading or using the checkpoint. Local
Transformers execution is a documented extension point, not silently claimed as qualified
by this repository.
