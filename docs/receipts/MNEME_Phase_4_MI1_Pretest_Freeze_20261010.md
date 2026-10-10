# Phase 4-MI1 visible-text calibration and synthetic-suite freeze

This receipt records the task-comprehension gate completed before any scored Memory Inception coordinate. The calibration used four separate fictional reachability cases, not any of the twelve frozen scored fixtures. Gemma received each rule bank as ordinary visible text and was asked for a keyed answer plus the complete directed path.

All 8 of 8 live generations passed the deterministic rubric: the final answer contained the expected target and every label in the answer path, and ended normally. This establishes that the host could understand this short visible-text task form; it does not establish latent-bank access.

The calls used the pinned `google/gemma-4-E4B-it` Q2 GGUF (SHA-256 `79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`), llama.cpp commit `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0` (server build `0.5.0-dev`, GNU 15.2.0), reasoning ON, `cache_prompt=false`, seed values 34031 and 34037, and temperature/top-k/top-p/min-p `0.35/40/0.90/0.05`. The host was brokeass-msi with an RTX 3060 Laptop GPU (6 GiB); the isolated calibration server used `-ngl 99 -c 8192`, with eight serial calls. Mean completion latency was 4.75 seconds; no call failed or was repaired.

The complete requests, rendered prompts, reasoning, final outputs, and raw server log are retained outside Git at `/home/nyx/mneme-artifacts/phase4-mi1/calibration/`:

- `visible-calibration-20261010.json`, SHA-256 `8e87bb6a841310e6562795cf92291807fd321d6f9aea809d6c9fa5dd838dc513`.
- `visible-calibration-20261010.server.log`, SHA-256 `e4677be2c354ca636d74aa5e749e10e9e13beaa7389147430e89bf11f019befe`.

The scored synthetic schedule is frozen in [the machine-readable fixture suite](../../experiments/mi1/fixtures/mi1_frozen_suite.json), SHA-256 `11c93e86f4c2875e4524eb86de19008fb8b1971e023e146de2766ebf71c59c79`. It contains 12 fictional paired banks with counterbalanced A/B outcomes, three distinct relational packs and nine held-out tasks, plus explicitly worded update/removal/new-bank coordinates. Test A, B, C, and the untouched confirmation reserve account for 316 generations; the authorized calibration ceiling is 120, so the total preplanned envelope is 436 of the 800-call hard cap. The eight comprehension calls count within calibration. No scored or latent-bank generation has been run.

Site selection, bank exposure/gain settings, and native duplicate-replay qualification remain pre-scored calibration gates. They must be frozen in a follow-on configuration receipt before the first scored generation. If ordinary visible-text comprehension changes under the actual fixed system/chat framing, stop and resolve it before latent evaluation.

Validation at this freeze: 15 focused fixture and bank-oracle tests pass; `git diff --check` passes. No MNEME state, SAA, learner, introspection, CompactStore, ON-30, or production inference binary was changed.
