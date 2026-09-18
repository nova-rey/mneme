"""P0.3 fixture and split-contamination tests."""

import hashlib
import json

import pytest

from mneme.experiments.datasets import (
    DatasetBoundaryError,
    DatasetRecord,
    FixturePack,
    family_membership_digest,
    load_fixture_pack,
    ordered_content_digest,
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
    dev_path = tmp_path / "development.jsonl"
    eval_path = tmp_path / "evaluation.jsonl"
    dev_raw = json.dumps(records[0]) + "\n"
    eval_raw = json.dumps(records[1]) + "\n"
    dev_path.write_text(dev_raw)
    eval_path.write_text(eval_raw)
    dev_parsed = (DatasetRecord.from_dict(records[0], source_path=str(dev_path)),)
    eval_parsed = (DatasetRecord.from_dict(records[1], source_path=str(eval_path)),)
    manifest = tmp_path / "pack.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "datasets": [
                    {
                        "name": "engineering-development",
                        "path": dev_path.name,
                        "partition": "engineering",
                        "role": "development",
                        "sha256": hashlib.sha256(dev_raw.encode()).hexdigest(),
                        "record_count": 1,
                        "content_sha256": ordered_content_digest(dev_parsed),
                        "family_sha256": family_membership_digest(dev_parsed),
                    },
                    {
                        "name": "engineering-evaluation",
                        "path": eval_path.name,
                        "partition": "engineering",
                        "role": "evaluation",
                        "sha256": hashlib.sha256(eval_raw.encode()).hexdigest(),
                        "record_count": 1,
                        "content_sha256": ordered_content_digest(eval_parsed),
                        "family_sha256": family_membership_digest(eval_parsed),
                    },
                ],
            }
        )
    )
    pack = load_fixture_pack(manifest)
    assert isinstance(pack, FixturePack)
    assert [record.record_id for record in pack.datasets["engineering-evaluation"]] == ["eval-0"]
    assert pack.manifest_digest is not None
    with pytest.raises(DatasetBoundaryError, match="manifest digest"):
        load_fixture_pack(manifest, expected_manifest_digest="0" * 64)


def test_same_dataset_file_cannot_be_assigned_to_both_roles(tmp_path):
    record = {
        "record_id": "one",
        "ordinal": 0,
        "scenario_family": "family-a",
        "messages": [{"role": "user", "content": "one"}],
        "partition": "engineering",
        "role": "development",
    }
    data_path = tmp_path / "records.jsonl"
    raw_data = json.dumps(record) + "\n"
    data_path.write_text(raw_data)
    file_digest = hashlib.sha256(raw_data.encode()).hexdigest()
    parsed = (DatasetRecord.from_dict(record, source_path=str(data_path)),)
    content_digest = ordered_content_digest(parsed)
    family_digest = family_membership_digest(parsed)
    manifest = tmp_path / "pack.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "datasets": [
                    {
                        "name": "one",
                        "path": data_path.name,
                        "partition": "engineering",
                        "role": "development",
                        "sha256": file_digest,
                        "record_count": 1,
                        "content_sha256": content_digest,
                        "family_sha256": family_digest,
                    },
                    {
                        "name": "two",
                        "path": data_path.name,
                        "partition": "engineering",
                        "role": "development",
                        "sha256": "0" * 64,
                        "record_count": 1,
                        "content_sha256": "0" * 64,
                        "family_sha256": "0" * 64,
                    },
                ],
            }
        )
    )
    with pytest.raises(DatasetBoundaryError, match="alias/reuse"):
        load_fixture_pack(manifest)


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


def test_inline_record_unknown_fields_fail_closed():
    with pytest.raises(DatasetBoundaryError, match="unknown field"):
        DatasetRecord.from_dict(
            {
                "record_id": "x",
                "ordinal": 0,
                "scenario_family": "f",
                "messages": [{"role": "user", "content": "x"}],
                "partition": "engineering",
                "role": "development",
                "future_field": "must not be silently ignored",
            }
        )


def test_manifest_file_count_content_and_family_digests_are_verified(tmp_path):
    record = {
        "record_id": "one",
        "ordinal": 0,
        "scenario_family": "family-a",
        "messages": [{"role": "user", "content": "one"}],
        "partition": "engineering",
        "role": "development",
    }
    data_path = tmp_path / "records.jsonl"
    raw_data = json.dumps(record) + "\n"
    data_path.write_text(raw_data)
    parsed = (DatasetRecord.from_dict(record, source_path=str(data_path)),)
    entry = {
        "name": "development",
        "path": data_path.name,
        "partition": "engineering",
        "role": "development",
        "sha256": hashlib.sha256(raw_data.encode()).hexdigest(),
        "record_count": 1,
        "content_sha256": ordered_content_digest(parsed),
        "family_sha256": family_membership_digest(parsed),
    }
    for field, bad_value in (
        ("sha256", "0" * 64),
        ("record_count", 2),
        ("content_sha256", "0" * 64),
        ("family_sha256", "0" * 64),
    ):
        manifest = tmp_path / f"pack-{field}.json"
        altered = dict(entry)
        altered[field] = bad_value
        manifest.write_text(json.dumps({"schema_version": 1, "datasets": [altered]}))
        with pytest.raises(DatasetBoundaryError):
            load_fixture_pack(manifest)
