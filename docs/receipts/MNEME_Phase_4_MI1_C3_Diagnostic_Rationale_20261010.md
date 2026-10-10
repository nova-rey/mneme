# Phase 4 MI1 C3 diagnostic rationale

This is a pre-generation diagnosis and frozen task/exposure diagnostic, not an MI1 pass and not scored Test A/B/C evidence. It preserves the earlier calibration outcomes unchanged.

## What the earlier outcomes distinguish

The earlier `visible-calibration-20261010.json` records 8/8 correct visible-bank outputs on four short, one-target rule chains. Its model hash, llama.cpp commit, reasoning mode, cache setting, and sampler match the later calibration lineage. The C1/C2 frozen tasks were materially harder: several candidate targets, disconnected incoming edges, and different relation verbs (including “makes available,” “unlocks,” “enables,” “releases,” “prepares,” and “permits”). C2 then reached 2/6 visible positives, with misses including a shortened path, a false reachability claim from an inactive source, and an invented edge. C1/C2 attached requests also loaded the intended parsed-bank fingerprint on all inspected coordinates. The evidence therefore does not point to model/runtime drift or bank misbinding; it does show that C1/C2's visible positive control mixed side-memory qualification with harder rule-following and target-selection demands.

That is a plausible confound, not proof that fixture difficulty caused every miss. The prior latent 0/6 results remain exploratory because their visible positive control did not qualify. Numeric prefill attention remains evidence of access only, not generated semantic uptake.

## Frozen C3 diagnostic

C3 reuses the four exact earlier 8/8 visible fixtures and their directed-rule task form. For each fixture and each of two prior deterministic seeds it freezes:

- no-bank control;
- visible-bank positive control;
- sparse/moderate latent bank;
- broad/moderate latent bank;
- broad/strong latent bank.

This creates 40 matched coordinates. The simplest fixture adds two generic-memory-cue diagnostic conditions (no bank and broad/strong latent bank, each with two seeds), for 44 total coordinates. Cue coordinates are explicitly excluded from primary efficacy evidence. The main latent conditions contain no memory instruction or bank text in the recipient prompt. Bank action is explicitly cleared before no-bank and visible-text coordinates; attachment requires the exact frozen source/configuration variant and the expected server-parsed bank fingerprint.

Scoring requires the named target and the complete labeled directed path in the final answer; `unknown` is required for no-bank cases. Every scheduled coordinate, including failed or not-run calls, remains in the denominator. C3 is designed to separate task-control difficulty from side-bank strength and generic bank cueing. It does not by itself complete Test A/B/C or held-out confirmation.

The frozen plan is [MNEME_Phase_4_MI1_C3_Calibration_Freeze_20261010.json](MNEME_Phase_4_MI1_C3_Calibration_Freeze_20261010.json), SHA-256 `4412f28877996850339de441b2fb95536858af6686326ed3cfaaa0ea0dd4809f`. It binds the parent C2 plan, C2 receipt, and earlier visible-calibration receipt by hash. No C3 inference is represented in this rationale.
