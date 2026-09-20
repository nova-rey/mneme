from __future__ import annotations

from pathlib import Path

from mneme.contracts import GenerationRequest
from mneme.development import Observation, QuarantineService
from mneme.development.recovery import verify_replay
from mneme.hosts import FakeHost
from mneme.memory import InterpretationPublisher, validate_residue
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.snapshots import create_checkpoint, fork_from_checkpoint
from mneme.state.storage import SQLiteStore


def test_fork_inherits_learner_snapshot_but_uses_child_identity(tmp_path: Path) -> None:
    parent_path = tmp_path / "parent.sqlite3"
    store = SQLiteStore(parent_path)
    host = FakeHost()
    instance = store.create_root(
        permissions=StoragePermissions(True, True, learn=True),
        host_binding=host.fingerprint().to_dict(),
    )
    operation = ContinuityService(store, instance, host).prepare_episode(
        GenerationRequest(({"role": "user", "content": "A causes B"},)),
        operation_id="fork-generation",
    )
    ContinuityService(store, instance, host).generate_operation(operation.operation_id)
    ContinuityService(store, instance, host).accept_episode(operation.operation_id)
    residue = validate_residue(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "A",
                    "confidence": 0.9,
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 1}],
                },
                {
                    "key": "b",
                    "label": "B",
                    "confidence": 0.9,
                    "source_spans": [{"source_slot": "s0", "start": 9, "end": 10}],
                },
            ],
            "edge_candidates": [
                {
                    "key": "edge-ab",
                    "from": "a",
                    "to": "b",
                    "relationship": "causes",
                    "confidence": 0.9,
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 10}],
                }
            ],
        },
        {"s0": "A causes B"},
    )
    publisher = InterpretationPublisher(store, instance)
    interpretation = publisher.prepare(operation.episode_id, operation_id="fork-interpretation")
    publisher.publish(
        interpretation,
        residue,
        observations=(Observation(target_key="edge-ab"),),
        development_operation_id="fork-development",
        opportunity=1,
    )
    checkpoint = tmp_path / "parent-checkpoint.sqlite3"
    create_checkpoint(store, checkpoint)
    store.close()

    child_path = tmp_path / "child.sqlite3"
    child = fork_from_checkpoint(checkpoint, child_path)
    with SQLiteStore(child_path, read_only=True) as child_store:
        manifest = child_store.connection.execute(
            "SELECT learner_snapshot_id,opportunity FROM manifests "
            "WHERE instance_id=? AND revision=0",
            (child,),
        ).fetchone()
        assert manifest[0]
        assert manifest[1] == 1
        assert child_store.connection.execute(
            "SELECT COUNT(*) FROM learner_values WHERE instance_id=?", (child,)
        ).fetchone()[0] == 1
        replay = verify_replay(child_store)
        assert replay["operation_count"] == 1
        assert replay["matches_materialized"] is True

    # A quarantine immediately after the fork has no child-local development
    # operation to own a rebuilt materialization.  The inherited parent
    # operation is still a valid immutable ledger owner for the child-local
    # learner rows, and the rebuild must not leave the old value visible.
    with SQLiteStore(child_path) as child_store:
        canonical = child_store.connection.execute(
            "SELECT canonical_key FROM semantic_bindings WHERE candidate_id IS NULL LIMIT 1"
        ).fetchone()[0]
        QuarantineService(child_store, child).add(
            "edge", str(canonical), "forked evidence quarantined"
        )
        replay = verify_replay(child_store)
        assert replay["operation_count"] == 0
        assert replay["skipped_operation_ids"] == ["fork-development"]
        assert replay["matches_materialized"] is True
        assert child_store.connection.execute(
            "SELECT accessibility FROM learner_values WHERE instance_id=? "
            "ORDER BY rowid DESC LIMIT 1",
            (child,),
        ).fetchone()[0] == 0
