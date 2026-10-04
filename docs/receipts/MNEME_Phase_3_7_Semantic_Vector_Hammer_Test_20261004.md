# MNEME Phase 3.7 — Semantic Vector Qualification Hammer Test

## Did we actually put a recognizable idea into Gemma without putting that idea in the prompt?

**No — not demonstrated.** None of the 24 balanced/robust vector screen coordinates made ecological succession, musical counterpoint, or defense in depth appear as a recognizable structure in an unrelated problem. The only full dose/control sweep, ecological succession, also remained indistinguishable from ordinary generic planning. A norm- and layer-matched random vector at high gain degraded generation instead of producing a coherent alternative framing.

The exact-Q2 mechanical path works: 41 explicit control-vector directions were constructed, loaded, and applied to reasoning-enabled Gemma. The missing result is semantic transfer.

## Strongest negative example

**Target:** ecological succession — early footholds change conditions for later organization; later structure emerges from those enabling stages.

**Unrelated prompt:** a small community radio station has declining listeners, ageing shows, a small budget, and volunteers with different interests.

| Condition | What Gemma reasoned / answered |
| --- | --- |
| No intervention | A generic recovery plan: fixed schedule, audit, content refresh, and community engagement. |
| Median vector, broad layers 1–41, gain 1.5 | The same generic recovery plan: consistency, predictability, and community connection. It did not discuss pioneers, enabling conditions, path dependence, or maturation. |
| Norm/layer-matched random vector, gain 1.5 | Three of four calls exhausted the token limit in reasoning and returned no visible answer. The fourth returned only: “The city needs to be more useful.” |

That is the decisive contrast. Stronger arbitrary perturbation can damage the host, while the bespoke candidate did not make the intended conceptual structure accessible.

## What was tested

The frozen corpus contained three targets, each with 16 balanced positive/negative contrast pairs and two unrelated evaluation prompts:

- Ecological succession
- Musical counterpoint
- Defense in depth

Each target received a balanced mean-difference vector and a coordinate-wise median aggregate of 16 per-pair vectors. Each construction used the pinned `google/gemma-4-E4B-it` Q2 GGUF, skipped capture-zero, and retained directions 1–41.

The first screen tested both construction methods across four predeclared layer ranges: 9–18, 17–29, 28–38, and 1–41. All 24 screen completions were normal, but none showed the target’s diagnostic structure. Ecological succession, first in the frozen priority order, received the full control sweep: no vector; candidate gains 0.2, 0.6, 1.0, and 1.5; norm/layer-matched random gains 0.2–1.5; and sign reversal at −0.2. Each complete condition covered two prompts and two seeds with reasoning enabled and `cache_prompt=false`.

The candidate remained generic at every positive gain and at sign reversal. Random gained no target structure; its highest gain caused three length-truncated reasoning traces without final answers. Further high-gain sign reversals were not launched after that condition sustained 86 °C GPU operation. The completed low-gain sign control remains a valid direction check, and all partial state is resumable externally.

## Why the earlier prompt set was discarded

The initial software-legacy and autonomous-agent prompts invited staged replacement and independent work streams from untreated Gemma. They were preserved as rejected pre-vector prompt qualification only. A subsequent partial replacement baseline used a fixed port and could have reached a stale disposable server; it too was preserved and rejected. Neither attempt constructed or applied a vector.

The accepted r3 baseline had 12 normal completions. It still contained generic stages, zoning, and checklists, but not the distinctive source structures required here: pioneer measures enabling later organization; autonomous lines responding at planned interactions; or distinct detection, containment, and evidence-based escalation layers.

## Counts and evidence

- 51 control-vector generator runs: 17 per target, including 16 robust-aggregation members.
- 76 behavioral completions: 12 baseline, 24 screen, 40 ecological controls.
- All matching used reasoning ON and prompt cache disabled.
- External evidence root: `/home/rey/mneme_artifacts/phase37-semantic-vector-hammer-20261004-r3` (28 MiB). It contains full requests, reasoning, outputs, vector files, server logs, incremental progress, and manifests.
- Compact machine receipt: [MNEME_Phase_3_7_Semantic_Vector_Hammer_Test_20261004.json](MNEME_Phase_3_7_Semantic_Vector_Hammer_Test_20261004.json).

The external manifest, baseline, and screen digests are recorded in the JSON receipt. Large vector and response artifacts were intentionally kept outside Git.

## Disposition

**NO — NOT DEMONSTRATED.** This does not falsify all representation engineering or published larger-scale methods. It does show that the present exact-Q2 balanced mean/median contrast construction does not provide a trustworthy semantic steering target for a neural compiler. Scaling this unresolved target construction on an A100 would not be a justified next step.

MNEME developmental state, SAA, ON-30, CompactStore, the resident inference service, and production runtime behavior were untouched.
