# MNEME P2.3 Local NLI Assessor Qualification

Date: 2026-09-26  
Status: **QUALIFIED FOR PROSPECTIVE P2.3 ASSESSOR USE**  
Historical Qwen assessor receipts: unchanged

This receipt records the first real pinned local specialist qualification. It does
not reclassify the earlier Qwen/Qwen3-235B HTTP-429 stops and does not claim a
behavioral A/B result.

## Binding and host

- Adapter: `p2-local-nli-deberta-v3-xsmall-v1`
- Model: `cross-encoder/nli-deberta-v3-xsmall`
- Hugging Face revision: `a150876415327c80daeff35ca6f68f5ed8cf5c24`
- Config SHA-256: `8d9f07bf7ba54a6fc3b1962483056f94c39dcf188db4cf61843e1c88f94b2342`
- Snapshot manifest SHA-256: `01935707184d31d6f6862e320a0b20d8f39036e12962ed46055ffebdc40524ea`
- Runtime: `torch 2.14.0+cpu`, `transformers 4.57.6`, CPU-only
- Execution host: `brokeass-msi` (NVIDIA RTX 3060 Laptop GPU, 6144 MiB, driver `595.91.07`; GPU was not used for NLI)
- Host memory reported: 3,368,780 KiB
- Source window: 1,800 characters with 200-character overlap; tokenizer max length 512
- Thresholds: entailment/contradiction `0.60`, winning-class margin `0.10`

The local model scores premise/hypothesis pairs. MNEME software remains
responsible for source availability, lossless windows, score aggregation,
coverage, exact evidence binding, correspondence, and serialization into the
existing `p2-assessor-v6` contract. It emits no provenance or learner credit.

## Production-shaped qualification

The frozen Q1/Q2/Q3 contract passed through the same adapter and validator used
by the prospective runner:

| Case | Result | Key checks |
|---|---|---|
| Q1 | PASS | latch supported/affirmed; model echo supported with `s0` correspondence; unrelated proposition absent |
| Q2 | PASS | rain-jacket proposition absent; supplied shade-memory relation supported and `exposure_linked` |
| Q3 | PASS | dial proposition contradicted/negated; unavailable model-output source remains unknown |

Qualification calls were local MSI inference calls, not DeepInfra provider
calls. The adapter returns unknown usage for local inference; no usage was
invented.

## Held-out semantic qualification

A separate ten-item held-out set, frozen before this run, covered direct
entailment, paraphrase, explicit negation, uncertainty, irrelevant lexical
overlap, future intent, multiple source material, absent relation, and reported
failure. All 10/10 expected semantic dispositions matched. The two
co-mentioned-but-unrelated cases were correctly retained as `present /
unsupported`, which is the existing contract's addressed-but-not-supported
state and cannot enter developmental support.

Confusion accounting: supported 4/4, contradicted 3/3, unsupported 2/2,
absent 1/1, unknown 1/1. False supported dispositions: 0. False contradicted
dispositions: 0. No item was accepted solely from lexical overlap without a
relation cue or NLI support.

## Performance

A single remote helper process loaded the pinned CPU model and scored 14 pairs
in 4.423 seconds (3.165 pairs/second, including process/SSH overhead). The
qualification calls completed in 13.909 s (Q1), 10.224 s (Q2), and 3.453 s
(Q3); missing-source Q3 did not invoke model scoring. This is adequate for the
small bounded P2.3 assessor schedule and avoids VRAM contention with local
Gemma/GLiNER.

## Boundary and continuation

The local specialist is now the pinned assessor for the prospective shared-
Interloper runner. The already-qualified `Qwen/Qwen3-30B-A3B` remains the shared
Interloper; the historical `Qwen/Qwen3-235B-A22B-Instruct-2507` assessor
failures remain reference evidence only. No behavioral calls, treatment
exposure, or A/B comparison were made during this qualification.
