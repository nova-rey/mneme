from __future__ import annotations

import json
from pathlib import Path

import pytest

from mneme.experiments.artifacts import ArtifactError, ArtifactStore, content_digest
from mneme.experiments.pilot import PilotRun


def _payload() -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    return (
        {"name": "shared-input-control", "contract_revision": 3, "purpose": "test"},
        {"valid": True, "host": {"backend": "fake"}},
        {"calls": 1, "seeds": {"development_generation": [42]}},
        {"subjects": [{"slot": 0, "checkpoint": "cp"}]},
    )


def test_publish_run_preserves_scientific_identity_and_is_idempotent(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    experiment, preflight, plan, bindings = _payload()
    run = store.publish_run(
        experiment=experiment,
        preflight=preflight,
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
        inputs={"development.jsonl": b"{}\n"},
        snapshots={"checkpoint.sqlite3": b"checkpoint"},
    )
    assert run.path == tmp_path / "experiments/shared-input-control/revisions/3/runs/run-001"
    manifest = json.loads((run.path / "run-manifest.json").read_text())
    assert manifest["experiment_name"] == "shared-input-control"
    assert manifest["contract_revision"] == 3
    assert manifest["contract_sha256"] == content_digest(experiment)
    again = store.publish_run(
        experiment=experiment,
        preflight=preflight,
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
    )
    assert again.path == run.path


def test_verify_run_allows_contingent_supplement_artifacts(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "lab")
    run = store.publish_run(
        experiment={"name": "contingent", "contract_revision": 1},
        preflight={"valid": True},
        study_plan={"supplement": "P2-SUPPLEMENT-INTERLOPER-01"},
        bindings={"subjects": [], "checkpoints": {}},
        run_id="run-contingent",
    )
    pilot = PilotRun(store, "run-contingent")
    pilot.prepare(planned_calls=3, max_output_tokens=10, qualification_calls=3, pilot_calls=0)
    pilot.publish_artifact("contingent", "fit-check.json", {"status": "PASS"})
    assert store.verify_run(run.path)
    assert store.verify_run(run.path)


def test_verify_run_allows_evidence_review_receipts(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "lab")
    run = store.publish_run(
        experiment={"name": "evidence-review", "contract_revision": 1},
        preflight={"valid": True},
        study_plan={"supplement": "P2-SUPPLEMENT-INTERLOPER-01"},
        bindings={"subjects": [], "checkpoints": {}},
        run_id="run-review",
    )
    PilotRun(store, "run-review").publish_artifact(
        "evidence-review", "review.json", {"disposition": "rejected", "grounded": True}
    )
    assert store.verify_run(run.path)


def test_verify_run_allows_contingent_assessment_receipts(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "lab")
    run = store.publish_run(
        experiment={"name": "contingent-assessment", "contract_revision": 1},
        preflight={"valid": True},
        study_plan={"supplement": "P2-SUPPLEMENT-INTERLOPER-01"},
        bindings={"subjects": [], "checkpoints": {}},
        run_id="run-assessment",
    )
    PilotRun(store, "run-assessment").publish_artifact(
        "contingent-assessment", "assessment.json", {"status": "accepted"}
    )
    assert store.verify_run(run.path)


def test_verify_run_allows_direct_phase_two_evaluation_json(tmp_path: Path) -> None:
    """PilotRuntime evaluation receipts are direct files, not P0.3 check dirs."""

    store = ArtifactStore(tmp_path / "lab")
    run = store.publish_run(
        experiment={"name": "direct-evaluation", "contract_revision": 1},
        preflight={"valid": True},
        study_plan={"supplement": "p2.3"},
        bindings={"subjects": []},
        run_id="run-direct-evaluation",
    )
    evaluation = run.path / "evaluation"
    evaluation.mkdir()
    receipt = evaluation / "evaluation-s0-p0-r0.json"
    receipt.write_text('{"status":"RESULT","output":"ok"}\n', encoding="utf-8")
    assert store.verify_run(run.path)

    receipt.write_text("not json\n", encoding="utf-8")
    assert store.verify_run(run.path) is False


def test_conflicting_run_id_is_rejected(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    experiment, preflight, plan, bindings = _payload()
    store.publish_run(
        experiment=experiment,
        preflight=preflight,
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
    )
    plan["calls"] = 2
    with pytest.raises(ArtifactError, match="conflicting intent"):
        store.publish_run(
            experiment=experiment,
            preflight=preflight,
            study_plan=plan,
            bindings=bindings,
            run_id="run-001",
        )


def test_check_lifecycle_is_idempotent_and_uncertain_is_terminal(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    experiment, preflight, plan, bindings = _payload()
    store.publish_run(
        experiment=experiment,
        preflight=preflight,
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
    )
    started = store.begin_check("run-001", "check-001", {"slot": 0, "probe": 0})
    assert started["status"] == "STARTED"
    assert store.begin_check("run-001", "check-001", {"slot": 0, "probe": 0}) == started
    result = store.complete_check("run-001", "check-001", {"output": "ok"})
    assert result["status"] == "RESULT"
    assert store.complete_check("run-001", "check-001", {"output": "ok"}) == result
    with pytest.raises(ArtifactError, match="conflicting intent"):
        store.begin_check("run-001", "check-001", {"slot": 99})

    store.begin_check("run-001", "check-002", {"slot": 1})
    uncertain = store.mark_uncertain("run-001", "check-002", "process interrupted")
    assert uncertain["status"] == "UNCERTAIN"
    with pytest.raises(ArtifactError, match="UNCERTAIN"):
        store.begin_check("run-001", "check-002", {"slot": 1})


def test_run_content_tampering_fails_verification(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    experiment, preflight, plan, bindings = _payload()
    run = store.publish_run(
        experiment=experiment,
        preflight=preflight,
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
    )
    (run.path / "study-plan.json").write_text('{"calls":99}\n')
    assert store.verify_run(run.path) is False


def test_payload_and_manifest_tampering_fail_verification(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    experiment, preflight, plan, bindings = _payload()
    run = store.publish_run(
        experiment=experiment,
        preflight=preflight,
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
        inputs={"development.jsonl": b"original\n"},
        snapshots={"checkpoint.sqlite3": b"checkpoint"},
    )
    assert store.verify_run(run.path)
    (run.path / "inputs" / "development.jsonl").write_bytes(b"tampered\n")
    assert store.verify_run(run.path) is False

    (run.path / "inputs" / "development.jsonl").write_bytes(b"original\n")
    manifest_path = run.path / "run-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["run_id"] = "rewritten"
    manifest_path.write_text(json.dumps(manifest) + "\n")
    assert store.verify_run(run.path) is False


def test_pilot_state_tampering_fails_verification(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    experiment, preflight, plan, bindings = _payload()
    run = store.publish_run(
        experiment=experiment,
        preflight=preflight,
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
    )
    pilot = PilotRun(store, "run-001")
    pilot.prepare(planned_calls=3, max_output_tokens=10)
    assert store.verify_run(run.path)

    state_path = run.path / "pilot" / "state.json"
    state = json.loads(state_path.read_text())
    state["status"] = "COMPLETE"
    state_path.write_text(json.dumps(state) + "\n")
    assert store.verify_run(run.path) is False


def test_pilot_reservation_tampering_fails_verification(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    experiment, preflight, plan, bindings = _payload()
    run = store.publish_run(
        experiment=experiment,
        preflight=preflight,
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
    )
    pilot = PilotRun(store, "run-001")
    pilot.prepare(planned_calls=3, max_output_tokens=10)
    pilot.begin_qualification()
    pilot.reserve_call(
        call_id="q-1",
        role="assessor-qualification",
        coordinate={"case": "Q1"},
        max_output_tokens=10,
    )
    assert store.verify_run(run.path)

    reservation_path = run.path / "pilot" / "reservations" / "q-1.json"
    reservation = json.loads(reservation_path.read_text())
    reservation["role"] = "tampered"
    reservation_path.write_text(json.dumps(reservation) + "\n")
    assert store.verify_run(run.path) is False

def test_publication_intent_binds_payload_digests(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    experiment, preflight, plan, bindings = _payload()
    run = store.publish_run(
        experiment=experiment,
        preflight=preflight,
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
        inputs={"development.jsonl": b"one\n"},
    )
    with pytest.raises(ArtifactError, match="conflicting intent"):
        store.publish_run(
            experiment=experiment,
            preflight=preflight,
            study_plan=plan,
            bindings=bindings,
            run_id="run-001",
            inputs={"development.jsonl": b"two\n"},
        )
    assert store.verify_run(run.path)


def test_invalid_artifact_path_is_rejected(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    experiment, preflight, plan, bindings = _payload()
    with pytest.raises(ArtifactError, match="escapes"):
        store.publish_run(
            experiment=experiment,
            preflight=preflight,
            study_plan=plan,
            bindings=bindings,
            run_id="run-001",
            inputs={"../secret": b"bad"},
        )
