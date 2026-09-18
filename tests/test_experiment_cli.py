"""P0.4 execution/report command wiring tests.

These tests intentionally stub the runner and reporter.  Execution semantics
belong to those modules; the CLI contract only needs to pass the prepared run
identity, laboratory root, optional test host, and report destination exactly
once.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

from mneme.cli import main
from mneme.experiments.cli import add_parser, dispatch, normalize_args


def test_execute_and_baseline_commands_parse_and_normalize(tmp_path: Path) -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    add_parser(sub)

    execute = parser.parse_args(
        ["experiment", "run", "execute", "run-1", "--lab", str(tmp_path), "--host", "fake"]
    )
    execute = normalize_args(execute)
    assert execute.experiment_action == "run_execute"
    assert execute.run_id == "run-1"
    assert execute.host == "fake"

    report = parser.parse_args(
        [
            "experiment",
            "baseline",
            "report",
            "run-1",
            "--lab",
            str(tmp_path),
            "--output",
            str(tmp_path / "baseline.json"),
        ]
    )
    report = normalize_args(report)
    assert report.experiment_action == "baseline_report"
    assert report.output == tmp_path / "baseline.json"


def test_execute_dispatches_to_integrated_runner(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, str | None]] = []

    def execute_run(*, run_id: str, lab: Path, host_name: str | None) -> dict[str, object]:
        calls.append((run_id, str(lab), host_name))
        return {"status": "COMPLETE", "run_id": run_id}

    monkeypatch.setitem(
        sys.modules,
        "mneme.experiments.runner",
        SimpleNamespace(execute_run=execute_run),
    )
    result = dispatch(
        SimpleNamespace(
            experiment_action="run_execute",
            run_id="run-1",
            lab=tmp_path,
            host="fake",
        )
    )
    assert result == 0
    assert calls == [("run-1", str(tmp_path), "fake")]
    assert '"status": "COMPLETE"' in capsys.readouterr().out


def test_resume_dispatches_to_integrated_runner(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, str | None]] = []

    def resume_run(*, run_id: str, lab: Path, host_name: str | None) -> dict[str, object]:
        calls.append((run_id, str(lab), host_name))
        return {"status": "PAUSED", "run_id": run_id}

    monkeypatch.setitem(
        sys.modules,
        "mneme.experiments.runner",
        SimpleNamespace(resume_run=resume_run),
    )
    assert (
        dispatch(
            SimpleNamespace(
                experiment_action="run_resume",
                run_id="run-1",
                lab=tmp_path,
                host=None,
            )
        )
        == 0
    )
    assert calls == [("run-1", str(tmp_path), None)]


def test_baseline_report_writes_requested_machine_readable_output(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    report_path = tmp_path / "baseline.json"

    def build_report(*, run_id: str, lab: Path) -> dict[str, object]:
        assert run_id == "run-1"
        assert lab == tmp_path
        return {"status": "COMPLETE", "run_id": run_id, "within_instance": {"agreement": 1.0}}

    monkeypatch.setitem(
        sys.modules,
        "mneme.experiments.baseline",
        SimpleNamespace(build_report=build_report),
    )
    assert (
        dispatch(
            SimpleNamespace(
                experiment_action="baseline_report",
                run_id="run-1",
                lab=tmp_path,
                output=report_path,
            )
        )
        == 0
    )
    assert report_path.is_file()
    assert '"agreement": 1.0' in report_path.read_text()
    assert '"output":' in capsys.readouterr().out


def test_top_level_cli_exposes_execute_parser(tmp_path: Path, monkeypatch, capsys) -> None:
    def execute_run(*, run_id: str, lab: Path, host_name: str | None) -> dict[str, object]:
        return {"status": "COMPLETE", "run_id": run_id, "host": host_name}

    monkeypatch.setitem(
        sys.modules,
        "mneme.experiments.runner",
        SimpleNamespace(execute_run=execute_run),
    )
    assert (
        main(
            [
                "experiment",
                "run",
                "execute",
                "run-1",
                "--lab",
                str(tmp_path),
                "--host",
                "fake",
            ]
        )
        == 0
    )
    assert '"run_id": "run-1"' in capsys.readouterr().out
