from __future__ import annotations

import json

import pytest

from mneme.chat import ChatSession
from mneme.contracts import GenerationRequest, GenerationResult
from mneme.controller import ResponseController, TurnIntent
from mneme.corrections import CorrectionService
from mneme.experiments.live_accounting import summarize_lineage_usage
from mneme.hosts import FakeHost
from mneme.identity import IdentityError, IdentityService
from mneme.memory import InterpretationPublisher, validate_residue
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.snapshots import create_checkpoint, fork_from_checkpoint
from mneme.state.storage import SQLiteStore


class _CountingFakeHost(FakeHost):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def generate(self, request: GenerationRequest):
        self.calls += 1
        return super().generate(request)


class _NamingHost(FakeHost):
    def __init__(self, content: str):
        super().__init__()
        self.content = content
        self.calls = 0

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls += 1
        result = super().generate(request)
        return GenerationResult(
            self.content,
            result.model_id,
            result.provider,
            result.effective_parameters,
            result.seed,
            result.token_usage,
            result.latency_ms,
            result.finish_reason,
            result.raw_metadata,
            result.provenance,
        )


class _NoUsageNamingHost(_NamingHost):
    def generate(self, request: GenerationRequest) -> GenerationResult:
        result = super().generate(request)
        return GenerationResult(
            result.content,
            result.model_id,
            result.provider,
            result.effective_parameters,
            result.seed,
            None,
            result.latency_ms,
            result.finish_reason,
            result.raw_metadata,
            result.provenance,
        )


def _store(tmp_path, name: str):
    store = SQLiteStore(tmp_path / f"{name}.sqlite3")
    instance = store.create_root(permissions=StoragePermissions(True, True, True, True, True))
    return store, instance


def test_identity_requires_deliberate_adoption_and_persists_self_view(tmp_path):
    store, instance = _store(tmp_path, "identity")
    with store:
        service = IdentityService(store, instance)
        assert service.current() is None
        adopted = service.adopt("Ada", source={"actor": "operator"})
        assert adopted.name == "Ada"
        assert service.current() == adopted
        with pytest.raises(IdentityError, match="already adopted"):
            service.adopt("Other")
        assert service.add_alias("A")
        assert store.current()["current_revision"] == 2


def test_identity_host_adoption_is_one_call_and_strictly_structured(tmp_path):
    store, instance = _store(tmp_path, "host-identity")
    with store:
        host = _NamingHost('{"name":"Nova"}')
        view = IdentityService(store, instance).adopt_from_host(host)
        assert view.name == "Nova"
        assert host.calls == 1
        source = store.connection.execute(
            "SELECT source_json FROM identity_events WHERE event_kind='adopt'"
        ).fetchone()[0]
        assert "Nova" not in source
        generation = store.connection.execute(
            "SELECT g.identity_event_id,g.host_ref,g.request_json,g.result_json,"
            "g.returned_model,g.returned_provider,g.usage_json,g.finish_reason,"
            "h.fingerprint_json FROM identity_generation_records g "
            "JOIN identity_events e ON e.event_id=g.identity_event_id "
            "JOIN host_records h ON h.host_ref=g.host_ref WHERE e.event_kind='adopt'"
        ).fetchone()
        assert generation is not None
        assert generation[0] == store.connection.execute(
            "SELECT event_id FROM identity_events WHERE event_kind='adopt'"
        ).fetchone()[0]
        assert json.loads(generation[2])["messages"][0]["content"].startswith("Choose one")
        assert json.loads(generation[3])["content"] == '{"name":"Nova"}'
        assert generation[4:6] == ("mneme-fake-v1", "builtin")
        assert json.loads(generation[6])["total_tokens"] is not None
        assert generation[7] == "stop"
        assert json.loads(generation[8])["provider"] == "builtin"

    invalid_store, invalid_instance = _store(tmp_path, "invalid-host-identity")
    with invalid_store:
        host = _NamingHost('{"name":"Nova", "extra":true}')
        with pytest.raises(IdentityError, match="only a string name"):
            IdentityService(invalid_store, invalid_instance).adopt_from_host(host)
        assert host.calls == 1
        assert IdentityService(invalid_store, invalid_instance).current() is None


def test_identity_host_adoption_preserves_unknown_usage(tmp_path):
    store, instance = _store(tmp_path, "host-identity-no-usage")
    with store:
        IdentityService(store, instance).adopt_from_host(_NoUsageNamingHost('{"name":"Nova"}'))
        usage = store.connection.execute(
            "SELECT usage_json FROM identity_generation_records"
        ).fetchone()[0]
        assert usage is None


def test_live_usage_accounting_separates_extraction_attempts_and_naming(tmp_path):
    store, instance = _store(tmp_path, "accounting")
    with store:
        host = _NamingHost('{"name":"Nova"}')
        continuity = ContinuityService(store, instance, host)
        operation = continuity.prepare_episode(
            GenerationRequest(({"role": "user", "content": "hello world"},))
        )
        continuity.generate_operation(operation.operation_id)
        continuity.accept_episode(operation.operation_id)
        IdentityService(store, instance).adopt_from_host(host)
        summary = summarize_lineage_usage(store)
        assert summary["calls"] == {"development": 1, "extraction": 0, "naming": 1, "total": 2}
        assert summary["by_role"]["naming"]["token_usage"]["total_tokens"] is not None


def test_fork_rebinds_inherited_self_view_to_child_lineage(tmp_path):
    store, instance = _store(tmp_path, "parent")
    checkpoint = tmp_path / "parent.checkpoint.sqlite3"
    child_path = tmp_path / "child.sqlite3"
    with store:
        parent_view = IdentityService(store, instance).adopt("Ada")
        create_checkpoint(store, checkpoint)
    child_id = fork_from_checkpoint(checkpoint, child_path)
    with SQLiteStore(child_path) as child:
        child_view = IdentityService(child, child_id).current()
        assert child_view is not None
        assert child_view.name == parent_view.name
        assert child_view.self_view_id != parent_view.self_view_id
        assert child_view.content_digest == parent_view.content_digest
        parent_id = child.connection.execute(
            "SELECT parent_instance_id FROM lineages WHERE instance_id=?", (child_id,)
        ).fetchone()[0]
        assert parent_id == instance
        owner = child.connection.execute(
            "SELECT instance_id FROM self_views WHERE self_view_id=?",
            (child_view.self_view_id,),
        ).fetchone()[0]
        assert owner == child_id


def test_controller_memory_off_has_no_identity_or_graph_payload(tmp_path):
    store_a, instance_a = _store(tmp_path, "a")
    store_b, instance_b = _store(tmp_path, "b")
    with store_a, store_b:
        IdentityService(store_a, instance_a).adopt("Ada")
        host_a, host_b = FakeHost(), FakeHost()
        prepared_a = ResponseController(store_a, instance_a, host_a).prepare(
            TurnIntent("same input", memory="off")
        )
        prepared_b = ResponseController(store_b, instance_b, host_b).prepare(
            TurnIntent("same input", memory="off")
        )
        assert prepared_a.request.generation_material() == prepared_b.request.generation_material()
        assert prepared_a.selected == ()
        result = ResponseController(store_a, instance_a, host_a).execute(prepared_a)
        assert result.operation.status == "ACCEPTED"
        assert store_a.current()["current_revision"] == 2
        assert store_a.connection.execute("SELECT COUNT(*) FROM turn_traces").fetchone()[0] == 1
        assert store_a.current()["current_revision"] != 3


def test_controller_retry_reuses_accepted_operation_without_duplicate_trace_or_call(tmp_path):
    store, instance = _store(tmp_path, "retry")
    with store:
        host = _CountingFakeHost()
        controller = ResponseController(store, instance, host)
        prepared = controller.prepare(TurnIntent("same input", memory="off", operation_id="op-1"))
        first = controller.execute(prepared)
        second = controller.execute(prepared)
        assert first.operation.status == second.operation.status == "ACCEPTED"
        assert first.operation.revision == second.operation.revision == 1
        assert host.calls == 1
        assert store.connection.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 1
        assert store.connection.execute("SELECT COUNT(*) FROM turn_traces").fetchone()[0] == 1
        assert (
            store.connection.execute("SELECT COUNT(*) FROM generation_records").fetchone()[0] == 1
        )


def test_chat_session_uses_controller_and_fresh_clears_only_process_context(tmp_path):
    store, instance = _store(tmp_path, "chat")
    with store:
        session = ChatSession(store, instance, FakeHost(), memory="off")
        first = session.turn("hello", operation_id="chat-1")
        assert first.output_text.startswith("FakeHost response")
        assert len(session.messages) == 2
        revision = store.current()["current_revision"]
        session.fresh()
        assert session.messages == ()
        assert store.current()["current_revision"] == revision


def test_correction_is_explicit_reversible_and_does_not_delete_history(tmp_path):
    store, instance = _store(tmp_path, "correction")
    with store:
        service = CorrectionService(store, instance)
        directive = service.suppress(route_id="route-1", context_tag="explanation")
        assert (
            store.connection.execute(
                "SELECT status FROM correction_directives WHERE directive_id=?", (directive,)
            ).fetchone()[0]
            == "ACTIVE"
        )
        revoked = service.revoke(directive)
        assert revoked != directive
        assert (
            store.connection.execute("SELECT COUNT(*) FROM correction_directives").fetchone()[0]
            == 2
        )
        assert store.current()["current_revision"] == 2


def test_controller_uses_fixed_content_route_selection(tmp_path):
    store, instance = _store(tmp_path, "route")
    with store:
        from mneme.state.service import ContinuityService

        continuity = ContinuityService(store, instance, FakeHost())
        operation = continuity.prepare_episode(
            GenerationRequest(({"role": "user", "content": "VRAM constrains capacity"},))
        )
        continuity.generate_operation(operation.operation_id)
        continuity.accept_episode(operation.operation_id)
        residue = validate_residue(
            {
                "core_concepts": [
                    {
                        "key": "vram",
                        "label": "VRAM",
                        "source_spans": [{"source_slot": "s0", "start": 0, "end": 4}],
                        "confidence": 0.9,
                    },
                    {
                        "key": "capacity",
                        "label": "capacity",
                        "source_spans": [{"source_slot": "s0", "start": 16, "end": 24}],
                        "confidence": 0.9,
                    },
                ],
                "edge_candidates": [
                    {
                        "key": "limits",
                        "from": "vram",
                        "to": "capacity",
                        "relationship": "constrains",
                        "source_spans": [{"source_slot": "s0", "start": 0, "end": 24}],
                        "confidence": 0.9,
                    }
                ],
                "route_candidates": [
                    {
                        "key": "route",
                        "edge_keys": ["limits"],
                        "source_spans": [{"source_slot": "s0", "start": 0, "end": 24}],
                        "confidence": 0.9,
                    }
                ],
            },
            {"s0": "VRAM constrains capacity"},
        )
        publisher = InterpretationPublisher(store, instance)
        interpretation = publisher.prepare(operation.episode_id)
        publisher.publish(interpretation, residue)
        prepared = ResponseController(store, instance, FakeHost()).prepare(
            TurnIntent("Explain VRAM", memory="graph")
        )
        assert [route.route_key for route in prepared.selected] == ["route"]
