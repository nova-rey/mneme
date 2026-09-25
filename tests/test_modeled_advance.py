from __future__ import annotations

import json

import pytest

from mneme.contracts import GenerationRequest
from mneme.development import ModeledAdvanceError, ModeledAdvanceService, Observation
from mneme.development import recovery as recovery_module
from mneme.development.recovery import verify_replay
from mneme.hosts import FakeHost
from mneme.memory import InterpretationPublisher, Residue, validate_residue
from mneme.state.contracts import StoragePermissions
from mneme.state.policy import PolicyService
from mneme.state.service import ContinuityService
from mneme.state.storage import SQLiteStore


def _prepared_store(tmp_path, *, learn: bool = True) -> tuple[SQLiteStore, str]:
    store = SQLiteStore(tmp_path / "lineage.sqlite3")
    instance = store.create_root(
        permissions=StoragePermissions(store=True, export=True, interpret=True, learn=True)
    )
    continuity = ContinuityService(store, instance, FakeHost())
    operation = continuity.prepare_episode(
        GenerationRequest(({"role": "user", "content": "A causes B"},)),
        operation_id="generation-op",
    )
    continuity.generate_operation(operation.operation_id)
    continuity.accept_episode(operation.operation_id)
    residue: Residue = validate_residue(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "A",
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 1}],
                    "confidence": 0.9,
                },
                {
                    "key": "b",
                    "label": "B",
                    "source_spans": [{"source_slot": "s0", "start": 8, "end": 9}],
                    "confidence": 0.9,
                },
            ],
            "edge_candidates": [
                {
                    "key": "edge-ab",
                    "from": "a",
                    "to": "b",
                    "relationship": "causes",
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 9}],
                    "confidence": 0.9,
                }
            ],
        },
        {"s0": "A causes B"},
    )
    publisher = InterpretationPublisher(store, instance)
    publisher.publish(
        publisher.prepare(operation.episode_id, operation_id="interpretation-op"),
        residue,
        development_operation_id="development-op",
        observations=(Observation(target_key="edge-ab"),),
    )
    if not learn:
        PolicyService(store, instance).revoke(("learn",))
    return store, instance


def test_modeled_advance_is_durable_replayable_and_idempotent(tmp_path) -> None:
    store, instance = _prepared_store(tmp_path)
    with store:
        before = dict(store.current())
        service = ModeledAdvanceService(store, instance)
        record = service.advance("general", 8, operation_id="advance-1")
        assert len(record.targets) == 1
        assert record.targets[0][1] == "general"
        assert record.opportunity == 9
        assert record.status == "ACCEPTED"
        assert record.accepted_episode_count == 1
        assert record.graph_revision == 1
        assert record.revision == int(before["current_revision"]) + 1
        assert store.connection.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1
        assert store.connection.execute(
            "SELECT COUNT(*) FROM modeled_advance_operations"
        ).fetchone()[0] == 1
        assert verify_replay(store)["matches_materialized"] is True

        retry = service.advance("general", 8, operation_id="advance-1")
        assert retry == record
        with pytest.raises(ModeledAdvanceError, match="idempotency conflict"):
            service.advance("general", 7, operation_id="advance-1")

        current = store.current()
        manifest = store.connection.execute(
            "SELECT accepted_episode_count,graph_revision,opportunity FROM manifests "
            "WHERE manifest_id=?",
            (current["current_manifest_id"],),
        ).fetchone()
        assert tuple(manifest) == (1, 1, 9)


def test_modeled_advance_rolls_back_operation_when_materialization_is_interrupted(
    tmp_path, monkeypatch
):
    store, instance = _prepared_store(tmp_path)
    with store:
        before = dict(store.current())

        original_replay = recovery_module.replay_learner
        calls = 0

        def interrupted(target_store):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_replay(target_store)
            raise recovery_module.ReplayError("simulated interruption")

        monkeypatch.setattr(recovery_module, "replay_learner", interrupted)
        with pytest.raises(ModeledAdvanceError, match="simulated interruption"):
            ModeledAdvanceService(store, instance).advance(
                "general", 8, operation_id="interrupted-advance"
            )
        assert store.connection.execute(
            "SELECT COUNT(*) FROM modeled_advance_operations"
        ).fetchone()[0] == 0
        assert dict(store.current()) == before


def test_modeled_advance_requires_learning_and_a_pinned_target(tmp_path) -> None:
    store, instance = _prepared_store(tmp_path, learn=False)
    with store:
        with pytest.raises(ModeledAdvanceError, match="learn"):
            ModeledAdvanceService(store, instance).advance("general", 8)

    empty, empty_instance = SQLiteStore(tmp_path / "empty.sqlite3"), None
    with empty:
        empty_instance = empty.create_root(
            permissions=StoragePermissions(store=True, export=True, interpret=True, learn=True)
        )
        with pytest.raises(ModeledAdvanceError, match="no learner targets"):
            ModeledAdvanceService(empty, empty_instance).advance("general", 8)


def test_cli_modeled_advance_emits_machine_readable_receipt(tmp_path, capsys) -> None:
    store, _instance = _prepared_store(tmp_path)
    store.close()
    from mneme.cli import main

    assert main(
        [
            "--store",
            str(tmp_path / "lineage.sqlite3"),
            "learner",
            "advance",
            "--context",
            "general",
            "--steps",
            "8",
            "--operation-id",
            "cli-advance",
        ]
    ) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["operation_id"] == "cli-advance"
    assert output["opportunity"] == 9
