# Canonical Gemma host decision

MNEME P0.1 targets the public checkpoint `google/gemma-4-E4B` on Hugging Face. The
checkpoint is the canonical model identity; a provider, runtime, quantization, device, and
revision are separate fingerprint fields. The hosted path is implemented through the
Hugging Face Inference API and is not asserted to be bit-identical to local execution.

The exact immutable revision is recorded by `GemmaHost.fingerprint()` when the provider
returns it or when `MNEME_MODEL_REVISION` is configured. The default model ID is a mutable
branch reference, so a qualification artifact without a resolved revision is explicitly
non-reproducible at the exact-weight level. Gemma terms and access permissions must be
accepted at the model provider before downloading or using the checkpoint. Local
Transformers execution is a documented extension point, not silently claimed as qualified
by this repository.
