"""P0.3 experiment identity and contract-boundary tests."""

import pytest

from mneme.experiments.contracts import ContractError, ExperimentSpec


def _spec(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": 1,
        "name": "shared-input-control",
        "contract_revision": 3,
        "purpose": "Verify controls.",
        "stage": "engineering",
        "contract": {"fixed": ["host"], "may_differ": ["development_sampling"]},
        "fixture_pack": {"path": "fixtures/pack.json", "sha256": "a" * 64},
        "checkpoints": {
            "checkpoint-a": {
                "path": "checkpoints/a.sqlite3",
                "checkpoint_id": "checkpoint-id",
                "instance_id": "instance-id",
                "revision": 0,
                "manifest_id": "manifest-id",
                "sha256": "b" * 64,
            }
        },
        "subjects": [
            {
                "slot": 0,
                "start": "checkpoint-a",
                "cohort": "shared",
                "condition": "common",
                "development_sampling_slot": 0,
            }
        ],
        "conditions": {"common": {"development_dataset": "dev"}},
        "evaluation": {"dataset": "eval", "repetitions": 2},
        "host": {"backend": "fake", "requires": ["text_generation"]},
        "randomization": {"master_seed": 7, "derivation_version": "mneme-seeds-v1"},
        "budgets": {"max_model_calls": 4, "max_output_tokens": 100},
        "storage_allowed": True,
    }
    value.update(changes)
    return value


def test_scientific_identity_is_distinct_from_content_digest():
    first = ExperimentSpec.from_dict(_spec())
    changed_description = ExperimentSpec.from_dict(_spec(purpose="A changed purpose."))
    next_revision = ExperimentSpec.from_dict(_spec(contract_revision=4))

    assert first.identity.label() == "shared-input-control / revision 3"
    assert first.content_digest != changed_description.content_digest
    assert first.identity == changed_description.identity
    assert next_revision.identity != first.identity
    assert first.content_digest != next_revision.content_digest


def test_contract_is_deeply_immutable_and_round_trips():
    original = _spec()
    spec = ExperimentSpec.from_dict(original)
    original["subjects"] = []
    assert len(spec.to_dict()["subjects"]) == 1  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        spec._data["name"] = "changed"  # type: ignore[index]
    restored = ExperimentSpec.from_json(spec.canonical_json())
    assert restored.to_dict() == spec.to_dict()


def test_unknown_and_missing_fields_fail_closed():
    with pytest.raises(ContractError, match="unknown"):
        ExperimentSpec.from_dict(_spec(unexpected=True))
    missing = _spec()
    del missing["host"]
    with pytest.raises(ContractError, match="missing"):
        ExperimentSpec.from_dict(missing)


def test_duplicate_json_fields_and_nonfinite_values_fail():
    with pytest.raises(ContractError, match="duplicate"):
        ExperimentSpec.from_json('{"schema_version": 1, "schema_version": 1}')
    with pytest.raises(ContractError, match="non-finite"):
        ExperimentSpec.from_dict(_spec(budgets={"max_seconds": float("nan")}))


def test_invalid_subject_reference_and_revision_fail():
    with pytest.raises(ContractError, match="unknown condition"):
        ExperimentSpec.from_dict(
            _spec(
                subjects=[
                    {
                        "slot": 0,
                        "start": "checkpoint-a",
                        "cohort": "x",
                        "condition": "missing",
                    }
                ]
            )
        )
    with pytest.raises(ContractError, match="positive"):
        ExperimentSpec.from_dict(_spec(contract_revision=0))


def test_starting_checkpoint_is_required_and_must_be_bound():
    missing = _spec()
    del missing["checkpoints"]
    with pytest.raises(ContractError, match="missing"):
        ExperimentSpec.from_dict(missing)

    unbound = _spec(subjects=[{
        "slot": 0,
        "start": "missing-checkpoint",
        "cohort": "x",
        "condition": "common",
    }])
    with pytest.raises(ContractError, match="undeclared starting checkpoint"):
        ExperimentSpec.from_dict(unbound)


def test_inline_datasets_use_strict_record_schema():
    record = {
        "record_id": "d0",
        "ordinal": 0,
        "scenario_family": "family-a",
        "messages": [{"role": "user", "content": "hello"}],
        "partition": "engineering",
        "role": "development",
    }
    accepted = ExperimentSpec.from_dict(_spec(datasets={"dev": [record]}))
    assert accepted.to_dict()["datasets"]["dev"][0]["record_id"] == "d0"
    invalid = _spec(datasets={"dev": [{**record, "unexpected": True}]})
    with pytest.raises(ContractError, match="unknown field"):
        ExperimentSpec.from_dict(invalid)
