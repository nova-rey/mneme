import hashlib
import json

import pytest

from mneme.contracts import Capability
from mneme.experiments.datasets import (
    DatasetRecord,
    family_membership_digest,
    ordered_content_digest,
)
from mneme.experiments.planning import PreflightError, SeedDomain, derive_seed, preflight
from mneme.hosts.fake import FakeHost


def spec() -> dict:
    return {
        "name": "shared-input-control",
        "contract_revision": 3,
        "randomization": {"master_seed": 17},
        "subjects": [
            {"slot": 0, "cohort": "shared", "condition": "common", "development_sampling_slot": 0},
            {"slot": 1, "cohort": "shared", "condition": "common", "development_sampling_slot": 1},
        ],
        "conditions": {"common": {"development_dataset": "dev"}},
        "evaluation": {"dataset": "eval", "repetitions": 2},
        "datasets": {
            "dev": [{"id": "d0", "input_tokens": 3, "max_output_tokens": 4}],
            "eval": [{"id": "e0", "input_tokens": 5, "max_output_tokens": 6}],
        },
        "host": {"requires": ["text_generation", "seed_control"]},
        "generation": {"parameters": {"max_new_tokens": 8}},
        "budgets": {
            "max_model_calls": 8,
            "max_input_tokens": 32,
            "max_output_tokens": 40,
            "max_isolation_check_calls": 1,
        },
    }


def test_seed_derivation_is_stable_and_domain_separated() -> None:
    first = derive_seed(
        17, SeedDomain.DEVELOPMENT_GENERATION, sampling_slot=0, episode=0, repetition=0
    )
    second = derive_seed(
        17, SeedDomain.DEVELOPMENT_GENERATION, sampling_slot=0, episode=0, repetition=0
    )
    other = derive_seed(
        17, SeedDomain.EVALUATION_GENERATION, probe=0, checkpoint_boundary=0, repetition=0
    )
    assert first == second
    assert first != other
    with pytest.raises(PreflightError):
        derive_seed(17, "development_generation", run_id="run-1")
    with pytest.raises(PreflightError, match="unsupported seed domain"):
        derive_seed(17, "future_domain", slot=0)
    with pytest.raises(PreflightError, match="exactly"):
        derive_seed(17, SeedDomain.DEVELOPMENT_GENERATION, sampling_slot=0)


def test_preflight_resolves_without_calling_host() -> None:
    plan = preflight(spec(), FakeHost(), contract_digest="abc")
    assert plan.experiment_name == "shared-input-control"
    assert plan.contract_revision == 3
    assert plan.contract_digest == "abc"
    assert plan.budget.development_calls == 2
    assert plan.budget.evaluation_calls == 4
    assert plan.budget.total_calls == 7
    assert {item["domain"] for item in plan.streams} == {
        "development_generation",
        "evaluation_generation",
        "condition_assignment",
        "dataset_ordering",
    }
    assert plan.host["capabilities"] == sorted(c.value for c in FakeHost().capabilities().supported)


def test_preflight_rejects_missing_capability() -> None:
    host = FakeHost(omit_capabilities=frozenset({Capability.SEED_CONTROL}))
    with pytest.raises(PreflightError, match="seed_control"):
        preflight(spec(), host)


def test_preflight_rejects_budget_overflow() -> None:
    value = spec()
    value["budgets"]["max_model_calls"] = 5
    with pytest.raises(PreflightError, match="max_model_calls"):
        preflight(value, FakeHost())


def test_preflight_rejects_unbounded_token_budget() -> None:
    value = spec()
    value["datasets"]["eval"] = [{"id": "e0", "max_output_tokens": 2}]
    with pytest.raises(PreflightError, match="input_tokens"):
        preflight(value, FakeHost())


def test_preflight_rejects_missing_checkpoint_binding(tmp_path) -> None:
    value = spec()
    for subject in value["subjects"]:
        subject["start"] = "start"
    value["checkpoints"] = {
        "start": {
            "path": str(tmp_path / "missing.sqlite3"),
            "checkpoint_id": "cp",
            "instance_id": "instance",
            "revision": 0,
            "manifest_id": "manifest",
            "sha256": "0" * 64,
        }
    }
    with pytest.raises(PreflightError, match="does not exist"):
        preflight(value, FakeHost())


def test_seed_does_not_depend_on_subject_slot_for_paired_evaluation() -> None:
    value = spec()
    plan = preflight(value, FakeHost())
    eval_seeds = [
        item["seed"] for item in plan.streams if item["domain"] == "evaluation_generation"
    ]
    assert eval_seeds[0] == eval_seeds[2]


def test_preflight_loads_fixture_pack_relative_to_contract(tmp_path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    records = [
        {
            "record_id": "dev-0",
            "ordinal": 0,
            "scenario_family": "dev-family",
            "messages": [{"role": "user", "content": "development"}],
            "partition": "engineering",
            "role": "development",
            "input_tokens": 2,
            "max_output_tokens": 3,
        },
        {
            "record_id": "eval-0",
            "ordinal": 0,
            "scenario_family": "eval-family",
            "messages": [{"role": "user", "content": "evaluation"}],
            "partition": "engineering",
            "role": "evaluation",
            "input_tokens": 2,
            "max_output_tokens": 3,
        },
    ]
    manifest_entries = []
    for record in records:
        file_name = f"{record['record_id']}.jsonl"
        raw = (json.dumps(record) + "\n").encode()
        (fixtures_dir / file_name).write_bytes(raw)
        parsed = (DatasetRecord.from_dict(record),)
        manifest_entries.append(
            {
                "name": "dev" if record["role"] == "development" else "eval",
                "path": file_name,
                "partition": record["partition"],
                "role": record["role"],
                "sha256": hashlib.sha256(raw).hexdigest(),
                "record_count": 1,
                "content_sha256": ordered_content_digest(parsed),
                "family_sha256": family_membership_digest(parsed),
            }
        )
    manifest = fixtures_dir / "pack.json"
    manifest.write_text(json.dumps({"schema_version": 1, "datasets": manifest_entries}))

    value = spec()
    value.pop("datasets")
    value["fixture_pack"] = {
        "path": "fixtures/pack.json",
        "sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    }
    value["conditions"]["common"]["development_dataset"] = "dev"
    value["evaluation"]["dataset"] = "eval"
    plan = preflight(value, FakeHost(), base_path=tmp_path)
    assert plan.assignments[0]["development_order"] == ["dev-0"]
    assert plan.assignments[0]["evaluation_order"] == ["eval-0"]


def test_float_hard_limits_are_rejected() -> None:
    value = spec()
    value["budgets"]["max_model_calls"] = 8.0
    with pytest.raises(PreflightError, match="positive integer"):
        preflight(value, FakeHost())
