from __future__ import annotations

from pathlib import Path

from mneme.experiments.contingent import (
    INTERLOPER_SYSTEM_PROMPT,
    ContingentSchedule,
    ContingentStudy,
    _bounded_pairs,
    _measurement_counters,
    _measurement_stop,
    _restored_interpretation,
)
from mneme.experiments.pilot import PilotStatus
from mneme.hosts import FakeHost


def test_schedule_has_distinct_chapters_and_24_turns() -> None:
    schedule = ContingentSchedule.fixed()
    assert len(schedule.turns) == 24
    assert [turn.chapter for turn in schedule.turns[0:8]] == ["A"] * 8
    assert [turn.chapter for turn in schedule.turns[8:16]] == ["B"] * 8
    assert [turn.chapter for turn in schedule.turns[16:24]] == ["C"] * 8
    assert schedule.turns[0].prompt != schedule.turns[8].prompt
    assert schedule.turns[8].prompt != schedule.turns[16].prompt


def test_bounded_context_contains_only_complete_recent_pairs() -> None:
    pairs = [(f"u{i}", f"a{i}") for i in range(6)]
    messages = _bounded_pairs(pairs)
    assert len(messages) == 8
    assert messages[0] == {"role": "user", "content": "u2"}
    assert messages[-1] == {"role": "assistant", "content": "a5"}
    assert all(message["role"] in {"user", "assistant"} for message in messages)


def test_interloper_prompt_forbids_fabricated_open_loop_answers() -> None:
    assert "Do not invent an answer" in INTERLOPER_SYSTEM_PROMPT
    assert "Write only your next participant message" in INTERLOPER_SYSTEM_PROMPT


def test_create_binds_partner_and_assessor_as_separate_roles(tmp_path: Path) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = FakeHost(model_id="qwen-test")
    study = ContingentStudy.create(tmp_path / "lab", gemma, qwen, qwen, gemma)
    state = study.pilot.status()
    bindings = state["envelope"]["role_bindings"]
    assert bindings["interloper"]["role"] == "interloper"
    assert bindings["assessor"]["role"] == "assessor"
    assert (
        bindings["interloper"]["fingerprint_sha256"] == bindings["assessor"]["fingerprint_sha256"]
    )
    assert bindings["interloper"]["role"] != bindings["assessor"]["role"]
    assert study.pilot.contract_digest


def test_subject_requests_carry_environment_origin_without_admin_ids(tmp_path: Path) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = FakeHost(model_id="qwen-test")
    study = ContingentStudy.create(tmp_path / "lab", gemma, qwen, qwen, gemma)
    request = study._subject_request([], "A partner message", "interactive", 0)
    assert request.run_metadata["environment_origin"] == "synthetic_environment_model"
    material = request.generation_material()
    assert "contingent-run-1" not in str(material)
    assert "interactive" not in str(material)


def test_terminal_interpretation_failure_is_missing_measurement_only() -> None:
    records = [
        {
            "trustworthy_interpretation": False,
            "downstream_status": "measurement_unknown / interpretation_unavailable",
            "failure_kind": "extraction",
        }
    ]
    counters = _measurement_counters(records)
    assert counters["attempted_developmental_turns"] == 1
    assert counters["terminal_unknown_turns"] == 1
    assert counters["extraction_failures"] == 1
    assert counters["successfully_interpreted_turns"] == 0
    assert counters["interpretation_success_rate"] == 0.0
    assert _measurement_stop(records) is None


def test_restart_does_not_promote_failed_assessment_to_trustworthy() -> None:
    status, trustworthy, failure_kind, reason = _restored_interpretation(
        valid_extraction=True,
        assessment={"valid": False, "validation_error": "missing monitor row"},
    )
    assert status == "measurement_unknown / interpretation_unavailable"
    assert trustworthy is False
    assert failure_kind == "assessment"
    assert reason == "missing monitor row"


def test_restart_accepts_valid_extraction_without_assessment_call() -> None:
    status, trustworthy, failure_kind, reason = _restored_interpretation(
        valid_extraction=True,
        assessment=None,
    )
    assert status == "complete"
    assert trustworthy is True
    assert failure_kind is None
    assert reason is None


def test_measurement_stop_requires_three_consecutive_or_low_rate_failures() -> None:
    assert _measurement_stop(
        [{"trustworthy_interpretation": False}] * 3
    ) == "three_consecutive_interpretation_failures"
    mixed = [{"trustworthy_interpretation": True}] * 5 + [
        {"trustworthy_interpretation": False},
        {"trustworthy_interpretation": True},
        {"trustworthy_interpretation": False},
    ]
    assert _measurement_stop(mixed) is None
    low_rate = [{"trustworthy_interpretation": True}] * 6 + [
        {"trustworthy_interpretation": False},
        {"trustworthy_interpretation": True},
        {"trustworthy_interpretation": False},
        {"trustworthy_interpretation": True},
        {"trustworthy_interpretation": False},
    ]
    assert _measurement_stop(low_rate) == "interpretation_success_rate_below_75_percent"


def test_transcript_snapshot_preserves_exact_conversational_text(tmp_path: Path) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = FakeHost(model_id="qwen-test")
    study = ContingentStudy.create(tmp_path / "lab", gemma, qwen, qwen, gemma)
    study._publish_transcript(
        condition="interactive",
        fit_records=[
            {"turn": 0, "preceding_reply": "fit reply", "message": "fit message"}
        ],
        records=[
            {
                "turn": 5,
                "chapter": "A",
                "partner": "exact partner — text",
                "subject": "exact Gemma response",
                "development_accepted": True,
                "downstream_status": "measurement_unknown / interpretation_unavailable",
                "failure_reason": "provider content is not JSON",
            }
        ],
    )
    transcript = (study.root / "conversation-transcript-interactive.md").read_text(
        encoding="utf-8"
    )
    assert "exact partner — text" in transcript
    assert "exact Gemma response" in transcript
    assert "measurement_unknown / interpretation_unavailable" in transcript
    assert "provider content is not JSON" in transcript


def test_measurement_stop_is_not_automatically_resumed(tmp_path: Path) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = FakeHost(model_id="qwen-test")
    study = ContingentStudy.create(tmp_path / "lab", gemma, qwen, qwen, gemma)
    study.pilot.begin_qualification()
    study.pilot._write_state(PilotStatus.QUALIFIED, qualification={"status": "PASS"})
    study.pilot.begin_pilot()
    study.pilot._write_state(
        PilotStatus.PAUSED,
        study_progress={"stop_reason": "interpretation_success_rate_below_75_percent"},
    )
    try:
        study.execute()
    except Exception as exc:
        assert "measurement review" in str(exc)
    else:
        raise AssertionError("a measurement stop must require review before resumption")
