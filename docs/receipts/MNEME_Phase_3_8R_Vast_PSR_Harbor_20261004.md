# Phase 3.8R — Vast PSR Harbor Experiment

**Could PSR reproduce the known harbor prompt’s influence without harbor text at evaluation time?** **NO.** On both frozen evaluation contexts, the trained Focused/PSR intervention produced byte-identical output to the no-intervention baseline. The explicit text-C anchor, in contrast, explicitly evaluated the harbor analogy.

This is a bounded negative result for this one small HF-surrogate PSR configuration. It does not establish equivalence to, or failure of, the deployed Q2 llama.cpp host.

## Strongest comparison

On the tool-lending prompt, baseline and PSR both begin by enumerating ordinary inventory, loan-tracking, reminder, and visibility requirements. Their entire 4,125-byte raw outputs have the same SHA-256 prefix, `5510978bfd489b3c`; PSR-off restoration is identical too. Text-C instead says it will evaluate the “Harbor/Tides/Docking Windows” analogy and maps it into the requested design. The evaluation request for baseline/PSR contained none of the prohibited harbor terms.

The unrelated clinic-room prompt gives the same result: baseline, PSR, and PSR-off restoration are all the same 4,094-byte output (`e5c8fa6ef32e3248…`). Text-C explicitly evaluates the harbor analogy. The untrained control changed prose in both contexts, demonstrating that a generic intervention can perturb generation; it did not establish harbor-specific transfer.

## Method and controls

- Host: `google/gemma-4-E4B-it` HF revision `ee0ef6023621cff504d758262d4e04895a5af4a2`, BF16 text model (42 layers, hidden size 2560), Transformers `5.19.0.dev0`, Torch 2.6.0+cu124, CUDA 12.4.
- This is a HF/PyTorch research surrogate, not an assertion of exact equivalence to the local Q2 GGUF/llama.cpp deployment.
- PSR implementation: Nokia Bell Labs `steer-like-the-llm` commit `3d916c618d146c5d657f055e432a432b0fa493c6`; Focused intervention at physical layer 21; published prompt-steering-imitation (`psi`) residual-MSE objective; 4 matched harbor-treated training tasks, 12 epochs, LR 0.003.
- Training loss fell from **5.74** to **4.25**. Intervention parameters changed; a base-model fingerprint stayed unchanged. Checkpoint reload reproduced its sanity generation.
- Frozen evaluation: tool lending and an unrelated shared diagnostic-room problem. Each used one matched seed and five conditions: baseline, text-C anchor, trained PSR, PSR-off restoration, and matched untrained Focused control. Non-text-C evaluation prompts were checked for `harbor`, `tide(s)`, `dock(ing)`, `port`, and `maritime`.
- Complete raw outputs are preserved in the external artifact; this report does not claim a separately parsed reasoning channel because this HF response format emitted the model’s `thought` content in the retained raw text rather than a distinct tagged field.

## Disposition

`NO — METHOD FAILURE FOR THIS BOUNDED CONFIGURATION.` The intervention trained and reloaded, but no harbor-derived structure entered the two held-out deliberations beyond baseline. Further PSR or neural-steering work requires fresh authorization; this result does not authorize MNEME/SAA integration.

## Evidence and rental closure

Canonical local artifact: `/home/nyx/mneme_artifacts/phase38r-psr-harbor-20261004-r1`.

Key verified artifact hashes:

- `r3/training.json`: `fb9fd5cf0818927b858a2a59223ae87ad87c129caa97eca4c20eafa462447711`
- `r3/checkpoint-reload.json`: `10668938bf5c7de4820180087e7c747a5eb7c25df9f5aca7efb35d8d631bfb04`
- `r6/evaluation.json`: `4460b90da6a5d613e121a43fba8ea763b5eaa5ece13dedaac45e2ab4d9d304e3`

The 24 GB RTX A5000 rental was destroyed after transfer and hash verification. `vastai show instances --raw` returned `[]`; a direct instance query returned `{"instances": null}`. It ran for approximately 16 minutes at $0.2445555556/hour, for an estimated GPU charge of about **$0.07**.
