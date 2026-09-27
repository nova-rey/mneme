from __future__ import annotations

from typing import Any

from tools.run_p23_saa_ten_thread_live import _record_measurement_unknown


class _Pilot:
    def __init__(self) -> None:
        self.artifacts: list[tuple[str, str, dict[str, Any]]] = []

    def publish_artifact(self, category: str, name: str, value: dict[str, Any]) -> None:
        self.artifacts.append((category, name, value))


def test_assessor_validation_miss_is_recorded_without_credit_or_absence() -> None:
    pilot = _Pilot()

    _record_measurement_unknown(
        pilot,
        call_id="assess-T04-7",
        coordinate={"thread": "T04", "turn": 7},
        operation_id="development-SAA-T04-7",
        validation_error="invalid monitor row",
    )

    assert len(pilot.artifacts) == 1
    category, name, receipt = pilot.artifacts[0]
    assert category == "assessment"
    assert name == "assess-T04-7-measurement-unknown.json"
    assert receipt["status"] == "measurement_unknown / interpretation_unavailable"
    assert receipt["admitted_relationships"] == 0
    assert receipt["learner_credit"] == 0
    assert receipt["absence_evidence"] is False
    assert receipt["validation_error"] == "invalid monitor row"
