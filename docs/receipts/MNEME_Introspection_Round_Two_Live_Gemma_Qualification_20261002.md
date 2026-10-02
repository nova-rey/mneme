# MNEME Introspection Round Two — live Gemma qualification

**Disposition: COMPLETE — live contract qualified and implemented**

This qualification used the exact local Gemma runtime on the recovered MSI host. It did not rerun P3-INTROSPECT-100 and did not use a hosted fallback.

## Runtime

- Host: `brokeass-msi` / `rey@100.115.208.48`
- Model: `google/gemma-4-E4B-it`
- GGUF: `/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf`
- GGUF SHA-256: `79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`
- Runtime: llama.cpp `0.5.0-dev`, commit `4b1a27f`
- Context: 4096; GPU layers: 99; RTX 3060 Laptop GPU, 6 GiB; host RAM about 64 GiB
- Resident service: Gemma remained loaded in VRAM on port 64170 for the qualification

All live model outputs, seeds, finish metadata, latency, and filing calls are in the [machine-readable evidence](MNEME_Introspection_Round_Two_Live_Gemma_Qualification_20261002.json).

## Contract tested

Round One was prose-only private reflection over the completed arc and recorded exposures. Round Two was a separate filing step. Python retained canonical target identity, validation, bounded numeric mapping, deduplication, and state mutation.

The six requested screening levels were all exercised with real Gemma calls over eight fixtures. Every level reached 100% first-attempt parse/schema validity on the screening set. The initial “most expressive” rule therefore selected full JSON, but the saved outputs showed a material limitation: full/compact filings frequently returned neutral or insufficient values even when Round One prose described a positive or negative outcome. Mechanical parse success was not treated as semantic qualification.

A follow-up interface, `microcall_explicit`, was then tested. It uses one-digit decisions with a visible answer bank: target choice where needed, evidence sufficiency, association usefulness, association harm/distraction, expression usefulness, expression suppression, and confidence. Contradictory binary judgments map conservatively to neutral. One-target packets resolve the sole ordinal deterministically; multi-target packets still require Gemma to choose from the supplied choices.

That contract was selected because it preserves more semantic dimensions than the compact forms while removing arbitrary JSON/alias clerical work from Gemma. It is now the default filing level in the production runner (`p3-introspection-v3-live-round-two`).

## Live measurements

| Stage | Reviews | First-attempt valid | Eventual valid | Target/legal values | Fallback | Mean calls/review | Median wall latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Six-level screening (each level) | 8 | 100% | 100% | 100% | 0% | 2.0 (microcall 5.0) | 5.3–6.2 s |
| Explicit follow-up | 8 | 100% | 100% | 100% | 0% | 7.125 | 8.49 s |
| Explicit torture qualification | 100 | 100% | 100% | 100% | 0% | 7.07 | 8.72 s |

The 100-review torture set cycles the eight archived/synthetic fixtures, including positive, negative, neutral, insufficient, competing-target, expression-only, and archived packets. It produced 707 live Round-Two/associated calls plus 100 live Round-One reflections. Across screening, follow-up, and torture, the qualification used 860 local Gemma calls. The adapter did not expose token counts for this resident endpoint; call counts and wall latency are recorded instead.

Round-One reflections were nonempty in every review; the conservative mechanical specificity check was 82% in the final torture set. This is a quality signal, not a semantic truth judge.

## Semantic fidelity boundary

The live model can reliably fill the bounded filing interface. It does not reliably produce a ground-truth introspective judgment: the saved outputs include contradictory usefulness/harm or expression-helpfulness/suppression answers, and the production mapper deliberately turns those conflicts into neutral rather than inventing a signed adjustment. The final evidence therefore supports **clerical contract reliability**, not a claim that Gemma's opinions are objectively correct.

Representative live outputs are preserved in the JSON. A positive reflection produced binary values that mapped to `association=E`; a negative reflection produced `association=A`; ambiguous and conflicting cases were retained and conservatively neutralized. No automatic semantic consistency score is being presented as a substitute for review. The earlier full-JSON screen's syntax success should not be read as semantic success.

## Implementation and delivery proof

Implemented:

- `FilingLevel.MICROCALL_EXPLICIT` and deterministic `parse_microcall_explicit`.
- Production Round One prose + Round Two explicit filing path.
- Python-owned canonical target resolution and bounded signed mapping.
- Safe fallback to the existing minimal form and safe abstention on malformed filing.
- Persistence of reflection, filing calls, fallback, seeds, and parsed proposals.
- Call-budget reservation increased to cover the explicit worst case (up to eight target checks, six field checks, reflection, and fallback per arc).

Focused tests cover positive, negative, expression-only, neutral, insufficient, malformed, conflict-safe mapping, ledger replay, and state mutation. Accepted positive/negative/neutral proposals reach the existing bounded adjustment path; deterministic tests verify the resulting SAA accessibility/expression deltas.

Historical P3 receipts remain unchanged. No developmental conversation or frozen readout was rerun.

## Validation

- Focused introspection tests: **29 passed**
- Full pytest, Ruff, strict mypy, wheel/fresh-install smoke, and CI are run after this implementation commit; their exact results and commit are reported with the final handoff.

## Evidence

- [Qualification JSON](MNEME_Introspection_Round_Two_Live_Gemma_Qualification_20261002.json)
- [Qualification harness](../../tools/qualify_introspection_live_round_two.py)
- [Production runner](../../tools/run_p3_introspection_100.py)
- [Introspection contract](../../src/mneme/development/introspection.py)

This qualification stops here. It does not rerun P3-INTROSPECT-100 or begin Phase Four.
