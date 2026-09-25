# P2.3 specialist reinterpretation of immutable balcony transcript

Date: 2026-09-25  
Status: **derived measurement; historical v5 result unchanged**

This receipt records a versioned reinterpretation of the twelve accepted v5
conversation episodes. It does not modify the v5 transcript, its FakeHost
interpretations, its `NOT_DEMONSTRATED` receipt, or its learner state. The
replay used a copied SQLite store and cloned episode/source coordinates so the
original store remained untouched.

## Instrument

- extractor contract: `gliner2.5-base-v1-relations-v1`
- model: `fastino/gliner2.5-base-v1`
- model revision: `b0c10b23313ec3ff028821dff298dd743e010706`
- source-span model file SHA-256:
  `7274094de2e0c2a37a386f55fc4e23061a954da5bd7a335e7dfe56f2743c277a`
- runtime: local MSI GS66 Stealth 11UE, GLiNER2.5 CPU instrument
- semantic assessor: existing production Qwen assessor contract `p2-assessor-v6`
  (six bounded calls for episodes with admitted candidate edges)
- raw specialist observations: [JSONL receipt](MNEME_P2.3_v5_specialist_gliner2.5_base_raw_20260925.jsonl)
- parsed/admission record, including each immutable source text:
  [JSON receipt](MNEME_P2.3_v5_specialist_parsed_20260925.json)
- assessor requests/results and validation outcomes:
  [JSON receipt](MNEME_P2.3_Specialist_Reinterpretation_Assessment_20260925.json)
- derived learner/graph trace:
  [JSON receipt](MNEME_P2.3_Specialist_Reinterpretation_Trace_20260925.json)

The specialist returned 82 raw source-grounded observations across the 66
source rows. Ten observations used an already supported downstream relation
kind and were forwarded; unsupported raw labels were retained as rejected
items. The adapter independently verified every returned source span and
deduplicated exact duplicates. It did not ask the model for MNEME IDs, routes,
provenance, or learner state.

## Episode-level disposition

| v5 episode | raw rows | raw observations | forwarded/admitted edges | semantic assessment | learner credit |
| ---: | ---: | ---: | ---: | --- | --- |
| 0 | 2 | 9 | 2 | one current-input echo, one unknown | none |
| 1 | 4 | 9 | 2 | one current-input echo, one absent | none |
| 2 | 6 | 9 | 2 | one current-input echo, one absent | none |
| 3 | 6 | 9 | 2 | assessor result rejected for correspondence on a non-present row | none |
| 4 | 6 | 5 | 1 | one external-supported occurrence | `D=80,000` |
| 5 | 6 | 2 | 0 | no candidate edge | none |
| 6 | 6 | 1 | 0 | no candidate edge | none |
| 7 | 6 | 14 | 0 | no candidate edge | none |
| 8 | 6 | 8 | 1 | assessor result rejected at evidence validation | none |
| 9 | 6 | 6 | 0 | no candidate edge | none |
| 10 | 6 | 1 | 0 | no candidate edge | none |
| 11 | 6 | 9 | 0 | no candidate edge | none |

The exact proposals, source quotations, rejection reasons, and assessor
responses are in the linked machine-readable receipts. Representative raw
labels include `retains`, `related`, `part_of`, and `prevents`; unsupported
labels such as `holds`, `maintains`, `provides`, and `shades` remain rejected
rather than silently coerced by this instrument.

## Measurement/consolidation conclusion

The specialist instrument did not remain empty: it produced grounded candidate
observations and six semantic-assessor calls completed, four validating and two
failing closed. The normal publication boundary created a derived graph and
learner ledger, but only one external-supported observation earned positive
credit (`A=80,000`, `S=20,000`). Repeated candidate edges were classified as
model-output/current-input echo or absent, so they did not earn independent
credit. No new consolidation transition occurred in the specialist-derived
scope. This is **Outcome B** for the reinterpretation: meaningful observations
were extracted, but the existing semantic/provenance path did not yield
separated qualifying support for consolidation.

The old v5 result remains `NOT_DEMONSTRATED` for the instrument actually used
there. This derived result shows that the previous empty-set result was an
instrument failure, while also showing that candidate extraction alone is not
sufficient to establish developmental support.

No matched-twin behavioral A/B was run. The derived state contained no
consolidated association and no cleanly established repeated qualifying support
that could be attributed to the new instrument; running a readout here would
risk treating one isolated credited observation as an experimental treatment.
That is a measurement limitation, not a claim of no behavioral effect.

## Integrity and accounting

- historical v5 conversation and receipts: unchanged;
- derived SQLite replay: `/tmp/mneme-p23-specialist-assessed-20260925/subjects.sqlite3`;
  SHA-256 is recorded in the trace JSON;
- new semantic-assessor calls: 6; no new Gemma or Qwen conversation calls;
- credentials and authorization headers: excluded;
- no historical interpretation was overwritten;
- no Phase Three work began.
