# P1.1 corrected-contract live attempt — human-review evidence bundle

**Purpose:** expose the actual two developmental examples and the complete persisted interpretation path so a human can judge whether the examples reasonably support a connected association route.

**Disposition:** this is a sanitized review addendum for the preserved failed run. It does not change the original receipt, acceptance criterion, or historical result. No provider call was made to produce this document.

## Run identity and provenance

- Experiment: `phase-one-graph-wrapper-preview` revision `1`
- Tested software revision: `ede9d3f2f639fbac5be7d85aa48edd2dc1816b45`
- Lineage: `06fb330a-01b2-4d50-a6ef-4953aef055e0`
- Provider/model: `DeepInfra` / `google/gemma-4-E4B-it`
- Run calls: `4` (two developmental responses, two initial extractions, zero repairs)
- Persisted private lineage SQLite SHA-256: `95e32477722cb6a78362d1dd8e1baef18d4c34c7892bd47e9446c85ff92478aa`
- Persisted private live summary SHA-256: `defc75a345881b4581cb767822906423d79df9dce873460e1b6cc67a0d239d5a`
- Secrets, authorization headers, environment dumps, and unrelated conversation content are excluded.

The source strings and model outputs below are the exact synthetic/engineering content persisted by this run. Model responses ended with provider `finish_reason: length`; the displayed text therefore ends exactly where the stored response ended.

## Simple review first

**Example 1:**
- Prompt: `VRAM constrains model capacity.`
- Gemma basically said: VRAM limits or constrains model capacity; the response expanded that explanation and was truncated at the provider output limit.
- Extractor found: `vram → model_capacity (constrains)`.

**Example 2:**
- Prompt: `VRAM constrains available model capacity.`
- Gemma basically said: VRAM limits or constrains model capacity; the response expanded that explanation and was truncated at the provider output limit.
- Extractor found: `vram → model_capacity (constrains)`.

**Result:** both examples independently yielded the same directly connected `vram → model_capacity` relationship. Neither extractor response included a `route_candidates` record, so no route was accepted; the failure is recorded as zero candidate routes, not as an unresolved or disconnected pair.

## Shared extractor template

The system template below is identical for both extraction calls. The per-example source payloads follow each example.

~~~~text
Extract residue v1 as one JSON object. Use only the supplied source slots. For every supported assertion, provide evidence as an array of objects with exactly {source, evidence}, where source is the source slot and evidence is a short, exact, non-empty quotation copied verbatim from that source. Do not calculate or provide numeric offsets; MNEME resolves quotations to canonical Unicode code-point spans. If no supported candidate exists, return {}. Return raw JSON only: no Markdown fences, no introductory or concluding prose, and no comments. Never invent enum values or labels for constrained fields. The validator accepts exactly these top-level fields: store, episode_id, core_concepts, salient_phrases, observed_patterns, edge_candidates, route_candidates, declared_memories, earned_candidates, identity_candidates, developmental_observation_refs, evidence_refs, extraction_confidence, intrusion_risk_estimate. Use only the canonical record fields described below. The complete allowed concept kind vocabulary is: behavior, concept, constraint, entity, event, fact, identity, object, pattern, person, process, question, resource, strategy, style, topic, trait, value, warning. The complete allowed relationship kind vocabulary is: analogy, association, causal, caused-by, caused_by, causes, constrains, contradiction, contrast, conversational-pattern, corrects, dependency, depends-on, depends_on, enables, explains, explanation, habit, identity, part-of, part_of, reasoning-strategy, refines, related, same-as, same_as, semantic, style, supports, task-utility, temporal, user-specific, warning. There are no other concept or relationship enum values. core_concepts records require key, label, kind, evidence, and confidence; edge_candidates records require key, from, to, relationship, evidence, and confidence, with from/to equal to concept keys; route_candidates records require key, edge_keys, evidence, and confidence. Every evidence object must contain only source and evidence; do not return source_spans, start, or end. Use at most two concepts, one edge, and one route. Use only supported kinds from the vocabularies above, keep labels short, and return only the JSON object.
~~~~

## Example 1

### 1. Developmental prompt/input

~~~~text
VRAM constrains model capacity.
~~~~

Generation accounting:
~~~~json
{
  "accepted_revision": 1,
  "episode_id": "be9b3ca4-58da-4f43-8db8-e34bc2902433",
  "finish_reason": "length",
  "operation_id": "fresh-p11-episode-0",
  "parameters": {
    "max_tokens": 192,
    "temperature": 0.0
  },
  "run_id": "a62d1560-91d9-4d91-a1dc-ec390b85f4b3",
  "usage": {
    "input_tokens": 16,
    "output_tokens": 192,
    "total_tokens": 208
  }
}
~~~~

### 2. Gemma developmental response

~~~~text
This is a **fundamentally true and critical statement** in the field of modern deep learning, especially with large language models (LLMs) and complex vision models.

Here is a detailed breakdown of *why* VRAM constrains model capacity, what that means in practice, and the implications.

---

## 🧠 Why VRAM Constrains Model Capacity

VRAM (Video RAM, or GPU memory) is the high-speed memory directly on the Graphics Processing Unit (GPU). It is the primary workspace for the model during training and inference.

The constraint arises because the model's parameters, intermediate calculations, and necessary data must all fit into this finite memory space.

### 1. Storing Model Parameters (Weights)
The most direct constraint is the size of the model itself.

*   **What it is:** A large model (like GPT-3 or Llama 2) is defined by billions or trillions
~~~~

### 3. Exact source material supplied to the extractor

The extractor received these source slots. `s0` is the external developmental input; `s1` is the persisted model output above.

~~~~json
{
  "source_slots": {
    "s0": "VRAM constrains model capacity.",
    "s1": "This is a **fundamentally true and critical statement** in the field of modern deep learning, especially with large language models (LLMs) and complex vision models.\n\nHere is a detailed breakdown of *why* VRAM constrains model capacity, what that means in practice, and the implications.\n\n---\n\n## 🧠 Why VRAM Constrains Model Capacity\n\nVRAM (Video RAM, or GPU memory) is the high-speed memory directly on the Graphics Processing Unit (GPU). It is the primary workspace for the model during training and inference.\n\nThe constraint arises because the model's parameters, intermediate calculations, and necessary data must all fit into this finite memory space.\n\n### 1. Storing Model Parameters (Weights)\nThe most direct constraint is the size of the model itself.\n\n*   **What it is:** A large model (like GPT-3 or Llama 2) is defined by billions or trillions"
  }
}
~~~~

### 4. Extractor request payload

The source-slot JSON below is the exact user message sent with the shared extractor template.

~~~~text
{"source_slots":{"s0":"VRAM constrains model capacity.","s1":"This is a **fundamentally true and critical statement** in the field of modern deep learning, especially with large language models (LLMs) and complex vision models.\n\nHere is a detailed breakdown of *why* VRAM constrains model capacity, what that means in practice, and the implications.\n\n---\n\n## 🧠 Why VRAM Constrains Model Capacity\n\nVRAM (Video RAM, or GPU memory) is the high-speed memory directly on the Graphics Processing Unit (GPU). It is the primary workspace for the model during training and inference.\n\nThe constraint arises because the model's parameters, intermediate calculations, and necessary data must all fit into this finite memory space.\n\n### 1. Storing Model Parameters (Weights)\nThe most direct constraint is the size of the model itself.\n\n*   **What it is:** A large model (like GPT-3 or Llama 2) is defined by billions or trillions"}}
~~~~

### 5. Extractor returned residue

Initial attempt (raw returned JSON, pretty-printed):
~~~~json
{
  "core_concepts": [
    {
      "confidence": 1.0,
      "evidence": [
        {
          "evidence": "VRAM constrains model capacity.",
          "source": "s0"
        }
      ],
      "key": "vram",
      "kind": "resource",
      "label": "VRAM"
    },
    {
      "confidence": 1.0,
      "evidence": [
        {
          "evidence": "VRAM constrains model capacity.",
          "source": "s0"
        }
      ],
      "key": "model_capacity",
      "kind": "concept",
      "label": "Model Capacity"
    }
  ],
  "edge_candidates": [
    {
      "confidence": 1.0,
      "evidence": [
        {
          "evidence": "VRAM constrains model capacity.",
          "source": "s0"
        }
      ],
      "from": "vram",
      "key": "e1",
      "relationship": "constrains",
      "to": "model_capacity"
    }
  ],
  "extraction_confidence": 0.9
}
~~~~

- Validation status: `VALID`; validation errors: `[]`.

Repair result: no repair occurred; the initial extraction was structurally and source-valid.

### 6. Accepted concepts

~~~~json
[
  {
    "candidate_id": "c5d6e6c9-41da-45ef-9558-6b8d76fae707",
    "confidence": 1.0,
    "context_json": [],
    "interpretation_id": "8e38f96a-850b-401d-b556-89bef0749cfb",
    "kind": "concept",
    "label": "Model Capacity",
    "local_key": "model_capacity",
    "normalized_label": "model capacity",
    "salience": 0.0
  },
  {
    "candidate_id": "658bd602-5bcc-4eea-90e5-b8b4968b35c1",
    "confidence": 1.0,
    "context_json": [],
    "interpretation_id": "8e38f96a-850b-401d-b556-89bef0749cfb",
    "kind": "resource",
    "label": "VRAM",
    "local_key": "vram",
    "normalized_label": "vram",
    "salience": 0.0
  }
]
~~~~

### 7. Accepted relationships/edges

~~~~json
[
  {
    "context_json": {
      "confidence": 1.0
    },
    "edge_key": "e1",
    "evidence_json": [
      {
        "end": 31,
        "source_slot": "s0",
        "start": 0
      }
    ],
    "polarity": "asserted",
    "relationship": "constrains",
    "snapshot_id": "760003b4-594c-4778-86d8-7149bb04dd78",
    "source_key": "vram",
    "target_key": "model_capacity"
  }
]
~~~~

### 8. Alias/resolution decisions

~~~~json
[
  {
    "canonical_label": "Model Capacity",
    "created_at": "2026-09-19T21:41:51.725148+00:00",
    "decision_id": "3cce07fb-3061-431c-94ad-748f18bdfec6",
    "decision_kind": "exact",
    "evidence_json": {
      "decision": {
        "ambiguous": false,
        "canonical_key": "model_capacity",
        "input_label": "Model Capacity",
        "method": "exact",
        "normalized_label": "model capacity"
      },
      "source_spans": [
        {
          "end": 31,
          "source_slot": "s0",
          "start": 0
        }
      ]
    },
    "interpretation_id": "8e38f96a-850b-401d-b556-89bef0749cfb",
    "local_key": "model_capacity",
    "normalized_label": "model capacity"
  },
  {
    "canonical_label": "VRAM",
    "created_at": "2026-09-19T21:41:51.725148+00:00",
    "decision_id": "0db60ea7-ab75-410d-a404-b162c7b1c65c",
    "decision_kind": "exact",
    "evidence_json": {
      "decision": {
        "ambiguous": false,
        "canonical_key": "vram",
        "input_label": "VRAM",
        "method": "exact",
        "normalized_label": "vram"
      },
      "source_spans": [
        {
          "end": 31,
          "source_slot": "s0",
          "start": 0
        }
      ]
    },
    "interpretation_id": "8e38f96a-850b-401d-b556-89bef0749cfb",
    "local_key": "vram",
    "normalized_label": "vram"
  }
]
~~~~

Resolution was exact for `VRAM → vram` and `Model Capacity → model_capacity`; no alias merge, paraphrase resolution, or ambiguity was recorded. Canonical offsets were derived from the exact `s0` quotation.

### 9. Resulting graph nodes and edges

**Graph nodes in the published snapshot:**
~~~~json
[
  {
    "candidate_id": null,
    "concept_key": "model_capacity",
    "confidence": 1.0,
    "kind": "concept",
    "label": "Model Capacity",
    "normalized_label": "model capacity",
    "salience": 0.0,
    "snapshot_id": "760003b4-594c-4778-86d8-7149bb04dd78"
  },
  {
    "candidate_id": null,
    "concept_key": "vram",
    "confidence": 1.0,
    "kind": "resource",
    "label": "VRAM",
    "normalized_label": "vram",
    "salience": 0.0,
    "snapshot_id": "760003b4-594c-4778-86d8-7149bb04dd78"
  }
]
~~~~

**Graph edges in the published snapshot:**
~~~~json
[
  {
    "context_json": {
      "confidence": 1.0
    },
    "edge_key": "e1",
    "evidence_json": [
      {
        "end": 31,
        "source_slot": "s0",
        "start": 0
      }
    ],
    "polarity": "asserted",
    "relationship": "constrains",
    "snapshot_id": "760003b4-594c-4778-86d8-7149bb04dd78",
    "source_key": "vram",
    "target_key": "model_capacity"
  }
]
~~~~

### 10. Candidate routes and decision

~~~~json
[]
~~~~

No route candidate was returned by the extractor, so there was no route to accept or reject. The graph publication retained the supported edge(s), but route materialization requires an explicit route candidate.

## Example 2

### 1. Developmental prompt/input

~~~~text
VRAM constrains available model capacity.
~~~~

Generation accounting:
~~~~json
{
  "accepted_revision": 2,
  "episode_id": "9ef004b1-7012-4634-93f5-9cdb07db84df",
  "finish_reason": "length",
  "operation_id": "fresh-p11-episode-1",
  "parameters": {
    "max_tokens": 192,
    "temperature": 0.0
  },
  "run_id": "0f25ebd8-dcad-431f-b02c-54ba36526443",
  "usage": {
    "input_tokens": 17,
    "output_tokens": 192,
    "total_tokens": 209
  }
}
~~~~

### 2. Gemma developmental response

~~~~text
This is a **concise and accurate statement** that captures a fundamental bottleneck in modern deep learning, especially with large language models (LLMs) and complex vision models.

Here's a breakdown of why this is true, what it means, and the implications:

---

## Why VRAM Constrains Model Capacity

**VRAM (Video RAM)** is the high-speed memory located directly on the GPU (Graphics Processing Unit). It is the memory the GPU uses to perform the massive parallel computations required for training and running neural networks.

The "model capacity" in this context refers to several interconnected factors:

### 1. Model Size (Parameters)
* **The Problem:** Large models (like GPT-3, Llama 2/3) have billions or trillions of parameters (weights and biases). Each parameter must be stored in memory during inference or training.
* **The Constraint:** If a model has $N$
~~~~

### 3. Exact source material supplied to the extractor

The extractor received these source slots. `s0` is the external developmental input; `s1` is the persisted model output above.

~~~~json
{
  "source_slots": {
    "s0": "VRAM constrains available model capacity.",
    "s1": "This is a **concise and accurate statement** that captures a fundamental bottleneck in modern deep learning, especially with large language models (LLMs) and complex vision models.\n\nHere's a breakdown of why this is true, what it means, and the implications:\n\n---\n\n## Why VRAM Constrains Model Capacity\n\n**VRAM (Video RAM)** is the high-speed memory located directly on the GPU (Graphics Processing Unit). It is the memory the GPU uses to perform the massive parallel computations required for training and running neural networks.\n\nThe \"model capacity\" in this context refers to several interconnected factors:\n\n### 1. Model Size (Parameters)\n* **The Problem:** Large models (like GPT-3, Llama 2/3) have billions or trillions of parameters (weights and biases). Each parameter must be stored in memory during inference or training.\n* **The Constraint:** If a model has $N$"
  }
}
~~~~

### 4. Extractor request payload

The source-slot JSON below is the exact user message sent with the shared extractor template.

~~~~text
{"source_slots":{"s0":"VRAM constrains available model capacity.","s1":"This is a **concise and accurate statement** that captures a fundamental bottleneck in modern deep learning, especially with large language models (LLMs) and complex vision models.\n\nHere's a breakdown of why this is true, what it means, and the implications:\n\n---\n\n## Why VRAM Constrains Model Capacity\n\n**VRAM (Video RAM)** is the high-speed memory located directly on the GPU (Graphics Processing Unit). It is the memory the GPU uses to perform the massive parallel computations required for training and running neural networks.\n\nThe \"model capacity\" in this context refers to several interconnected factors:\n\n### 1. Model Size (Parameters)\n* **The Problem:** Large models (like GPT-3, Llama 2/3) have billions or trillions of parameters (weights and biases). Each parameter must be stored in memory during inference or training.\n* **The Constraint:** If a model has $N$"}}
~~~~

### 5. Extractor returned residue

Initial attempt (raw returned JSON, pretty-printed):
~~~~json
{
  "core_concepts": [
    {
      "confidence": 1.0,
      "evidence": [
        {
          "evidence": "VRAM constrains available model capacity.",
          "source": "s0"
        }
      ],
      "key": "vram",
      "kind": "resource",
      "label": "VRAM"
    },
    {
      "confidence": 1.0,
      "evidence": [
        {
          "evidence": "VRAM constrains available model capacity.",
          "source": "s0"
        }
      ],
      "key": "model_capacity",
      "kind": "concept",
      "label": "Model Capacity"
    }
  ],
  "edge_candidates": [
    {
      "confidence": 1.0,
      "evidence": [
        {
          "evidence": "VRAM constrains available model capacity.",
          "source": "s0"
        }
      ],
      "from": "vram",
      "key": "constrains_capacity",
      "relationship": "constrains",
      "to": "model_capacity"
    }
  ]
}
~~~~

- Validation status: `VALID`; validation errors: `[]`.

Repair result: no repair occurred; the initial extraction was structurally and source-valid.

### 6. Accepted concepts

~~~~json
[
  {
    "candidate_id": "1aa7f3ac-beed-4faf-97dc-9b0f2073caef",
    "confidence": 1.0,
    "context_json": [],
    "interpretation_id": "4de294d5-a331-4ffa-8684-8509dd51730e",
    "kind": "concept",
    "label": "Model Capacity",
    "local_key": "model_capacity",
    "normalized_label": "model capacity",
    "salience": 0.0
  },
  {
    "candidate_id": "aee42d24-f01e-4f1e-97bc-11fe2c27dd4b",
    "confidence": 1.0,
    "context_json": [],
    "interpretation_id": "4de294d5-a331-4ffa-8684-8509dd51730e",
    "kind": "resource",
    "label": "VRAM",
    "local_key": "vram",
    "normalized_label": "vram",
    "salience": 0.0
  }
]
~~~~

### 7. Accepted relationships/edges

~~~~json
[
  {
    "context_json": {
      "confidence": 1.0
    },
    "edge_key": "constrains_capacity",
    "evidence_json": [
      {
        "end": 41,
        "source_slot": "s0",
        "start": 0
      }
    ],
    "polarity": "asserted",
    "relationship": "constrains",
    "snapshot_id": "92930d98-f5ec-423a-b149-ad4117365aed",
    "source_key": "vram",
    "target_key": "model_capacity"
  }
]
~~~~

The published snapshot also retained this inherited edge from the previous interpretation:

~~~~json
[
  {
    "context_json": {
      "confidence": 1.0
    },
    "edge_key": "e1",
    "evidence_json": [
      {
        "end": 31,
        "source_slot": "s0",
        "start": 0
      }
    ],
    "polarity": "asserted",
    "relationship": "constrains",
    "snapshot_id": "92930d98-f5ec-423a-b149-ad4117365aed",
    "source_key": "vram",
    "target_key": "model_capacity"
  }
]
~~~~

### 8. Alias/resolution decisions

~~~~json
[
  {
    "canonical_label": "Model Capacity",
    "created_at": "2026-09-19T21:41:55.737992+00:00",
    "decision_id": "e85a1437-e727-4b03-9f0d-f6e6fa529ead",
    "decision_kind": "exact",
    "evidence_json": {
      "decision": {
        "ambiguous": false,
        "canonical_key": "model_capacity",
        "input_label": "Model Capacity",
        "method": "exact",
        "normalized_label": "model capacity"
      },
      "source_spans": [
        {
          "end": 41,
          "source_slot": "s0",
          "start": 0
        }
      ]
    },
    "interpretation_id": "4de294d5-a331-4ffa-8684-8509dd51730e",
    "local_key": "model_capacity",
    "normalized_label": "model capacity"
  },
  {
    "canonical_label": "VRAM",
    "created_at": "2026-09-19T21:41:55.737992+00:00",
    "decision_id": "f9905ee5-ff73-4ac9-a691-7acc33c58f4c",
    "decision_kind": "exact",
    "evidence_json": {
      "decision": {
        "ambiguous": false,
        "canonical_key": "vram",
        "input_label": "VRAM",
        "method": "exact",
        "normalized_label": "vram"
      },
      "source_spans": [
        {
          "end": 41,
          "source_slot": "s0",
          "start": 0
        }
      ]
    },
    "interpretation_id": "4de294d5-a331-4ffa-8684-8509dd51730e",
    "local_key": "vram",
    "normalized_label": "vram"
  }
]
~~~~

Resolution was exact for `VRAM → vram` and `Model Capacity → model_capacity`; no alias merge, paraphrase resolution, or ambiguity was recorded. Canonical offsets were derived from the exact `s0` quotation.

### 9. Resulting graph nodes and edges

**Graph nodes in the published snapshot:**
~~~~json
[
  {
    "candidate_id": null,
    "concept_key": "model_capacity",
    "confidence": 1.0,
    "kind": "concept",
    "label": "Model Capacity",
    "normalized_label": "model capacity",
    "salience": 0.0,
    "snapshot_id": "92930d98-f5ec-423a-b149-ad4117365aed"
  },
  {
    "candidate_id": null,
    "concept_key": "vram",
    "confidence": 1.0,
    "kind": "resource",
    "label": "VRAM",
    "normalized_label": "vram",
    "salience": 0.0,
    "snapshot_id": "92930d98-f5ec-423a-b149-ad4117365aed"
  }
]
~~~~

**Graph edges in the published snapshot:**
~~~~json
[
  {
    "context_json": {
      "confidence": 1.0
    },
    "edge_key": "constrains_capacity",
    "evidence_json": [
      {
        "end": 41,
        "source_slot": "s0",
        "start": 0
      }
    ],
    "polarity": "asserted",
    "relationship": "constrains",
    "snapshot_id": "92930d98-f5ec-423a-b149-ad4117365aed",
    "source_key": "vram",
    "target_key": "model_capacity"
  },
  {
    "context_json": {
      "confidence": 1.0
    },
    "edge_key": "e1",
    "evidence_json": [
      {
        "end": 31,
        "source_slot": "s0",
        "start": 0
      }
    ],
    "polarity": "asserted",
    "relationship": "constrains",
    "snapshot_id": "92930d98-f5ec-423a-b149-ad4117365aed",
    "source_key": "vram",
    "target_key": "model_capacity"
  }
]
~~~~

### 10. Candidate routes and decision

~~~~json
[]
~~~~

No route candidate was returned by the extractor, so there was no route to accept or reject. The graph publication retained the supported edge(s), but route materialization requires an explicit route candidate.

## Review conclusion

The two developmental examples are short, direct engineering statements about the same relation. The persisted extraction evidence supports the concepts `VRAM` and `Model Capacity` and the `constrains` edge in both examples. Exact resolution produced the same canonical keys in both snapshots. The live gate stopped because route candidates were absent from both returned residues; this bundle does not decide whether the route omission belongs to the fixture, extractor behavior, resolver, or graph policy.

## Future live-acceptance evidence practice

For every future live gate, preserve a sanitized review bundle alongside the summary receipt. The bundle must be generated from persisted records after the run and must include, for each scheduled example:

1. the exact model-visible developmental input and accepted response;
2. the exact immutable source slots supplied to extraction;
3. the exact extractor template, including all constrained vocabularies and structural limits;
4. every initial and permitted repair request/result, with validation status and errors;
5. accepted concepts, relationships, aliases/resolution decisions, canonical evidence spans, graph snapshot nodes/edges, and route candidates with acceptance/rejection reasons;
6. run/gate coordinates, tested software SHA, artifact digests, usage, and a clear redaction statement.

Raw credentials, authorization headers, environment dumps, unrelated private content, and provider metadata that can contain secrets must remain excluded. Public receipts may remain concise, but a human-review bundle must retain enough sanitized input/output material to reconstruct `developmental input → host response → extraction input → extraction output → validation/resolution → graph state → route decision`. Historical receipts must not be rewritten; this practice applies to new runs and this document is an addendum to the preserved failure receipt.
