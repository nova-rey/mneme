from __future__ import annotations

import json

import pytest

from mneme.contracts import GenerationRequest, GenerationResult, TokenUsage
from mneme.experiments.live_accounting import summarize_lineage_usage
from mneme.hosts import FakeHost
from mneme.memory.interpretation import (
    InterpretationError,
    InterpretationIdempotencyConflict,
    InterpretationNotReady,
    InterpretationService,
    InterpretationUncertain,
    InterpretationValidationError,
)
from mneme.memory.residue import (
    RELATIONSHIP_RECONCILIATION_VERSION,
    SUPPORTED_CONCEPT_KINDS,
    SUPPORTED_RELATIONSHIP_KINDS,
    ResidueValidationError,
    normalize_relationship_items,
    validate_residue,
)
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.storage import SQLiteStore


class ResidueHost(FakeHost):
    """Fake extractor with a configurable sequence of JSON results."""

    def __init__(self, *results: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.results = list(results) or ["{}"]
        self.calls = 0

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.fail:
            raise RuntimeError("fixture host failure")
        result = self.results[min(self.calls, len(self.results) - 1)]
        self.calls += 1
        return GenerationResult(
            result,
            self.model_id,
            "builtin",
            dict(request.parameters),
            request.seed,
            TokenUsage(10, len(result.split()), 10 + len(result.split())),
            0.0,
            "stop",
            {"fixture": True},
            {"request_has_source_slots": "source_slots" in request.messages[0]["content"]},
        )


def _accepted(
    tmp_path, host: FakeHost | None = None, *, interpretation_allowed: bool = True
):
    host = host or FakeHost()
    store = SQLiteStore(tmp_path / "lineage.sqlite3")
    instance = store.create_root(
        permissions=StoragePermissions(True, True, interpretation_allowed)
    )
    continuity = ContinuityService(store, instance, host)
    operation = continuity.prepare_episode(
        GenerationRequest(({"role": "user", "content": "hello world"},))
    )
    continuity.generate_operation(operation.operation_id)
    continuity.accept_episode(operation.operation_id)
    if hasattr(host, "calls"):
        host.calls = 0
    return store, instance, operation.episode_id


def test_legacy_policy_cannot_interpret_without_explicit_opt_in(tmp_path):
    store, instance, episode_id = _accepted(
        tmp_path, FakeHost(), interpretation_allowed=False
    )
    with store:
        service = InterpretationService(store, instance, FakeHost())
        with pytest.raises(InterpretationError, match="permission"):
            service.prepare(episode_id)


def test_interpretation_persists_result_then_publishes_empty_residue(tmp_path):
    host = ResidueHost("{}")
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id, operation_id="interp-empty")
        ready = service.execute(prepared)
        assert ready.status == "RESULT_READY"
        attempt = store.connection.execute(
            "SELECT request_json,result_json,status FROM interpretation_attempts "
            "WHERE operation_id=?",
            (prepared.operation_id,),
        ).fetchone()
        assert attempt[2] == "RESULT_READY"
        request = json.loads(attempt[0])
        assert request["source_bundle"]["eligible"][0]["content"] == "hello world"
        assert json.loads(attempt[1])['content'] == "{}"
        residue = service.validate(prepared)
        assert residue.core_concepts == ()
        published = service.publish(prepared, residue)
        assert published.lineage_revision == 2
        assert published.graph_revision == 0
        assert service.publish(prepared, residue) == published
        assert store.current()["current_revision"] == 2


def test_source_purpose_filter_keeps_model_output_out_of_live_extraction(tmp_path):
    host = ResidueHost("{}")
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(
            store,
            instance,
            host,
            source_purposes=("external_evidence",),
        )
        prepared = service.prepare(episode_id, operation_id="interp-external-only")
        service.execute(prepared)
        request = json.loads(
            store.connection.execute(
                "SELECT request_json FROM interpretation_attempts WHERE operation_id=?",
                (prepared.operation_id,),
            ).fetchone()[0]
        )
        bundle = request["source_bundle"]
        assert [source["purpose"] for source in bundle["sources"]] == [
            "external_evidence",
            "model_output",
        ]
        assert [source["purpose"] for source in bundle["eligible"]] == [
            "external_evidence"
        ]
        source_slots = json.loads(request["request"]["messages"][0]["content"])
        assert list(source_slots["source_slots"]) == ["s0"]
        assert "hello world" in source_slots["source_slots"]["s0"]


def test_extraction_prompt_declares_strict_residue_record_shape(tmp_path):
    store, instance, episode_id = _accepted(tmp_path, FakeHost())
    with store:
        prepared = InterpretationService(store, instance, FakeHost()).prepare(episode_id)
        # Preparation is intentionally provider-free; the strict shape is
        # assembled at execution start, so exercise the request helper through
        # the recorded attempt by using the deterministic fixture host.
        service = InterpretationService(store, instance, FakeHost())
        service.execute(prepared)
        request = json.loads(
            store.connection.execute(
                "SELECT request_json FROM interpretation_attempts WHERE operation_id=?",
                (prepared.operation_id,),
            ).fetchone()[0]
        )
        system = request["request"]["system"]
        assert "residue-v4" in system
        assert "Return raw JSON only" in system
        assert "no Markdown fences" in system
        assert "Formatting is part of the immutable source" in system
        assert "preserve every Markdown marker" in system
        assert "no introductory or concluding prose" in system
        assert "canonical vocabulary" in system
        assert "normalize a bounded equivalent label" in system
        assert "retains" in system
        assert "core_concepts records require key, label, kind" in system
        assert "evidence, and confidence" in system
        assert '"confidence":0.90' in system
        assert "Do not calculate or provide numeric offsets" in system
        assert "Every evidence object must contain only source and evidence" in system
        assert "route_candidates are optional source-backed groupings" in system
        assert "MNEME derives bounded directed routes from accepted graph edges" in system
        assert "one contiguous substring of the referenced source slot" in system
        assert "omit that assertion instead of paraphrasing" in system
        assert "leading `* ` and both pairs of `**`" in system
        for kind in SUPPORTED_CONCEPT_KINDS:
            assert kind in system
        for relationship in SUPPORTED_RELATIONSHIP_KINDS:
            assert relationship in system
        assert request["request"]["parameters"]["max_new_tokens"] == 1536


def test_markdown_evidence_regression_requires_exact_source_formatting() -> None:
    """The historical stripped-markup quote remains rejected by strict validation."""

    source = "That's excellent! It sounds like **consistent, focused effort paid off**."
    base = {
        "core_concepts": [
            {
                "key": "effort",
                "label": "focused effort",
                "kind": "concept",
                "evidence": [{"source": "s1", "evidence": "consistent, focused effort paid off."}],
                "confidence": 0.9,
            }
        ]
    }
    with pytest.raises(ResidueValidationError, match="does not occur verbatim"):
        validate_residue(base, source_slots={"s1": source})

    base["core_concepts"][0]["evidence"][0]["evidence"] = (
        "**consistent, focused effort paid off**"
    )
    residue = validate_residue(base, source_slots={"s1": source})
    assert residue.core_concepts[0]["source_spans"] == (
        {"source_slot": "s1", "start": 33, "end": 72},
    )


def test_markdown_list_evidence_requires_bullet_and_bold_markers() -> None:
    source = "* **Reduces Evaporation:** water evaporates."
    base = {
        "core_concepts": [
            {
                "key": "evaporation",
                "label": "evaporation",
                "kind": "process",
                "evidence": [
                    {"source": "s1", "evidence": "Reduces Evaporation: water evaporates."}
                ],
                "confidence": 0.9,
            }
        ]
    }
    with pytest.raises(ResidueValidationError, match="does not occur verbatim"):
        validate_residue(base, source_slots={"s1": source})
    base["core_concepts"][0]["evidence"][0]["evidence"] = source
    assert validate_residue(base, source_slots={"s1": source}).core_concepts[0]["source_spans"]


def _observed_invalid_extractor_outputs() -> list[tuple[str, str, str]]:
    """Provider output fixtures captured during the failed live attempts."""

    def concept(kind: str) -> str:
        return json.dumps(
            {
                "core_concepts": [
                    {
                        "key": "a",
                        "label": "Resource",
                        "kind": kind,
                        "evidence": [{"source": "s0", "evidence": "hello"}],
                        "confidence": 0.9,
                    }
                ]
            }
        )
    relationship = json.dumps(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "Resource",
                    "kind": "concept",
                    "evidence": [{"source": "s0", "evidence": "hello"}],
                    "confidence": 0.9,
                },
                {
                    "key": "b",
                    "label": "Bandwidth",
                    "kind": "concept",
                    "evidence": [{"source": "s0", "evidence": "world"}],
                    "confidence": 0.9,
                },
            ],
            "edge_candidates": [
                {
                    "key": "e1",
                    "from": "a",
                    "to": "b",
                    "relationship": "processed by",
                    "evidence": [{"source": "s0", "evidence": "hello world"}],
                    "confidence": 0.9,
                }
            ],
        }
    )
    return [
        ("fenced JSON", "```json\n{}\n```", "provider content is not JSON"),
        ("pseudo-JSON", "core_concepts:[{key: 'a'}]", "provider content is not JSON"),
        ("unsupported memory_type", concept("memory_type"), "unsupported concept kind"),
        ("unsupported definition", concept("definition"), "unsupported concept kind"),
        ("unsupported TERM", concept("TERM"), "unsupported concept kind"),
        ("unsupported processed by", relationship, "unsupported relationship kind"),
    ]


@pytest.mark.parametrize(
    ("name", "output", "error"), _observed_invalid_extractor_outputs()
)
def test_observed_invalid_extractor_outputs_remain_fail_closed(
    tmp_path, name: str, output: str, error: str
) -> None:
    """Historical malformed/unsupported outputs must not become residue."""

    host = ResidueHost(output)
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id)
        service.execute(prepared)
        if name == "unsupported processed by" or name.startswith("unsupported "):
            residue = service.validate(prepared)
            assert residue.edge_candidates == ()
            assert service.normalization_report(prepared)["rejected_items"]
        else:
            with pytest.raises(InterpretationValidationError, match=error):
                service.validate(prepared)


def test_invalid_result_allows_one_explicit_repair_and_no_more(tmp_path):
    host = ResidueHost('{"unexpected": true}', "{}")
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id)
        service.execute(prepared)
        with pytest.raises(InterpretationValidationError):
            service.validate(prepared)
        repaired = service.execute(prepared, repair=True)
        assert repaired.attempt == 1
        assert service.validate(prepared).core_concepts == ()
        assert host.calls == 2
        summary = summarize_lineage_usage(store)
        assert summary["calls"]["extraction"] == 2
        assert summary["token_usage"]["total_tokens"] > 0
        with pytest.raises(InterpretationNotReady, match="one invalid"):
            service.execute(prepared, repair=True)


def test_explicit_revalidation_reclassifies_persisted_result_without_provider_call(tmp_path):
    payload = json.dumps(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "hello",
                    "kind": "concept",
                    "evidence": [{"source": "s0", "evidence": "hello"}],
                    "confidence": 0.9,
                },
                {
                    "key": "b",
                    "label": "world",
                    "kind": "concept",
                    "evidence": [{"source": "s0", "evidence": "world"}],
                    "confidence": 0.9,
                },
            ],
            "edge_candidates": [
                {
                    "key": "e1",
                    "from": "a",
                    "to": "b",
                    "relationship": "related",
                    "evidence": [{"source": "s0", "evidence": "hello world"}],
                    "confidence": 0.9,
                }
            ],
            "route_candidates": [
                {
                    "key": "r1",
                    "edge_keys": ["e1", "e1"],
                    "evidence": [{"source": "s0", "evidence": "hello world"}],
                    "confidence": 0.9,
                }
            ],
        }
    )
    host = ResidueHost(payload)
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id, operation_id="interp-revalidate")
        service.execute(prepared)
        # Simulate the persisted terminal rejection made by the old validator.
        store.connection.execute(
            "UPDATE interpretation_attempts SET status='INVALID',"
            "validation_errors_json='[\"route edges are discontinuous or reversed\"]' "
            "WHERE operation_id=?",
            (prepared.operation_id,),
        )
        store.connection.execute(
            "UPDATE interpretation_operations SET status='FAILED',failure_code='validation_failed' "
            "WHERE operation_id=?",
            (prepared.operation_id,),
        )
        with pytest.raises(InterpretationValidationError, match="not valid"):
            service.validate(prepared)
        residue = service.validate(prepared, revalidate_invalid=True)
        assert len(residue.edge_candidates) == 1
        assert residue.route_candidates == ()
        assert host.calls == 1
        status = store.connection.execute(
            "SELECT status FROM interpretation_operations WHERE operation_id=?",
            (prepared.operation_id,),
        ).fetchone()[0]
        assert status == "RESULT_READY"


def test_repair_with_adjacent_disjoint_json_sections_is_normalized(tmp_path):
    first = json.dumps(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "hello",
                    "kind": "concept",
                    "evidence": [{"source": "s0", "evidence": "hello"}],
                    "confidence": 0.9,
                }
            ]
        }
    )
    second = json.dumps({"edge_candidates": [], "observed_patterns": []})
    host = ResidueHost(first + "\n" + second)
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id, operation_id="interp-adjacent-json")
        service.execute(prepared)
        residue = service.validate(prepared)
        assert [item["key"] for item in residue.core_concepts] == ["a"]


def test_adjacent_json_sections_with_duplicate_fields_remain_invalid(tmp_path):
    host = ResidueHost('{"core_concepts": []}{"core_concepts": []}')
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id, operation_id="interp-duplicate-json")
        service.execute(prepared)
        with pytest.raises(InterpretationValidationError, match="not JSON"):
            service.validate(prepared)


def test_invalid_evidence_allows_one_explicit_repair_and_resolves_offsets(tmp_path):
    invalid = json.dumps(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "Hello",
                    "kind": "concept",
                    "evidence": [{"source": "s0", "evidence": "not present"}],
                    "confidence": 0.9,
                }
            ]
        }
    )
    valid = json.dumps(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "Hello",
                    "kind": "concept",
                    "evidence": [{"source": "s0", "evidence": "hello"}],
                    "confidence": 0.9,
                }
            ]
        }
    )
    host = ResidueHost(invalid, valid)
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id)
        service.execute(prepared)
        with pytest.raises(InterpretationValidationError, match="does not occur"):
            service.validate(prepared)
        service.execute(prepared, repair=True)
        residue = service.validate(prepared)
        assert residue.core_concepts[0]["source_spans"] == (
            {"source_slot": "s0", "start": 0, "end": 5},
        )
        assert "evidence" not in residue.core_concepts[0]
        assert host.calls == 2


def test_model_numeric_source_spans_are_rejected_at_interpretation_boundary(tmp_path):
    output = json.dumps(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "Hello",
                    "kind": "concept",
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 5}],
                    "confidence": 0.9,
                }
            ]
        }
    )
    host = ResidueHost(output)
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id)
        service.execute(prepared)
        with pytest.raises(InterpretationValidationError, match="quotation evidence"):
            service.validate(prepared)


def test_uncertain_provider_call_is_never_automatically_retried(tmp_path):
    store, instance, episode_id = _accepted(tmp_path, FakeHost())
    failing = ResidueHost("{}", fail=True)
    # The accepted episode's host fingerprint is intentionally the normal
    # FakeHost fingerprint, so use a failing host with the same fingerprint by
    # toggling the fixture after preparation.
    failing.fail = False
    with store:
        service = InterpretationService(store, instance, failing)
        prepared = service.prepare(episode_id)
        failing.fail = True
        with pytest.raises(Exception):
            service.execute(prepared)
        with pytest.raises(InterpretationUncertain):
            service.execute(prepared)
        assert failing.calls == 0


def test_host_fingerprint_drift_rejected_before_extraction_call(tmp_path):
    original = ResidueHost("{}")
    store, instance, episode_id = _accepted(tmp_path, original)
    changed = ResidueHost("{}", model_id="changed")
    with store:
        service = InterpretationService(store, instance, changed)
        prepared = service.prepare(episode_id)
        with pytest.raises(Exception, match="fingerprint drifted"):
            service.execute(prepared)
        assert changed.calls == 0


def test_operation_id_and_episode_configuration_are_idempotent(tmp_path):
    host = ResidueHost("{}")
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        first = service.prepare(episode_id, operation_id="same", configuration={"x": 1})
        assert service.prepare(episode_id, operation_id="same", configuration={"x": 1}) == first
        with pytest.raises(InterpretationIdempotencyConflict):
            service.prepare(episode_id, operation_id="same", configuration={"x": 2})
        with pytest.raises(InterpretationIdempotencyConflict):
            service.prepare(episode_id, operation_id="other", configuration={"x": 2})


def test_failed_interpretation_recovery_gets_new_operation_without_rewriting_history(tmp_path):
    host = ResidueHost("{}")
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        failed = service.prepare(episode_id, operation_id="extraction-original")
        store.connection.execute(
            "UPDATE interpretation_operations SET status='FAILED',failure_code='validation_failed' "
            "WHERE operation_id=?",
            (failed.operation_id,),
        )
        recovered = service.prepare(
            episode_id,
            operation_id="extraction-recovery",
            recovery_of=failed.operation_id,
            recovery_version="residue-v1-recovery-test",
        )
        assert recovered.operation_id == "extraction-recovery"
        assert tuple(store.connection.execute(
            "SELECT status,failure_code FROM interpretation_operations WHERE operation_id=?",
            (failed.operation_id,),
        ).fetchone()) == ("FAILED", "validation_failed")
        assert tuple(store.connection.execute(
            "SELECT status,failure_code FROM interpretation_operations WHERE operation_id=?",
            (recovered.operation_id,),
        ).fetchone()) == ("PREPARED", "RECOVERY_OF:extraction-original")
        with pytest.raises(InterpretationError, match="only a FAILED"):
            service.prepare(
                episode_id,
                operation_id="bad-recovery",
                recovery_of=recovered.operation_id,
                recovery_version="residue-v1-recovery-test",
            )


def _holds_payload() -> dict[str, object]:
    return {
        "core_concepts": [
            {"key": "bed", "label": "mulched bed", "kind": "object", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "mulched bed"}]},
            {"key": "moisture", "label": "moisture", "kind": "resource", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "held moisture"}]},
            {"key": "seedlings", "label": "seedlings", "kind": "entity", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "supported seedlings"}]},
        ],
        "edge_candidates": [
            {"key": "e-holds", "from": "bed", "to": "moisture", "relationship": "holds",
             "confidence": 0.9, "evidence": [{"source": "s0", "evidence": "held moisture"}]},
            {"key": "e-supports", "from": "moisture", "to": "seedlings", "relationship": "supports",
             "confidence": 0.9, "evidence": [{"source": "s0", "evidence": "supported seedlings"}]},
        ],
        "route_candidates": [
            {"key": "r-holds", "edge_keys": ["e-holds", "e-supports"], "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "held moisture"}]}
        ],
    }


def test_unsupported_relationship_is_rejected_itemwise_without_losing_valid_edges() -> None:
    source = "The mulched bed held moisture, and the moisture supported seedlings."
    normalized, decisions = normalize_relationship_items(_holds_payload())
    assert _holds_payload()["edge_candidates"][0]["relationship"] == "holds"
    assert [edge["relationship"] for edge in normalized["edge_candidates"]] == [
        "retains", "supports"
    ]
    assert normalized["route_candidates"][0]["edge_keys"] == ["e-holds", "e-supports"]
    assert decisions[0]["kind"] == "relationship_alias"
    assert decisions[0]["raw_relationship"] == "holds"
    assert decisions[0]["normalized_relationship"] == "retains"
    residue = validate_residue(
        normalized, source_slots={"s0": source}, require_evidence_quotes=True
    )
    assert [edge["relationship"] for edge in residue.edge_candidates] == [
        "retains", "supports"
    ]


def test_unsupported_relationship_normalization_is_deterministic_and_other_errors_fail_closed(
) -> None:
    payload = {"core_concepts": [], "edge_candidates": [
        {"key": "e1", "from": "a", "to": "b", "relationship": "holds"}
    ]}
    first = normalize_relationship_items(payload)
    second = normalize_relationship_items(payload)
    assert first == second
    malformed = {"core_concepts": [], "edge_candidates": [{"from": "a", "to": "b"}]}
    normalized, rejected = normalize_relationship_items(malformed)
    assert normalized == malformed and rejected == ()
    with pytest.raises(ResidueValidationError):
        validate_residue(normalized, source_slots={"s0": "source"})


def test_keyed_edge_with_undeclared_endpoint_is_rejected_without_losing_valid_concepts() -> None:
    payload = {
        "core_concepts": [
            {"key": "c1", "label": "slow practice", "kind": "process", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "slow practice"}]},
        ],
        "salient_phrases": [
            {"key": "s1", "label": "focused effort", "kind": "trait", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "focused effort"}]},
        ],
        "edge_candidates": [
            {"key": "e1", "from": "c1", "to": "c2", "relationship": "causes",
             "confidence": 0.9, "evidence": [{"source": "s0", "evidence": "slow practice"}]}
        ],
    }
    normalized, decisions = normalize_relationship_items(payload)
    assert normalized["core_concepts"] == payload["core_concepts"]
    assert normalized["edge_candidates"] == []
    assert decisions[0]["kind"] == "invalid_relationship_item"
    residue = validate_residue(
        normalized,
        source_slots={"s0": "Daily slow practice improved my accuracy through focused effort."},
        require_evidence_quotes=True,
    )
    assert len(residue.core_concepts) == 1
    assert residue.edge_candidates == ()


def test_keyed_graph_items_missing_confidence_are_rejected_without_defaulting() -> None:
    payload = {
        "core_concepts": [
            {"key": "c1", "label": "slow practice", "kind": "process",
             "evidence": [{"source": "s0", "evidence": "slow practice"}]},
        ],
        "edge_candidates": [
            {"key": "e1", "from": "c1", "to": "c1", "relationship": "causes",
             "confidence": 0.9, "evidence": [{"source": "s0", "evidence": "slow practice"}]}
        ],
    }
    normalized, decisions = normalize_relationship_items(payload)
    assert normalized["core_concepts"] == []
    assert normalized["edge_candidates"] == []
    assert [decision["kind"] for decision in decisions] == [
        "invalid_concept_item", "invalid_relationship_item"
    ]
    residue = validate_residue(
        normalized,
        source_slots={"s0": "Daily slow practice improved accuracy."},
        require_evidence_quotes=True,
    )
    assert residue.core_concepts == ()
    assert residue.edge_candidates == ()


def test_understood_protection_wording_is_normalized_and_unsupported_kind_is_dropped() -> None:
    source = "A thick mulch layer protected the soil from drying out during the warm week."
    payload = {
        "core_concepts": [
            {"key": "mulch", "label": "mulch layer", "kind": "object", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "mulch layer"}]},
            {"key": "soil", "label": "soil", "kind": "object", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "soil"}]},
            {"key": "drying", "label": "drying out", "kind": "process", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "drying out"}]},
            {"key": "week", "label": "warm week", "kind": "time", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "warm week"}]},
        ],
        "edge_candidates": [
            {"key": "e1", "from": "mulch", "to": "soil", "relationship": "protects",
             "confidence": 0.9, "evidence": [{"source": "s0", "evidence": "protected the soil"}]},
            {"key": "e2", "from": "mulch", "to": "drying", "relationship": "prevents",
             "confidence": 0.9, "evidence": [{"source": "s0", "evidence": (
                 "protected the soil from drying out"
             )}]},
        ],
    }
    normalized, decisions = normalize_relationship_items(payload)
    assert [edge["relationship"] for edge in normalized["edge_candidates"]] == [
        "prevents", "prevents"
    ]
    assert [concept["key"] for concept in normalized["core_concepts"]] == [
        "mulch", "soil", "drying"
    ]
    assert any(decision["kind"] == "relationship_alias" for decision in decisions)
    assert any(decision["key"] == "week" for decision in decisions)
    residue = validate_residue(
        normalized, source_slots={"s0": source}, require_evidence_quotes=True
    )
    assert [edge["relationship"] for edge in residue.edge_candidates] == [
        "prevents", "prevents"
    ]


def test_interpretation_reports_raw_holds_and_admits_unrelated_valid_edge(tmp_path) -> None:
    payload = {
        "core_concepts": [
            {"key": "a", "label": "hello", "kind": "concept", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "hello"}]},
            {"key": "b", "label": "world", "kind": "concept", "confidence": 0.9,
             "evidence": [{"source": "s0", "evidence": "world"}]},
        ],
        "edge_candidates": [
            {"key": "e-holds", "from": "a", "to": "b", "relationship": "holds",
             "confidence": 0.9, "evidence": [{"source": "s0", "evidence": "hello"}]},
            {"key": "e-supports", "from": "a", "to": "b", "relationship": "supports",
             "confidence": 0.9, "evidence": [{"source": "s0", "evidence": "world"}]},
        ],
    }

    class SourceResidueHost(ResidueHost):
        def generate(self, request: GenerationRequest) -> GenerationResult:
            return GenerationResult(
                json.dumps(payload), self.model_id, "builtin", dict(request.parameters),
                request.seed, TokenUsage(10, 10, 20), 0.0, "stop", {"fixture": True}, {},
            )

    host = SourceResidueHost()
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id, operation_id="interp-holds-item")
        service.execute(prepared)
        residue = service.validate(prepared)
        assert [edge["relationship"] for edge in residue.edge_candidates] == [
            "retains", "supports"
        ]
        report = service.normalization_report(prepared)
        assert report["version"] == RELATIONSHIP_RECONCILIATION_VERSION
        assert report["normalization_decisions"][0]["raw_relationship"] == "holds"
        assert report["rejected_items"] == []
        row = store.connection.execute(
            "SELECT result_json FROM interpretation_attempts WHERE operation_id=?",
            (prepared.operation_id,),
        ).fetchone()
        raw = json.loads(row[0])
        assert json.loads(raw["content"])["edge_candidates"][0]["relationship"] == "holds"
