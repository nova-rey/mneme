# MI2 pre-heldout design freeze (pending Root review)

Status: **design frozen for review; no Gemma generation performed**.

This plan tests the paper’s own representative Appendix E Quantum Mechanics process card, copied as a three-part trigger/action/trap card, against held-out original PHYSICS questions. The author’s underlying five-to-ten construction examples and anonymous code/data URL were not recoverable; we do not claim to recreate that distillation. MI1 remains a negative for its tested synthetic factual-recall task.

The paper→Gemma mapping, every exact selected question and official answer, request templates, all score criteria, token-span retention rules, Gemma GQA/SWA layer mapping, calibration selector, gain sweep, seed schedule, condition sequences, and stop rules are frozen in the companion JSON. It records the Q2 GGUF SHA, pinned llama.cpp commit, GPU, prompt-cache-off deterministic configuration, and direct/visible/latent/irrelevant/removal/reuse conditions.

Calibration uses four questions from PHYSICS-eval, disjoint from six held-out questions in PHYSICS-test. Visible guidance must show a predeclared process-score improvement before held-out analysis is allowed. Site selection and the one global bank bias can be chosen only from calibration, then must be separately frozen and reviewed by Root before any held-out/scored request. The selected calibration and held-out IDs are disjoint; the complete PHYSICS-test and PHYSICS-eval files also have zero ID overlap. Two have attach→replace→disable→reuse lifecycle checks.

**No held-out inference has been run.** The local GPU remains idle.
