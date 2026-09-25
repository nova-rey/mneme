from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from mneme.contracts import GenerationResult
from mneme.experiments.contingent import (
    INTERLOPER_SYSTEM_PROMPT,
    ContingentSchedule,
    ContingentStudy,
    ContingentStudyError,
    _attractor_risk,
    _bounded_pairs,
    _interloper_executive_state,
    _interloper_history,
    _measurement_counters,
    _measurement_stop,
    _payload,
    _restored_interpretation,
    _subject_history,
)
from mneme.experiments.p23_supplement import (
    SUPPLEMENT_ID,
    P23SupplementStudy,
    SupplementSchedule,
)
from mneme.experiments.pilot import PilotStatus
from mneme.hosts import FakeHost


def test_p23_supplement_freezes_one_lineage_schedule_and_role_audit(tmp_path: Path) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = FakeHost(model_id="qwen-test")
    study = P23SupplementStudy.create(
        tmp_path / "lab", gemma, qwen, qwen, gemma, run_id="p23-supplement-test"
    )
    experiment = study.pilot.artifacts._read_json(study.pilot.run_path / "experiment.json")
    assert experiment["name"] == SUPPLEMENT_ID
    assert len(SupplementSchedule.fixed().turns) == 12
    audit = study.pilot.artifacts._read_json(
        study.pilot.run_path / "receipts" / "role-serialization-preflight.json"
    )
    assert audit["assertions"] == {
        "gemma_assistant_is_gemma": True,
        "gemma_user_is_interloper": True,
        "qwen_assistant_is_interloper": True,
        "qwen_user_is_gemma": True,
    }
    request = study._interloper_request(
        "supplement", 1, [("participant", "Gemma response")], current_prompt="private circumstance"
    )
    assert "CURRENT PRIVATE CIRCUMSTANCE" in (request.system or "")
    assert "private circumstance" in (request.system or "")


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
    assert len(messages) == 4
    assert messages[0] == {"role": "user", "content": "u4"}
    assert messages[-1] == {"role": "assistant", "content": "a5"}
    assert all(message["role"] in {"user", "assistant"} for message in messages)


def test_perspective_specific_history_renderers_reverse_roles() -> None:
    pairs = [
        ("Qwen says hello", "Gemma answers hello"),
        ("Qwen asks about dinner", "Gemma ends layered with smoked"),
    ]
    assert _subject_history(pairs) == [
        {"role": "user", "content": "Qwen says hello"},
        {"role": "assistant", "content": "Gemma answers hello"},
        {"role": "user", "content": "Qwen asks about dinner"},
        {"role": "assistant", "content": "Gemma ends layered with smoked"},
    ]
    assert _interloper_history(pairs) == [
        {"role": "assistant", "content": "Qwen says hello"},
        {"role": "user", "content": "Gemma answers hello"},
        {"role": "assistant", "content": "Qwen asks about dinner"},
        {"role": "user", "content": "Gemma ends layered with smoked"},
    ]


def test_lentil_incident_attractor_gets_private_escape_state(tmp_path: Path) -> None:
    pairs = [
        ("I am here.", "We stay."),
        ("Enough.", "We remain."),
    ]
    schedule = ContingentSchedule.fixed()
    state = _interloper_executive_state(schedule, 8, pairs)
    assert _attractor_risk(pairs, 8) in {"elevated", "high"}
    assert state.environment == "balcony plants during hot weather"
    assert state.transition_approaching is False
    assert "basil" in " ".join(state.private_concerns)
    assert "expensive equipment" in state.prompt_text()

    gemma = FakeHost(model_id="gemma-test")
    qwen = FakeHost(model_id="qwen-test")
    study = ContingentStudy.create(tmp_path / "lab", gemma, qwen, qwen, gemma)
    request = study._interloper_request(
        "interactive", 8, pairs, latest_user_message="Gemma current reply"
    )
    assert len(request.messages) == 5
    assert request.messages[-1] == {
        "role": "user",
        "content": "Gemma current reply",
    }
    assert "PRIVATE EXECUTIVE STATE" in (request.system or "")
    assert "balcony plants during hot weather" in (request.system or "")
    assert "basil" in (request.system or "")
    assert "desired associations" in (request.system or "")
    assert "experimental conversational assistant" not in (request.system or "")
    assert "We are studying conversations" not in (request.system or "")
    result = qwen.generate(request)
    assert result.content


def test_serialized_requests_use_the_generating_model_perspective(tmp_path: Path) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = FakeHost(model_id="qwen-test")
    study = ContingentStudy.create(tmp_path / "lab", gemma, qwen, qwen, gemma)
    pairs = [("Qwen asks", "Gemma answers"), ("Qwen follows up", "layered with smoked")]
    gemma_request = study._subject_request(pairs, "new Qwen message", "interactive", 2)
    qwen_request = study._interloper_request(
        "interactive", 2, pairs, latest_user_message="Newest Gemma response"
    )
    assert gemma_request.to_dict()["messages"] == [
        {"role": "user", "content": "Qwen asks"},
        {"role": "assistant", "content": "Gemma answers"},
        {"role": "user", "content": "Qwen follows up"},
        {"role": "assistant", "content": "layered with smoked"},
        {"role": "user", "content": "new Qwen message"},
    ]
    assert qwen_request.to_dict()["messages"] == [
        {"role": "assistant", "content": "Qwen asks"},
        {"role": "user", "content": "Gemma answers"},
        {"role": "assistant", "content": "Qwen follows up"},
        {"role": "user", "content": "layered with smoked"},
        {"role": "user", "content": "Newest Gemma response"},
    ]
    assert qwen_request.to_dict()["messages"][-1] == {
        "role": "user",
        "content": "Newest Gemma response",
    }
    assert gemma_request.system is None
    assert "experimental conversational assistant" not in str(gemma_request.to_dict())


def test_blank_interloper_result_is_persisted_then_rejected(tmp_path: Path) -> None:
    class BlankHost(FakeHost):
        def generate(self, request):  # type: ignore[no-untyped-def]
            return replace(super().generate(request), content="")

    gemma = FakeHost(model_id="gemma-test")
    blank = BlankHost(model_id="qwen-test")
    study = ContingentStudy.create(tmp_path / "lab", gemma, blank, blank, gemma)
    study.pilot.begin_qualification()
    study.pilot._write_state(PilotStatus.QUALIFIED, qualification={"status": "PASS"})
    study.pilot.begin_pilot()
    request = study._interloper_request("interactive", 0, (), initial_prompt="start")
    try:
        study._partner_call("interactive", 0, request)
    except Exception as exc:
        assert "blank interloper generation" in str(exc)
    else:
        raise AssertionError("blank interloper output must be rejected")
    assert (study.pilot._reservation_path("interloper-interactive-t00")).is_file()
    assert (study.root / "interloper-interactive-t00-invalid.json").is_file()


class _SequenceInterloperHost(FakeHost):
    def __init__(self, outputs: list[str]) -> None:
        super().__init__(model_id="qwen-sequence")
        self.outputs = outputs

    def generate(self, request):  # type: ignore[no-untyped-def]
        result = super().generate(request)
        content = self.outputs.pop(0) if self.outputs else ""
        return GenerationResult(
            content,
            result.model_id,
            result.provider,
            result.effective_parameters,
            result.seed,
            result.token_usage,
            result.latency_ms,
            result.finish_reason,
            result.raw_metadata,
            result.provenance,
        )


def test_supplement_empty_interloper_hard_stops_before_gemma(tmp_path: Path) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = _SequenceInterloperHost(["", ""])
    study = P23SupplementStudy.create(
        tmp_path / "lab", gemma, qwen, qwen, gemma, run_id="p23-empty-stop"
    )
    study.schedule = SupplementSchedule((SupplementSchedule.fixed().turns[0],))

    report = study.execute()

    assert report["terminal_result"] == "INVALID"
    assert report["interloper_recovery_attempts"] == 1
    assert report["hard_stop_reason"]
    assert report["records"][0]["downstream_status"] == "invalid_environment_empty_interloper"
    assert len(report["reservations"]["calls"]) == 2
    assert all(call["role"] == "interloper" for call in report["reservations"]["calls"])
    assert not list(study.subjects[0].store.connection.execute("SELECT 1 FROM episodes"))
    assert not (study.root / "interloper-supplement-t01.json").exists()


def test_supplement_empty_interloper_one_recovery_reuses_coordinate(tmp_path: Path) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = _SequenceInterloperHost(["   \n", "A practical participant message."])
    study = P23SupplementStudy.create(
        tmp_path / "lab", gemma, qwen, qwen, gemma, run_id="p23-empty-recovery"
    )
    study.schedule = SupplementSchedule((SupplementSchedule.fixed().turns[0],))

    report = study.execute()

    assert report["terminal_result"] == "NOT_DEMONSTRATED"
    assert report["records"][0]["interloper_recovery_attempts"] == 1
    assert report["records"][0]["partner"] == "A practical participant message."
    calls = report["reservations"]["calls"]
    call_ids = {call["call_id"] for call in calls}
    assert call_ids == {
        "interloper-supplement-t00",
        "interloper-supplement-t00-recovery-1",
        "development-supplement-t00",
        "extraction-supplement-t00",
    }
    initial = next(call for call in calls if call["call_id"] == "interloper-supplement-t00")
    recovery = next(
        call for call in calls if call["call_id"] == "interloper-supplement-t00-recovery-1"
    )
    assert recovery["coordinate"]["turn"] == initial["coordinate"]["turn"] == 0
    assert not any(record["partner"] == "" for record in report["records"])


def test_payload_preserves_provider_metadata_for_blank_forensics() -> None:
    result = GenerationResult(
        "",
        "qwen-test",
        "DeepInfra",
        {"max_tokens": 256},
        None,
        None,
        0.0,
        "stop",
        {"choices": [{"message": {"content": "", "reasoning_content": "hidden"}}]},
        {"host": {"model_id": "qwen-test"}},
    )
    payload = _payload(result)
    assert payload["content"] == ""
    assert payload["finish_reason"] == "stop"
    assert payload["raw_metadata"]["choices"][0]["message"]["reasoning_content"] == "hidden"


def test_open_loop_stop_publishes_partial_transcript(tmp_path: Path, monkeypatch) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = FakeHost(model_id="qwen-test")
    study = ContingentStudy.create(tmp_path / "lab", gemma, qwen, qwen, gemma)
    study.schedule = ContingentSchedule(
        (
            ContingentSchedule.fixed().turns[0],
            ContingentSchedule.fixed().turns[1],
        )
    )
    results = iter(("first participant message",))

    def partner_call(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        try:
            return next(results)
        except StopIteration as exc:
            raise ContingentStudyError("simulated blank-turn stop") from exc

    monkeypatch.setattr(study, "_partner_call", partner_call)
    with pytest.raises(ContingentStudyError, match="blank-turn stop"):
        study._generate_open_loop_messages()
    transcript = (study.root / "conversation-transcript-open-loop.md").read_text()
    assert "first participant message" in transcript
    assert "Turn 0" in transcript


def test_attractor_detector_marks_late_low_novelty_window() -> None:
    pairs = [
        ("we stay here", "we remain here"),
        ("still here", "we stay"),
    ]
    assert _attractor_risk(pairs, 12) in {"elevated", "high"}


def test_interloper_request_discards_older_stylistic_context(tmp_path: Path) -> None:
    gemma = FakeHost(model_id="gemma-test")
    qwen = FakeHost(model_id="qwen-test")
    study = ContingentStudy.create(tmp_path / "lab", gemma, qwen, qwen, gemma)
    pairs = [(f"old{i}", f"old-answer{i}") for i in range(5)]
    request = study._interloper_request(
        "interactive",
        8,
        pairs,
    )
    contents = [str(message["content"]) for message in request.messages]
    assert contents == ["old3", "old-answer3", "old4", "old-answer4"]


def test_interloper_prompt_forbids_fabricated_open_loop_answers() -> None:
    assert "Do not invent an answer" in INTERLOPER_SYSTEM_PROMPT
    assert "Write only your next participant message" in INTERLOPER_SYSTEM_PROMPT
    assert "maintaining your own conversational" in INTERLOPER_SYSTEM_PROMPT
    assert "Do not repeatedly mirror, praise, or intensify" in INTERLOPER_SYSTEM_PROMPT
    assert "return to" in INTERLOPER_SYSTEM_PROMPT


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


def test_reviewed_continuation_evaluates_post_correction_segment_only() -> None:
    historical = [
        {"turn": turn, "trustworthy_interpretation": turn not in {3, 5, 8}}
        for turn in range(9)
    ]
    post_correction = [
        {"turn": 9, "trustworthy_interpretation": True},
        {"turn": 10, "trustworthy_interpretation": True},
    ]
    all_records = historical + post_correction
    counters = _measurement_counters(
        all_records,
        measurement_segment=post_correction,
    )
    assert counters["attempted_developmental_turns"] == 11
    assert counters["successfully_interpreted_turns"] == 8
    assert counters["stop_reason"] is None
    assert counters["post_correction"]["attempted_developmental_turns"] == 2
    assert counters["post_correction"]["successfully_interpreted_turns"] == 2
    assert counters["post_correction"]["interpretation_success_rate"] == 1.0


def test_reviewed_segment_requires_preserved_resume_turn() -> None:
    from mneme.experiments.contingent import _reviewed_segment_start

    assert (
        _reviewed_segment_start(
            {
                "measurement_review": {
                    "status": "APPROVED_CONTINUATION",
                    "resume_turn": 9,
                }
            },
            "interactive",
        )
        == 9
    )
    assert _reviewed_segment_start({}, "interactive") is None
    assert _reviewed_segment_start(
        {"measurement_review": {"status": "APPROVED_CONTINUATION", "resume_turn": 9}},
        "open-loop",
    ) is None


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
