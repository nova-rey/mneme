from __future__ import annotations

import json
from pathlib import Path

import pytest

from mneme.cli import main
from mneme.demo import DemoError, _ResidueFixtureHost, run_phase_one_gate
from mneme.live_phase_one import LivePhaseOneError, _name_matches, run_live_phase_one


def test_live_name_recovery_accepts_display_spacing_without_broadening_identity() -> None:
    assert _name_matches("Gemma4", "Gemma 4") is True
    assert _name_matches("Gemma4", "My adopted name is Gemma 4.") is True
    assert _name_matches("Gemma4", "Gemma 40") is False
    assert _name_matches("Gemma4", "I do not have a name") is False


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
    assert p12["evidence"]["selected_routes"]
    assert p12["evidence"]["correction_directive_id"]
    assert p12["evidence"]["selected_routes"][0] not in p12["evidence"][
        "post_correction_selected_routes"
    ]
    assert p12["evidence"]["fork_inherited_identity"] is True
    assert p13["evidence"]["probe_count"] == 4
    assert p13["evidence"]["matched_readouts"] == 12
    assert p13["evidence"]["identity_enabled"] is False
    assert p13["evidence"]["authored_control_route"] == "authored-control-route"
    assert p13["evidence"]["authored_control_child"].endswith("authored-control.sqlite3")
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


def test_phase_one_gate_rejects_live_gate_when_started_at_p12(tmp_path: Path) -> None:
    with pytest.raises(DemoError, match="single P1.1.*P1.2.*P1.3"):
        run_phase_one_gate(
            gate="p1.2",
            host="gemma-deepinfra",
            live_budget="phase-one-v1",
            workspace=tmp_path,
        )
    assert not (tmp_path / "live_summary.json").exists()


def test_live_driver_completes_bounded_fake_control_and_is_restart_auditable(
    tmp_path: Path,
) -> None:
    report = run_live_phase_one(
        tmp_path,
        live_budget="phase-one-v1",
        host=_ResidueFixtureHost(),
    )
    assert report["status"] == "PASS"
    assert report["provider_calls"] == 23
    assert {gate: value["status"] for gate, value in report["gates"].items()} == {
        "p1.1": "PASS",
        "p1.2": "PASS",
        "p1.3": "PASS",
    }
    assert any(
        len(route["edge_keys"]) >= 2 for route in report["gates"]["p1.1"]["multi_hop_routes"]
    )
    assert report["gates"]["p1.2"]["checkpoint_unchanged"] is True
    assert report["gates"]["p1.3"]["completed_reentry_host_free"] is True
    assert (tmp_path / "live_summary.json").is_file()


def test_live_driver_persists_uncertain_dispatch_without_retry(tmp_path: Path) -> None:
    class UncertainHost(_ResidueFixtureHost):
        def generate(self, request):
            raise TimeoutError("simulated interruption")

    with pytest.raises(LivePhaseOneError, match="simulated interruption"):
        run_live_phase_one(
            tmp_path,
            live_budget="phase-one-v1",
            host=UncertainHost(),
        )
    report = json.loads((tmp_path / "live_summary.json").read_text(encoding="utf-8"))
    assert report["provider_calls"] == 1
    assert report["calls"][0]["status"] == "UNCERTAIN"


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
