from __future__ import annotations

from pathlib import Path

from mneme.experiments.contingent import (
    INTERLOPER_SYSTEM_PROMPT,
    ContingentSchedule,
    ContingentStudy,
    _bounded_pairs,
)
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
