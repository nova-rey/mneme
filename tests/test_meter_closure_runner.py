import copy
import json
from pathlib import Path

import pytest

from mneme.contracts import GenerationResult
from mneme.state.compact import CompactStore
from tools import run_meter_closure as runner


def plan():
    return json.loads(Path("docs/experiments/meter_closure/construction.json").read_text())


def result(content):
    return GenerationResult(content, "fixture", "test", {}, None, None, 0, "stop", {})


def test_bounded_plan_matches_domains_settings_and_budget():
    construction = plan()
    trajectories = construction["trajectories"]
    assert len(trajectories) == 4
    assert all(row["turns"] == 8 and len(row["ledger"]) == 7 for row in trajectories)
    assert construction["budget"]["max_calls"] == 5 * (8 + 8 + 7)
    assert construction["budget"]["requested_output_tokens_ceiling"] == 126080
    assert construction["budget"]["replacement_trajectories"] == 1
    for domain in ("network", "baking"):
        rows = [row for row in trajectories if row["domain"] == domain]
        assert rows[0]["opening"] == rows[1]["opening"]
        assert rows[0]["seed_domain_index"] == rows[1]["seed_domain_index"]
    previous = json.loads(Path("docs/experiments/three_pressure_v2/construction.json").read_text())
    assert construction["settings"] == previous["settings"]
    assert construction["context_policy"] == previous["context_policy"]


@pytest.mark.parametrize("change", ["number", "negation", "extra", "question", "private"])
def test_exact_gate_rejects_every_unapproved_change(change):
    ledger = {
        "required_facts": ["There were 0 resets. It is not wet."],
        "question": "What follows?",
    }
    original = runner.public_message(ledger)
    text = {
        "number": original.replace("0", "9"),
        "negation": original.replace("not ", ""),
        "extra": original + " I moved it.",
        "question": original.replace("What follows?", "What about a new sensor?"),
        "private": original + " The environment must be static.",
    }[change]
    assert runner.fact_gate(text, ledger)
    assert not runner.fact_gate(original.replace(" ", "\n"), ledger)


def test_shared_partner_request_is_private_and_has_same_branch():
    ledger = plan()["trajectories"][0]["ledger"][0]
    request = runner.quinn_request("opening", ledger, 2, [("last user", "last answer")])
    assert runner.public_message(ledger) in request.system
    assert request.parameters["max_new_tokens"] == 384
    assert request.parameters["reasoning_effort"] == "none"
    assert request.seed is None
    assert request.messages[0] == {"role": "assistant", "content": "last user"}
    replies = json.loads(request.messages[1]["content"].split("\n", 1)[1])
    assert replies["assistant_A"] == replies["assistant_B"] == "last answer"


@pytest.mark.parametrize("quinn_valid", [True, False])
def test_recorder_accepts_gemma_circling_and_only_gates_quinn(tmp_path, monkeypatch, quinn_valid):
    state = tmp_path / "state.sqlite3"
    store = CompactStore(state)
    store.close()
    digest = runner.file_digest(state)
    construction = copy.deepcopy(plan())
    construction["trajectories"] = construction["trajectories"][:1]
    construction["trajectories"][0]["turns"] = 3
    schedule = construction["trajectories"][0]
    called = []

    class Field:
        accessibility_distribution = ()
        payload = ""

        def to_dict(self):
            return {}

    class Evaluation:
        field = Field()

    monkeypatch.setattr(runner.CompactRuntime, "evaluate_saa", lambda *a, **kw: Evaluation())

    def forbidden(*args, **kwargs):
        raise AssertionError("developmental mutation")

    monkeypatch.setattr(CompactStore, "set_metadata", forbidden)
    monkeypatch.setattr(runner.CompactRuntime, "publish_state", forbidden)

    class Host:
        def __init__(self, role):
            self.role = role
            self.calls = 0

        def generate(self, request):
            called.append(self.role)
            self.calls += 1
            if self.role == "quinn":
                public = runner.public_message(schedule["ledger"][self.calls - 1])
                return result(public if quinn_valid else public + " I changed the setup.")
            if self.role == "extractor":
                raise ValueError("incomplete extraction is available as missing data")
            assert "private" not in request.system
            assert "moving" not in request.system
            return result("Instability to Silence. Complete Data Loss.")

    receipt = runner.run(
        tmp_path / "output",
        state,
        construction,
        budget_path=tmp_path / "budget.json",
        hosts={role: Host(role) for role in ("gemma", "extractor", "quinn")},
        preprocess=lambda messages: {"prompt_tokens": 10},
        expected_sha=digest,
    )
    assert receipt["unchanged"] and receipt["measurement_calls"] == 0
    assert receipt["accepted_turns"] == (3 if quinn_valid else 1)
    assert called == (
        ["gemma", "extractor", "quinn", "gemma", "extractor", "quinn", "gemma", "extractor"]
        if quinn_valid
        else ["gemma", "extractor", "quinn"]
    )
    records = runner.read_json(tmp_path / "output/records.json")
    assert all(row["residue"] is None for row in records)
    assert records[-1]["arc"]["turn_ids"] == [f"p001:turn:{i + 1}" for i in range(len(records))]
    assert runner.file_digest(state) == digest
    if not quinn_valid:
        rejected = runner.read_json(tmp_path / "output/rejections.json")
        assert rejected[0]["kind"] == "quinn_fidelity"
        assert rejected[0]["participant_text"].endswith("I changed the setup.")


def test_continuation_refuses_attempted_or_unknown_trajectories(tmp_path):
    state = tmp_path / "state.sqlite3"
    store = CompactStore(state)
    store.close()
    budget = tmp_path / "budget.json"
    budget.write_text(json.dumps({"calls": [{"coordinate": "prospective/p001-t01/gemma"}]}))
    for selected, message in [
        (("p001",), "previously attempted"),
        (("unknown",), "unknown selected"),
    ]:
        with pytest.raises((ValueError, RuntimeError), match=message):
            runner.run(
                tmp_path / "output",
                state,
                plan(),
                budget_path=budget,
                hosts={},
                preprocess=lambda messages: {},
                expected_sha=runner.file_digest(state),
                selected_ids=selected,
                run_key="untouched-continuation",
            )


def test_continuation_run_reservation_cannot_repeat(tmp_path):
    state = tmp_path / "state.sqlite3"
    store = CompactStore(state)
    store.close()
    construction = plan()
    budget = tmp_path / "budget.json"
    reservation = runner.CallBudget(budget, construction["budget"])
    reservation.register_run("main", tmp_path / "old")
    reservation.register_run("untouched-continuation", tmp_path / "first")
    with pytest.raises(RuntimeError, match="reserved"):
        runner.run(
            tmp_path / "new",
            state,
            construction,
            budget_path=budget,
            hosts={},
            preprocess=lambda messages: {},
            expected_sha=runner.file_digest(state),
            selected_ids=("p002",),
            run_key="untouched-continuation",
        )
