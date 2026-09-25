from __future__ import annotations

from mneme.extraction.specialist import (
    SPECIALIST_EXTRACTOR_VERSION,
    observations_to_minimal_payload,
    observations_to_residue_payload,
    parse_gliner_relations,
)


def _payload() -> dict[str, object]:
    return {
        "relation_extraction": {
            "retains": [
                {
                    "head": {"text": "soil", "start": 4, "end": 8},
                    "tail": {"text": "moisture", "start": 29, "end": 37},
                    "confidence": 0.91,
                },
                {
                    "head": {"text": "soil", "start": 4, "end": 8},
                    "tail": {"text": "moisture", "start": 29, "end": 37},
                    "confidence": 0.90,
                }
            ],
            "invented_relation": [
                {
                    "head": {"text": "soil", "start": 4, "end": 8},
                    "tail": {"text": "moisture", "start": 29, "end": 37},
                    "confidence": 0.88,
                }
            ],
        }
    }


def test_specialist_spans_are_verified_and_deduplicated() -> None:
    text = "The soil will slowly wick up moisture as needed."
    extraction = parse_gliner_relations(
        _payload(), {"s0": text}, model="fastino/gliner2.5-base-v1", model_revision="rev"
    )
    assert extraction.version == SPECIALIST_EXTRACTOR_VERSION
    assert len(extraction.observations) == 2
    retains = next(item for item in extraction.observations if item.relation == "retains")
    assert retains.subject == "soil"
    assert retains.object == "moisture"
    assert retains.evidence_start == 4
    assert retains.evidence_end == 37
    assert retains.score == 0.91


def test_bad_span_is_rejected_itemwise() -> None:
    payload = _payload()
    payload["relation_extraction"] = {
        "retains": [
            {
                "head": {"text": "not soil", "start": 4, "end": 8},
                "tail": {"text": "moisture", "start": 29, "end": 37},
                "confidence": 0.99,
            }
        ]
    }
    extraction = parse_gliner_relations(
        payload, {"s0": "The soil will slowly wick up moisture as needed."}, model="m"
    )
    assert extraction.observations == ()


def test_downstream_forwarding_preserves_raw_relation_and_rejects_unsupported() -> None:
    text = "The soil will slowly wick up moisture as needed."
    extraction = parse_gliner_relations(
        _payload(), {"s0": text}, model="m"
    )
    payload, decisions = observations_to_minimal_payload(
        extraction, {"s0": text}, supported_relations=frozenset({"retains"})
    )
    assert payload["relationships"] == [
        {
            "from": "soil",
            "relation": "retains",
            "to": "moisture",
            "source": "s0",
            "evidence": "soil will slowly wick up moisture",
        }
    ]
    assert any(d["kind"] == "unsupported_specialist_relation" for d in decisions)


def test_digest_is_independent_of_observation_insertion_order() -> None:
    text = "The soil will slowly wick up moisture as needed."
    first = parse_gliner_relations(_payload(), {"s0": text}, model="m")
    payload = _payload()
    payload["relation_extraction"] = {
        "invented_relation": payload["relation_extraction"]["invented_relation"],
        "retains": payload["relation_extraction"]["retains"],
    }
    second = parse_gliner_relations(payload, {"s0": text}, model="m")
    assert first.content_digest == second.content_digest


def test_residue_bridge_forwards_variable_observation_count() -> None:
    text = "The soil will slowly wick up moisture as needed."
    extraction = parse_gliner_relations(_payload(), {"s0": text}, model="m")
    payload, _ = observations_to_residue_payload(
        extraction,
        {"s0": text},
        supported_relations=frozenset({"retains"}),
        episode_id="episode",
    )
    assert payload["episode_id"] == "episode"
    assert len(payload["edge_candidates"]) == 1
    assert payload["edge_candidates"][0]["relationship"] == "retains"
    assert payload["edge_candidates"][0]["context"] == ["specialist_score=0.910000"]
