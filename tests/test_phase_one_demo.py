from __future__ import annotations

import json
from pathlib import Path

import pytest

from mneme.cli import main
from mneme.demo import DemoError, run_phase_one_gate


def test_phase_one_gate_driver_requires_preceding_gate(tmp_path: Path) -> None:
    with pytest.raises(DemoError, match="preceding gate"):
        run_phase_one_gate(gate="p1.2", host="fake", workspace=tmp_path)


def test_phase_one_offline_gates_use_existing_boundaries_and_are_idempotent(
    tmp_path: Path,
) -> None:
    p11 = run_phase_one_gate(gate="p1.1", host="fake", workspace=tmp_path)
    p12 = run_phase_one_gate(gate="p1.2", host="fake", workspace=tmp_path)
    p13 = run_phase_one_gate(gate="p1.3", host="fake", workspace=tmp_path)

    assert p11["status"] == p12["status"] == p13["status"] == "PASS"
    assert p11["evidence"]["accepted_episodes"] == 2
    assert p12["evidence"]["identity_adopted_from_host"] is True
    assert p12["evidence"]["post_correction_selected_routes"] == []
    assert p12["evidence"]["fork_inherited_identity"] is True
    assert p13["evidence"]["probe_count"] == 4
    assert p13["evidence"]["matched_readouts"] == 12
    assert p13["evidence"]["identity_enabled"] is False
    assert p13["evidence"]["checkpoint_file_unchanged"] is True
    assert p13["evidence"]["checkpoint_state_unchanged"] is True
    assert p13["evidence"]["idempotent_reentry_without_host_call"] is True

    # A later gate may advance the working store, but immutable gate evidence
    # remains loadable and the completed command does not execute it again.
    assert run_phase_one_gate(gate="p1.1", host="fake", workspace=tmp_path) == p11
    assert run_phase_one_gate(gate="p1.2", host="fake", workspace=tmp_path) == p12
    assert run_phase_one_gate(gate="p1.3", host="fake", workspace=tmp_path) == p13

    comparison = tmp_path / "p1.3" / "comparison" / "comparison.json"
    payload = json.loads(comparison.read_text(encoding="utf-8"))
    assert len(payload["results"]) == 12
    assert "output" not in payload["results"][0]


def test_phase_one_gate_rejects_changed_preceding_evidence(tmp_path: Path) -> None:
    run_phase_one_gate(gate="p1.1", host="fake", workspace=tmp_path)
    receipt = tmp_path / "p1.1" / "gate.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["artifact_inventory"]["p1.1/lineage.checkpoint.sqlite3"] = "0" * 64
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DemoError, match="integrity validation"):
        run_phase_one_gate(gate="p1.2", host="fake", workspace=tmp_path)


def test_phase_one_gate_does_not_claim_unsupported_live_execution(tmp_path: Path) -> None:
    with pytest.raises(DemoError, match="no host call was made"):
        run_phase_one_gate(
            gate="p1.1",
            host="gemma-deepinfra",
            live_budget="phase-one-v1",
            workspace=tmp_path,
        )
    assert not (tmp_path / "p1.1").exists()


def test_phase_one_cli_exposes_approved_gate_command(tmp_path: Path, capsys) -> None:
    assert (
        main(
            [
                "demo",
                "phase-one",
                "--gate",
                "p1.1",
                "--host",
                "fake",
                "--workspace",
                str(tmp_path),
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["gate"] == "p1.1"
    assert output["status"] == "PASS"
