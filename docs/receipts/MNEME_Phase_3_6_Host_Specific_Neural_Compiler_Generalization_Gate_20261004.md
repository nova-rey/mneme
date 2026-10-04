# MNEME Phase 3.6 — Host-Specific Neural Compiler Generalization Gate

**Disposition: NOT TESTABLE WITH CURRENT RESOURCES.**

Plainly: a compiler that turns a new semantic description into a useful Gemma
control vector is a real research direction, but the MSI cannot perform the
smallest honest version of the published approach. The one local approximation
that fits physically would be too small and too dependent on individually made
reference vectors to establish that Gemma's steering geometry has been learned
rather than merely compressed or retrieved. No MNEME state was loaded or
changed.

This is a feasibility/design gate, not a failed semantic-steering result. It
does not improve, rerun, or reinterpret the Phase 3.5 harbor experiment.

## What the audit found

| Method | Description to unseen intervention? | Role in this gate |
| --- | --- | --- |
| [HyperSteer](https://arxiv.org/abs/2506.03292) / [AxBench](https://github.com/stanfordnlp/axbench) | Yes. A hypernetwork receives steering text, optionally prompt and host activations, and is evaluated on withheld steering descriptions. | Closest direct precedent. |
| [PSR / Steer Like the LLM](https://proceedings.mlr.press/v306/heyman26a.html) | No. It learns a direction and position coefficients for an already selected target. | Later application-strength reference only. |
| [RepE](https://arxiv.org/abs/2310.01405) / [repeng](https://github.com/vgel/repeng) | No. Contrast pairs produce one vector for one target. | Reference-vector and nearest-vector baseline. |
| [UCVG.cpp](https://github.com/Egor4More/ucvg.cpp) | No. It constructs and applies per-trait vectors. | Construction/application reference, not a compiler. |

HyperSteer is therefore the only reviewed system that directly asks the Phase
3.6 question. Its published training uses about 16,000 concepts, a held-out
Concept500 split, frozen Gemma-2 hosts plus a trainable truncated host, PyTorch,
Transformers and pyvene intervention hooks. The paper reports training on one
A100 80GB. The released AxBench implementation is Gemma-2-specific; porting it
to Gemma 4 is an implementation project, not a package-install option.

The current deployed host is an exact Q2 GGUF on llama.cpp. Training on a BF16
Hugging Face Gemma 4 and deploying into this Q2 representation would introduce
an unqualified host-space mismatch. A safe evaluation would construct and apply
reference vectors on the exact Q2 host, even if a future compiler uses a
separate frozen text encoder for its portable description input.

## Current runtime and resource map

Observed on `brokeass-msi` on 2026-10-04:

- 61 GiB RAM available; NVIDIA RTX 3060 Laptop GPU with 6,144 MiB VRAM, 5,806
  MiB free; 59 GiB free local disk.
- Exact host: `google/gemma-4-E4B-it`,
  `gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`, SHA-256
  `79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`.
- Pinned CUDA llama.cpp: `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`,
  `0.5.0-dev` build 1.
- No Torch, Transformers, Accelerate, pyvene, SentenceTransformers, or Gemma 4
  HF weights were present.

The resident hardware can generate exact-GGUF contrast vectors and run bounded
inference. It cannot hold an 8B BF16 Gemma 4 plus activations and a trainable
HyperSteer-style truncated host. Installing an unrelated benchmark stack would
not change that memory boundary.

## Gemma 4 control-vector capture correction

### Observed

Gemma 4 builds one `l_out` callback for each layer `0..41`. The pinned adapter
creates no layer-zero tensor and maps `direction.N` to layer `N`, for
`N=1..41`. The generic generator instead assumed that it would see exactly
`n_layer - 1` callbacks and did not retain callback layer identity. This is why
the original generator saw 42 captures and asserted while allocating 41 output
directions.

### Correct isolated mapping

The disposable Phase 3.6 build omits the layer-zero `l_out` callback during
vector construction. It leaves layers `1..41` in order, which maps directly to
the runtime's `direction.1..direction.41` contract. This is a construction-tool
patch only; it was not applied to the resident llama.cpp source, server, or
MNEME runtime.

The isolated CUDA generator processed four ordinary contrast pairs and emitted
all 41 expected directions without an assertion. The output vector SHA-256 is
`ed0517f46fb46da6f065f7eb1abb119ec7d9e17f438ad701e501dc63babee1ad`.
The smoke build used a logically equivalent isolated patch with SHA-256
`6bb54f034c786274c098bf2d1729d76abf5a6a95369e697278265112648ab3a8`.
The committed, reproducible patch has SHA-256
`f472b6ffbb5403bb37abfbbf4a2e08b4326fcdb0412df540948676b616db227e`;
both omit only the layer-zero callback.
Raw smoke artifacts remain outside Git at
`/home/nyx/mneme_artifacts/phase36-neural-compiler-20261004/`.

### Consequence for Phase 3.5

Phase 3.5 remains valid evidence that a static vector can alter the exact host.
It remains **INCONCLUSIVE** for harbor semantics. Its ad hoc capture workaround
did not retain a layer-indexed capture record, so it cannot establish that its
41 retained tensors had the corrected `1..41` alignment. This gate does not
change Phase 3.5's disposition or artifacts.

## Smallest scientifically meaningful future experiment

This is the proposed protocol, frozen only after an owner approves compute.

1. Predeclare 24 diverse training targets across affective, interpersonal,
   abstraction, resource, temporal, uncertainty, cooperation, structural,
   complexity, and evidence framings. Use at least six varied contrast contexts
   per target on the exact Q2 host.
2. Predeclare six genuinely held-out targets, including a relational/structural
   target. They may not be lexical variants, trivial opposites, or near
   paraphrases of training targets.
3. Construct each reference vector on the corrected exact-Q2 capture path.
   Hold the layer range fixed at 1–41. Qualify a small global gain range before
   held-out evaluation; never tune gain per held-out result.
4. Fit a small description-embedding to low-rank vector-coefficient model. The
   decoder basis is learned from training vectors only. No held-out vector or
   target text is available during fitting.
5. On unseen prompts, compare no intervention, compiler vector, independent
   held-out bespoke vector, norm/layer-matched random vector, and nearest
   training-vector retrieval. Use reasoning ON, `cache_prompt=false`, matched
   seeds, at least two contexts and two seeds per held-out target.

The primary outcome is target-specific, cross-context behavior that exceeds both
random perturbation and nearest-vector retrieval while preserving competence.
Cosine similarity to a bespoke vector is diagnostic only: multiple directions
can steer a behavior.

The small 24/6 proposal is a falsification screen, not a reproduction of
HyperSteer's scaling claim. It was deliberately **not** run locally: before a
semantic reference-vector corpus exists, a low-rank fit can only show that it
compresses those labels. A negative result would be ambiguous between an
undersampled label space and lack of compiler generalization; a positive result
would still need the published-scale replication. Running it merely to avoid a
GPU request would weaken the stated question.

## Required compute for the full gate

A concrete next experiment needs one A100 80GB-class GPU, at least 200 GB
scratch storage, and the exact BF16 Gemma 4 weights plus a Gemma-4-specific
activation/intervention port. A conservative envelope is 48–72 GPU-hours:
roughly 8 hours for verified host/hook and target-corpus qualification, 24–48
hours for compiler training/evaluation, and retained checkpoints. At Runpod's
published A100 80GB Secure Cloud rate of $1.59/hour, that is approximately
$76–$115 for GPU time, plus storage and any egress. Availability and price must
be rechecked immediately before any rental. No cloud resource was created.

## Scaling implication and recommendation

If a held-out compiler beats the random and retrieval baselines, moving MNEME to
another host would require a new bounded host-specific compiler calibration and
training run. If it does not, each novel association would still need individual
vector discovery, which is effectively a vector dictionary and fails the
architecture requirement.

**Recommendation: perform one specifically justified follow-up, but only after
owner approval for the A100 80GB experiment above.** Do not integrate neural
influence into MNEME, train from MNEME history, load ON-30, or alter SAA before
that gate produces a held-out result.

## Evidence boundaries

Observed: runtime resources, missing PyTorch/HF stack, exact host fingerprints,
the Gemma 4 callback/adapter layer contract, and corrected 41-direction capture.

Inferred: Phase 3.5's unindexed workaround was not enough to prove correct
layer alignment; a BF16-to-Q2 compiler would require a separate equivalence
qualification.

Unresolved: whether corrected exact-Q2 bespoke vectors have reliable semantic
transfer across a varied target set, and whether a learned compiler will beat
retrieval for genuinely unseen descriptions.
