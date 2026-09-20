"""Focused atomic publication tests for the Phase Two learner ledger."""

from __future__ import annotations

import json

import pytest

from mneme.contracts import GenerationRequest
from mneme.development import ConsequenceAssessment, Observation, QuarantineService
from mneme.development.recovery import verify_replay
from mneme.hosts import FakeHost
from mneme.memory import InterpretationPublisher, PublicationError, Residue, validate_residue
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.storage import SQLiteStore


def _episode_and_residue(tmp_path, *, learn: bool) -> tuple[SQLiteStore, str, str, Residue]:
    store = SQLiteStore(tmp_path / "lineage.sqlite3")
    instance = store.create_root(
        permissions=StoragePermissions(
            store=True,
            export=True,
            interpret=True,
            learn=learn,
        )
    )
    continuity = ContinuityService(store, instance, FakeHost())
    operation = continuity.prepare_episode(
        GenerationRequest(({"role": "user", "content": "A causes B"},)),
        operation_id="generation-op",
    )
    continuity.generate_operation(operation.operation_id)
    continuity.accept_episode(operation.operation_id)
    residue = validate_residue(
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
    return store, instance, operation.episode_id, residue


def test_learning_publication_is_atomic_and_records_stable_bindings(tmp_path):
    store, instance, episode_id, residue = _episode_and_residue(tmp_path, learn=True)
    with store:
        publisher = InterpretationPublisher(store, instance)
        operation_id = publisher.prepare(episode_id, operation_id="interpretation-op")
        receipt = publisher.publish(
            operation_id,
            residue,
            development_operation_id="development-op",
            opportunity=1,
            observations=(
                Observation(target_key="edge-ab", occurrence_key="observation-1"),
            ),
        )

        assert receipt.status == "ACCEPTED"
        manifest = store.connection.execute(
            "SELECT learner_snapshot_id,learner_configuration_digest,opportunity "
            "FROM manifests WHERE manifest_id=?",
            (receipt.manifest_id,),
        ).fetchone()
        assert manifest[0] is not None
        assert manifest[1]
        assert manifest[2] == 1
        assert store.connection.execute(
            "SELECT COUNT(*) FROM semantic_bindings WHERE interpretation_id=?",
            (receipt.interpretation_id,),
        ).fetchone()[0] == 3
        observation = store.connection.execute(
            "SELECT edge_key,status,dependence,covered,actual_exposure,credit_reason "
            "FROM development_observations"
        ).fetchone()
        assert tuple(observation) == (
            "edge-ab",
            "present",
            "external_supported",
            1,
            0,
            "credited",
        )
        update = store.connection.execute(
            "SELECT delta,before_json,after_json FROM learner_updates"
        ).fetchone()
        assert update[0] == 80_000
        assert json.loads(update[1])["accessibility"] == 0
        assert json.loads(update[2])["accessibility"] == 80_000
        assert store.connection.execute(
            "SELECT accessibility FROM learner_values"
        ).fetchone()[0] == 80_000

        # The accepted receipt is the idempotent boundary: no second learner
        # application, binding, or observation is created on retry.
        assert publisher.publish(operation_id, residue, observations=()) == receipt
        for table in (
            "semantic_bindings",
            "development_observations",
            "learner_updates",
            "learner_values",
            "learner_snapshots",
        ):
            assert store.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == (
                3
                if table == "semantic_bindings"
                else 1
            )


def test_learning_values_reuse_stable_edge_binding_across_local_keys(tmp_path):
    store, instance, episode_id, first_residue = _episode_and_residue(tmp_path, learn=True)
    with store:
        publisher = InterpretationPublisher(store, instance)
        publisher.publish(
            publisher.prepare(episode_id, operation_id="stable-first"),
            first_residue,
            development_operation_id="stable-development-first",
            opportunity=1,
            observations=(Observation(target_key="edge-ab", occurrence_key="first"),),
        )
        continuity = ContinuityService(store, instance, FakeHost())
        operation = continuity.prepare_episode(
            GenerationRequest(({"role": "user", "content": "A causes B"},)),
            operation_id="stable-generation-second",
        )
        continuity.generate_operation(operation.operation_id)
        continuity.accept_episode(operation.operation_id)
        second_residue = validate_residue(
            {
                "core_concepts": [
                    {
                        "key": "new-a",
                        "label": "A",
                        "source_spans": [{"source_slot": "s0", "start": 0, "end": 1}],
                        "confidence": 0.9,
                    },
                    {
                        "key": "new-b",
                        "label": "B",
                        "source_spans": [{"source_slot": "s0", "start": 8, "end": 9}],
                        "confidence": 0.9,
                    },
                ],
                "edge_candidates": [
                    {
                        "key": "edge-new-local",
                        "from": "new-a",
                        "to": "new-b",
                        "relationship": "causes",
                        "source_spans": [{"source_slot": "s0", "start": 0, "end": 9}],
                        "confidence": 0.9,
                    }
                ],
            },
            {"s0": "A causes B"},
        )
        publisher.publish(
            publisher.prepare(operation.episode_id, operation_id="stable-second"),
            second_residue,
            development_operation_id="stable-development-second",
            opportunity=2,
            observations=(
                Observation(target_key="edge-new-local", occurrence_key="second"),
            ),
        )
        bindings = store.connection.execute(
            "SELECT canonical_key FROM semantic_bindings "
            "WHERE local_key IN ('edge-ab', 'edge-new-local') "
            "ORDER BY local_key"
        ).fetchall()
        values = store.connection.execute(
            "SELECT edge_key,accessibility FROM learner_values ORDER BY opportunity"
        ).fetchall()
        updates = store.connection.execute(
            "SELECT before_json,after_json FROM learner_updates ORDER BY opportunity"
        ).fetchall()

    assert len(bindings) == 2
    assert bindings[0][0] == bindings[1][0]
    assert len(values) == 2
    assert values[0][0] == values[1][0] == bindings[0][0]
    assert json.loads(updates[1][0])["accessibility"] == 80_000
    assert json.loads(updates[1][1])["accessibility"] == 160_000


def test_replay_verification_and_quarantine_rebuild_use_canonical_binding(tmp_path):
    store, instance, episode_id, residue = _episode_and_residue(tmp_path, learn=True)
    with store:
        publisher = InterpretationPublisher(store, instance)
        receipt = publisher.publish(
            publisher.prepare(episode_id, operation_id="replay-interpretation"),
            residue,
            development_operation_id="replay-development",
            opportunity=1,
            observations=(Observation(target_key="edge-ab", occurrence_key="replay"),),
        )
        initial = verify_replay(store)
        assert initial["matches_materialized"] is True
        canonical = store.connection.execute(
            "SELECT canonical_key FROM semantic_bindings WHERE binding_id=("
            "SELECT binding_id FROM development_observations WHERE operation_id=?)",
            ("replay-development",),
        ).fetchone()[0]
        added = QuarantineService(store, instance).add(
            "edge", str(canonical), "source interpretation rejected"
        )
        rebuilt = verify_replay(store)
        assert rebuilt["matches_materialized"] is True
        assert "replay-development" in rebuilt["skipped_operation_ids"]
        assert rebuilt["rebuild_required"] is True
        assert store.connection.execute(
            "SELECT accessibility FROM learner_values ORDER BY rowid DESC LIMIT 1"
        ).fetchone()[0] == 0
        released = QuarantineService(store, instance).release(added.event_id)
        restored = verify_replay(store)
        assert restored["matches_materialized"] is True
        assert restored["skipped_operation_ids"] == []
        assert released.authority_revision > added.authority_revision
        assert receipt.status == "ACCEPTED"


def test_unknown_observation_is_durable_without_credit(tmp_path):
    store, instance, episode_id, residue = _episode_and_residue(tmp_path, learn=True)
    with store:
        publisher = InterpretationPublisher(store, instance)
        operation_id = publisher.prepare(episode_id, operation_id="unknown-interpretation")
        publisher.publish(
            operation_id,
            residue,
            development_operation_id="unknown-development",
            opportunity=1,
            observations=(
                Observation(
                    target_key="edge-ab",
                    status="unknown",
                    covered=False,
                    occurrence_key="unknown-1",
                ),
            ),
        )
        update = store.connection.execute(
            "SELECT delta,reason FROM learner_updates"
        ).fetchone()
        assert tuple(update) == (0, "measurement_unknown")
        assert store.connection.execute(
            "SELECT accessibility FROM learner_values"
        ).fetchone()[0] == 0


def test_route_consequences_and_assessments_are_durable_in_learner_snapshot(tmp_path):
    store, instance, episode_id, residue = _episode_and_residue(tmp_path, learn=True)
    with store:
        publisher = InterpretationPublisher(store, instance)
        operation_id = publisher.prepare(episode_id, operation_id="route-interpretation")
        receipt = publisher.publish(
            operation_id,
            residue,
            development_operation_id="route-development",
            opportunity=1,
            observations=(Observation(target_key="edge-ab", occurrence_key="route-observation"),),
            consequences=(
                ConsequenceAssessment(
                    "assessment-1",
                    "route-ab",
                    direction=-1,
                    exposure_id="exposure-1",
                    opportunity=1,
                ),
            ),
        )
        learner_snapshot = store.connection.execute(
            "SELECT learner_snapshot_id FROM manifests WHERE manifest_id=?",
            (receipt.manifest_id,),
        ).fetchone()
        row = store.connection.execute(
            "SELECT configuration_json FROM learner_snapshots WHERE snapshot_id=?",
            (learner_snapshot[0],),
        ).fetchone()
        payload = json.loads(row[0])
        assert payload["state"]["routes"]["route-ab:general"]["consequence"] == -50_000
        assessment = store.connection.execute(
            "SELECT assessment_id,target_route_id,direction,status FROM outcome_assessments"
        ).fetchone()
        assert tuple(assessment) == ("assessment-1", "route-ab", -1, "ACCEPTED")

        # A later publication reconstructs route state from the prior learner
        # snapshot rather than starting contextual restraint over at zero.
        continuity = ContinuityService(store, instance, FakeHost())
        next_operation = continuity.prepare_episode(
            GenerationRequest(({"role": "user", "content": "A causes B"},)),
            operation_id="generation-op-2",
        )
        continuity.generate_operation(next_operation.operation_id)
        continuity.accept_episode(next_operation.operation_id)
        next_interpretation = publisher.prepare(
            next_operation.episode_id, operation_id="route-interpretation-2"
        )
        next_receipt = publisher.publish(
            next_interpretation,
            residue,
            development_operation_id="route-development-2",
            opportunity=2,
            observations=(Observation(target_key="edge-ab", occurrence_key="route-observation-2"),),
            consequences=(
                ConsequenceAssessment(
                    "assessment-2",
                    "route-ab",
                    direction=-1,
                    exposure_id="exposure-2",
                    opportunity=2,
                ),
            ),
        )
        next_snapshot = store.connection.execute(
            "SELECT learner_snapshot_id FROM manifests WHERE manifest_id=?",
            (next_receipt.manifest_id,),
        ).fetchone()
        next_payload = json.loads(
            store.connection.execute(
                "SELECT configuration_json FROM learner_snapshots WHERE snapshot_id=?",
                (next_snapshot[0],),
            ).fetchone()[0]
        )
        assert next_payload["state"]["routes"]["route-ab:general"]["consequence"] == -100_000
        assert store.connection.execute(
            "SELECT COUNT(*) FROM outcome_assessments"
        ).fetchone()[0] == 2


def test_learning_publication_requires_explicit_learning_permission(tmp_path):
    store, instance, episode_id, residue = _episode_and_residue(tmp_path, learn=False)
    with store:
        publisher = InterpretationPublisher(store, instance)
        operation_id = publisher.prepare(episode_id, operation_id="legacy-interpretation")
        with pytest.raises(PublicationError, match="learning permission"):
            publisher.publish(
                operation_id,
                residue,
                observations=(Observation(target_key="edge-ab"),),
            )
        assert store.connection.execute("SELECT COUNT(*) FROM interpretations").fetchone()[0] == 0
        assert store.connection.execute(
            "SELECT COUNT(*) FROM development_observations"
        ).fetchone()[0] == 0
