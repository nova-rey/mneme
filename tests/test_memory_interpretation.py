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
from mneme.memory.residue import SUPPORTED_CONCEPT_KINDS, SUPPORTED_RELATIONSHIP_KINDS
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
        assert "Return raw JSON only" in system
        assert "no Markdown fences" in system
        assert "no introductory or concluding prose" in system
        assert "no other concept or relationship enum values" in system
        assert "core_concepts records require key, label, kind" in system
        assert "evidence, and confidence" in system
        assert "Do not calculate or provide numeric offsets" in system
        assert "Every evidence object must contain only source and evidence" in system
        assert "route_candidates are optional source-backed groupings" in system
        assert "MNEME derives bounded directed routes from accepted graph edges" in system
        assert "one contiguous substring of the referenced source slot" in system
        assert "omit that assertion instead of paraphrasing" in system
        for kind in SUPPORTED_CONCEPT_KINDS:
            assert kind in system
        for relationship in SUPPORTED_RELATIONSHIP_KINDS:
            assert relationship in system
        assert request["request"]["parameters"]["max_new_tokens"] == 1536


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
        ("fenced JSON", "```json\n{}\n```", "Expecting value"),
        ("pseudo-JSON", "core_concepts:[{key: 'a'}]", "Expecting value"),
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

    del name
    host = ResidueHost(output)
    store, instance, episode_id = _accepted(tmp_path, host)
    with store:
        service = InterpretationService(store, instance, host)
        prepared = service.prepare(episode_id)
        service.execute(prepared)
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
