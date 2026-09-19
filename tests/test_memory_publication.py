import pytest

from mneme.contracts import GenerationRequest
from mneme.hosts import FakeHost
from mneme.memory import (
    InterpretationPublisher,
    ResolutionDecision,
    StalePublication,
    validate_residue,
)
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.storage import SQLiteStore


def _accepted(tmp_path):
    store = SQLiteStore(tmp_path / "lineage.sqlite3")
    instance = store.create_root(permissions=StoragePermissions(True, True))
    service = ContinuityService(store, instance, FakeHost())
    operation = service.prepare_episode(
        GenerationRequest(({"role": "user", "content": "VRAM constrains model capacity"},))
    )
    service.generate_operation(operation.operation_id)
    service.accept_episode(operation.operation_id)
    return store, instance, operation.episode_id


def _residue():
    return validate_residue(
        {
            "core_concepts": [
                {
                    "key": "vram",
                    "label": "VRAM",
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 4}],
                },
                {
                    "key": "capacity",
                    "label": "model capacity",
                    "source_spans": [{"source_slot": "s0", "start": 15, "end": 29}],
                },
            ],
            "edge_candidates": [
                {"key": "limits", "from": "vram", "to": "capacity", "relationship": "causal"}
            ],
            "route_candidates": [{"key": "route", "edge_keys": ["limits"]}],
        },
        {"s0": "VRAM constrains model capacity"},
    )


def test_publication_is_atomic_and_idempotent(tmp_path):
    store, instance, episode_id = _accepted(tmp_path)
    with store:
        publisher = InterpretationPublisher(store, instance)
        operation_id = publisher.prepare(episode_id)
        receipt = publisher.publish(operation_id, _residue())
        assert receipt.status == "ACCEPTED"
        assert store.current()["current_revision"] == 2
        assert store.connection.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0] == 1
        interpretation_id = store.connection.execute(
            "SELECT interpretation_id FROM interpretations"
        ).fetchone()[0]
        assert store.connection.execute(
            "SELECT COUNT(*) FROM resolution_decisions WHERE interpretation_id=?",
            (interpretation_id,),
        ).fetchone()[0] == 2
        retry = publisher.publish(operation_id, _residue())
        assert retry == receipt
        assert store.current()["current_revision"] == 2


def test_publication_rejects_stale_base_without_graph_write(tmp_path):
    store, instance, episode_id = _accepted(tmp_path)
    with store:
        publisher = InterpretationPublisher(store, instance)
        operation_id = publisher.prepare(episode_id)
        with pytest.raises(StalePublication):
            publisher.publish(operation_id, _residue(), expected_manifest_id="stale")
        assert store.current()["current_revision"] == 1
        assert store.connection.execute("SELECT COUNT(*) FROM interpretations").fetchone()[0] == 0


def test_publication_persists_explicit_alias_decision(tmp_path):
    store, instance, episode_id = _accepted(tmp_path)
    with store:
        publisher = InterpretationPublisher(store, instance)
        operation_id = publisher.prepare(episode_id)
        publisher.publish(
            operation_id,
            _residue(),
            resolution_decisions={
                "vram": ResolutionDecision(
                    "video memory", "video memory", "vram", "explicit_alias"
                )
            },
        )
        row = store.connection.execute(
            "SELECT canonical_label,normalized_label,decision_kind FROM resolution_decisions "
            "WHERE local_key='vram'"
        ).fetchone()
        assert tuple(row) == ("VRAM", "video memory", "explicit_alias")


def test_invalid_recorded_attempt_cannot_publish(tmp_path):
    store, instance, episode_id = _accepted(tmp_path)
    with store:
        publisher = InterpretationPublisher(store, instance)
        operation_id = publisher.prepare(episode_id)
        publisher.record_attempt(operation_id, "{bad", status="INVALID")
        with pytest.raises(Exception, match="not publishable"):
            publisher.publish(operation_id, _residue())
        assert store.current()["current_revision"] == 1


def test_attempt_result_is_durable_after_started_transition(tmp_path):
    store, instance, episode_id = _accepted(tmp_path)
    with store:
        publisher = InterpretationPublisher(store, instance)
        operation_id = publisher.prepare(episode_id)
        publisher.record_attempt(operation_id, "", status="STARTED")
        publisher.record_attempt(operation_id, _residue().to_dict(), status="RESULT_READY")
        status = store.connection.execute(
            "SELECT status FROM interpretation_operations WHERE operation_id=?", (operation_id,)
        ).fetchone()[0]
        assert status == "RESULT_READY"
