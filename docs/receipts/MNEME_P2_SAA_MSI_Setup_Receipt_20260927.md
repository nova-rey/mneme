# SAA local inference host setup receipt

Initial preflight before live execution resolved the user-authorized local host as:

- hostname: `brokeass-msi`
- SSH user: `rey`
- endpoint used by the existing harness: `100.115.208.48`
- OS/kernel: Ubuntu headless Linux, `7.0.0-34-generic`
- GPU: NVIDIA GeForce RTX 3060 Laptop GPU, 6144 MiB
- driver: `595.91.07`
- RAM/swap: 3.2 GiB / 3.5 GiB
- root disk: 98 GiB total, 60 GiB free at preflight
- local Gemma: `google/gemma-4-E4B-it`, `gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`, llama.cpp
- local extractor: `fastino/gliner2.5-base-v1`
- local assessor: `cross-encoder/nli-deberta-v3-xsmall`, revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`, CPU

During r4 at `2026-09-27T02:20Z`, the host closed the SSH connection during local NLI assessment and became offline in Tailscale. Subsequent IPv4/IPv6 SSH and Tailscale probes timed out. No host modification or power-cycle was attempted; recovery requires the existing machine/network to return before another local run can be validly started.
