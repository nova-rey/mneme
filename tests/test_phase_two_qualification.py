from __future__ import annotations

import json
from pathlib import Path

from mneme.contracts import GenerationRequest, GenerationResult, TokenUsage
from mneme.development.assessment import qualification_cases
from mneme.experiments.artifacts import ArtifactStore
from mneme.experiments.pilot import PilotRun, PilotStatus
from mneme.experiments.qualification import run_assessor_qualification
from mneme.hosts import FakeHost


def _pilot(tmp_path: Path) -> PilotRun:
    store = ArtifactStore(tmp_path / "lab")
    store.publish_run(
        experiment={"name": "p2-qualification", "contract_revision": 1},
        preflight={"valid": True},
        study_plan={"budgets": {}},
        bindings={"subjects": []},
        run_id="run-1",
    )
    pilot = PilotRun(store, "run-1")
    pilot.prepare(planned_calls=3, max_output_tokens=4_608, qualification_calls=3)
    return pilot


def _results() -> dict[str, str]:
    outputs: dict[str, str] = {}
    for case in qualification_cases():
        rows = []
        for monitor in case.request.monitors:
            expected = case.expected[monitor.monitor_id]
            row: dict[str, object] = {
                "monitor_id": monitor.monitor_id,
                "status": expected.get("status", "unknown"),
                "relation_support": expected.get("relation_support", "unknown"),
                "expression_status": expected.get("expression_status", "unknown"),
                "dependence": expected.get("dependence", "unknown"),
                "coverage": {"complete": False, "source_slots": [], "reason": "unavailable"},
                "evidence": None,
            }
            if row["status"] == "present":
                source = monitor.required_source_slots[0]
                text = next(item.text for item in case.request.sources if item.slot == source)
                row["coverage"] = {
                    "complete": True,
                    "source_slots": list(monitor.required_source_slots),
                    "reason": None,
                }
                row["evidence"] = {"source_slot": source, "quote": text}
            elif row["status"] == "absent":
                row["coverage"] = {
                    "complete": True,
                    "source_slots": list(monitor.required_source_slots),
                    "reason": "not expressed",
                }
            rows.append(row)
        outputs[case.case_id] = json.dumps(
            {"schema_version": "p2-assessor-v1", "assessments": rows}
        )
    return outputs


class ScriptedHost(FakeHost):
    def __init__(self, outputs: dict[str, str]) -> None:
        super().__init__()
        self.outputs = outputs
        self.ordinal = 0

    def generate(self, request: GenerationRequest) -> GenerationResult:
        case_id = f"Q{self.ordinal + 1}"
        self.ordinal += 1
        content = self.outputs[case_id]
        return GenerationResult(
            content,
            self.model_id,
            "builtin",
            dict(request.parameters),
            None,
            TokenUsage(10, len(content.split()), 10 + len(content.split())),
            0.0,
            "stop",
            {},
            {"host": self.fingerprint().to_dict()},
        )


def test_qualification_persists_results_before_validation_and_passes(tmp_path: Path) -> None:
    pilot = _pilot(tmp_path)
    result = run_assessor_qualification(pilot, ScriptedHost(_results()))
    assert result["status"] == PilotStatus.QUALIFIED.value
    assert [item["valid"] for item in result["cases"]] == [True, True, True]
    report = PilotRun(pilot.artifacts, "run-1").reservations_report()
    assert report["counts"]["RETURNED"] == 3
    assert all(
        (pilot.run_path / "qualification" / f"q{ordinal}.json").is_file()
        for ordinal in range(1, 4)
    )


def test_invalid_qualification_is_retained_and_does_not_retry(tmp_path: Path) -> None:
    outputs = _results()
    outputs["Q2"] = "```json\n{}\n```"
    pilot = _pilot(tmp_path)
    result = run_assessor_qualification(pilot, ScriptedHost(outputs))
    assert result["status"] == PilotStatus.FAILED.value
    assert result["cases"][1]["valid"] is False
    assert PilotRun(pilot.artifacts, "run-1").reservations_report()["counts"]["RETURNED"] == 3
