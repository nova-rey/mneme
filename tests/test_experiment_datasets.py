"""P0.3 fixture and split-contamination tests."""

import json

import pytest

from mneme.experiments.datasets import (
    DatasetBoundaryError,
    DatasetRecord,
    FixturePack,
    load_fixture_pack,
    validate_split_boundaries,
)


def _record(
    record_id: str,
    *,
    family: str = "family-a",
    role: str = "development",
    partition: str = "engineering",
    text: str | None = None,
    ordinal: int = 0,
) -> DatasetRecord:
    return DatasetRecord(
        record_id,
        ordinal,
        family,
        ({"role": "user", "content": text or record_id},),
        partition,
        role,
    )


def test_duplicate_content_under_different_ids_is_rejected():
    first = _record("one", text="same prompt")
    second = _record("two", text="same  prompt", ordinal=1)
    with pytest.raises(DatasetBoundaryError, match="duplicate normalized content"):
        validate_split_boundaries([first, second])


def test_scenario_family_cannot_cross_development_evaluation():
    first = _record("dev", family="same-family")
    second = _record("eval", family="same-family", role="evaluation", ordinal=0)
    with pytest.raises(DatasetBoundaryError, match="crosses split"):
        validate_split_boundaries([first, second])


def test_duplicate_ids_and_ordinals_are_rejected():
    with pytest.raises(DatasetBoundaryError, match="duplicate record ID"):
        validate_split_boundaries([_record("same"), _record("same", ordinal=1)])
    with pytest.raises(DatasetBoundaryError, match="duplicate ordinal"):
        validate_split_boundaries([_record("one"), _record("two", family="family-b")])


def test_known_variants_stay_together_and_fixture_pack_loads(tmp_path):
    records = [
        {
            "record_id": "dev-0",
            "ordinal": 0,
            "scenario_family": "family-a",
            "messages": [{"role": "user", "content": "development"}],
            "partition": "engineering",
            "role": "development",
        },
        {
            "record_id": "eval-0",
            "ordinal": 0,
            "scenario_family": "family-b",
            "messages": [{"role": "user", "content": "evaluation"}],
            "partition": "engineering",
            "role": "evaluation",
        },
    ]
    data_path = tmp_path / "records.jsonl"
    data_path.write_text("\n".join(json.dumps(record) for record in records) + "\n")
    manifest = tmp_path / "pack.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "datasets": [
                    {"path": data_path.name, "partition": "engineering"}
                ],
            }
        )
    )
    pack = load_fixture_pack(manifest)
    assert isinstance(pack, FixturePack)
    assert [record.record_id for record in pack.by_role("evaluation")] == ["eval-0"]
    assert pack.manifest_digest is not None


def test_invalid_partition_and_missing_family_fail():
    with pytest.raises(DatasetBoundaryError, match="unsupported partition"):
        DatasetRecord.from_dict(
            {
                "record_id": "x",
                "ordinal": 0,
                "scenario_family": "f",
                "messages": [{"role": "user", "content": "x"}],
                "partition": "unknown",
                "role": "development",
            }
        )
    with pytest.raises(DatasetBoundaryError, match="missing"):
        DatasetRecord.from_dict({"record_id": "x"})
