# MSI local inference setup receipt

Date: 2026-09-25

The historical `broke-ass-laptop.local` name no longer resolved. The active
Tailscale peer was resolved and identity-checked before setup:

- hostname: `brokeass-msi`
- board: `MSI GS66 Stealth 11UE`, `MS-16V4`
- CPU: Intel i7-11800H (11th gen)
- RAM: 3.2 GiB reported by the host; swap 3.5 GiB
- GPU: NVIDIA RTX 3060 Laptop GPU, 6144 MiB, driver 595.91.07, compute 8.6
- OS/kernel: Ubuntu Server 26.04.1, x86_64, kernel 7.0.0-34-generic
- disk: 98 GiB filesystem, approximately 68 GiB free after setup
- services observed: SSH, Tailscale, NVIDIA persistence/power, and ordinary
  system services; no unrelated service was stopped or reconfigured

An isolated Python environment was created at
`/home/rey/mneme-extractor-venv`. It contains the pinned GLiNER2.5 runtime and
CPU PyTorch for the specialist benchmark. The canonical Gemma family was
installed as a quantized GGUF under `/home/rey/models/gemma4/`; no credentials
or private network configuration were stored in the repository.

The distro llama.cpp binary could not load the QAT GGUF, so current upstream
llama.cpp commit `4b1a27f` was built in `/home/rey/src/llama.cpp/build-cuda`
with CUDA 12.4 and GPU architecture 8.6. A one-turn GPU-offloaded local Gemma
smoke returned a non-empty `Hello.` response. The setup remains an explicit
laboratory dependency and is not required by ordinary CI.
