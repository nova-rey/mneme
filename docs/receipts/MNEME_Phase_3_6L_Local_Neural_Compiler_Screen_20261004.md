# Phase 3.6L local neural-compiler screen

**Plain-English result: NO CURRENT RENTAL JUSTIFICATION.** The small local
compiler produced usable control vectors for withheld descriptions, and those
vectors behaved very differently from norm-matched random perturbations. But
they did not beat semantic nearest-vector retrieval, and the independently
constructed withheld vectors did not show a clearer target-specific effect
than retrieval or the task itself. This is a useful negative screen, not a
test of HyperSteer-scale training.

This was a host-space experiment only. It never loaded MNEME, ON-30,
CompactStore, SAA, or developmental state.

## Frozen design and cost

The exact host was `google/gemma-4-E4B-it`, GGUF
`gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`, SHA-256
`79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`,
with llama.cpp `4b1a27f`. Vector capture skipped Gemma's layer-zero `l_out`
and retained explicit directions 1–41. A six-pair pilot cost 5.14 seconds,
about 4.68 GiB VRAM, 3.49 GiB peak RSS, and 421,824 bytes per vector; the
measured projection justified the predeclared 48 training / 8 held-out corpus.

Each target used six balanced contrasts: the target description remained
present on both sides while the instruction changed from using it as an
organizing lens to treating it as unavailable. The corpus and selection were
frozen before target-vector construction. A CPU MiniLM-L6-v2 embedding
(384 dimensions, L2 normalized) drove a rank-12 ridge mapper fitted only on
the 48 training targets. Held-out vectors were constructed only after mapper
freeze.

The broad 1–41 range was selected before fitting. The early, middle,
late-middle, and broad qualification calls were all coherent, but their
target-aligned prompts did not provide defensible evidence that one narrow
range was globally better. The broad range was the predeclared mechanical
baseline.

## Held-out evaluation

The complete matrix has 72 vector/gain configurations and 289 persisted calls:
two unseen contexts × two fixed seeds for each of eight targets, with no
intervention, compiler, nearest training vector, norm-matched random vector,
and independently built bespoke vector. The four vector conditions used the
globally fixed gains 0.35 and 0.70. Generation used reasoning ON,
`cache_prompt=false`, fixed sampler settings, and a duplicate preflight that
was byte-identical.

| condition | calls | nonempty final answers | normal `stop` finishes |
| --- | ---: | ---: | ---: |
| no intervention | 32 | 32 | 32 |
| compiler | 64 | 64 | 64 |
| nearest retrieval | 64 | 64 | 63 |
| random | 64 | 52 | 44 |
| bespoke held-out | 64 | 64 | 64 |

The random baseline often collapsed into repetitive self-description or an
empty final answer. That establishes that a control vector can perturb this
host substantially; it does **not** establish semantic transfer.

The important comparison is compiler versus nearest retrieval. Across the
held-out prompts, both mostly retained the strong task-native framing and
were often indistinguishable in the relevant structure. Bespoke vectors also
produced competent answers, but usually did not make their target more
identifiable than the prompt already did. Consequently this screen found no
behavioral evidence that the learned mapper generated an unseen semantic
direction rather than a broadly benign/retrieved direction.

Examples at gain 0.70 illustrate the ambiguity. For the withheld harbor
target, compiler, nearest, and bespoke responses all proposed schedules,
visibility, and return windows for a tool library; those are already direct
solutions to the prompt. For the watershed target, all three emphasized
drainage, landscape, and staged improvements. For negative-space composition,
all three recommended hierarchy and breathing room. None supplied a clean
cross-domain signature that exceeded task-native reasoning or nearest-vector
reuse. In contrast, random vectors produced visibly degenerate answers in
the repairability, bottleneck, ecosystem, and composition contexts.

## Interpretation and recommendation

**Observed:** the exact-Q2 vector path is mechanically viable; compiler,
nearest, and bespoke interventions preserve competence far better than the
norm-matched random baseline; cache-disabled same-condition duplicate output
was byte-identical.

**Observed:** this small mapper did not demonstrate an advantage over nearest
semantic-vector retrieval on any held-out family. The reference vectors also
did not establish a strong semantic-transfer benchmark beyond the prompts'
own natural implications.

**Inference:** the immediate limitation is likely the small, highly shared
contrast-vector corpus and weak semantic identifiability of the vectors, not
proof that a larger HyperSteer-style compiler cannot generalize.

**Recommendation:** do not spend the proposed A100 budget yet. First improve
the target-vector ground-truth qualification so a withheld bespoke vector can
produce a target-specific behavioral signature that beats no-vector and random
controls. A larger mapper without that reference signal would only scale an
unresolved construction problem. This does not alter MNEME or authorize
production neural influence.

## Evidence

Raw vectors, activation construction logs, full reasoning, and full responses
remain outside Git at
`/home/rey/mneme_artifacts/phase36l-local-neural-compiler-20261004-r2`.
The complete evaluation JSON SHA-256 is
`5d412da719bf2639fbcf996cc9fff018864664cbe626aaabc3c15c76cc7212b6`.
The compact machine-readable receipt is
[MNEME_Phase_3_6L_Local_Neural_Compiler_Screen_20261004.json](MNEME_Phase_3_6L_Local_Neural_Compiler_Screen_20261004.json).
