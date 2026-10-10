from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

from experiments.mi1.calibration import (
    build_calibration_coordinates,
    canonical_bytes,
    variant_key,
)


def _suite() -> dict[str, Any]:
    value = json.loads(
        Path("experiments/mi1/fixtures/mi1_frozen_suite.json").read_text(encoding="utf-8")
    )
    return cast(dict[str, Any], value)


def test_calibration_matrix_is_frozen_and_cache_disabled() -> None:
    rows = build_calibration_coordinates(_suite())
    assert len(rows) == 44
    assert len({row["coordinate_id"] for row in rows}) == 44
    assert all(row["request"]["cache_prompt"] is False for row in rows)
    assert all(row["request"]["seed"] in {34111, 34133} for row in rows)

    matrix = [
        row
        for row in rows
        if row["metadata"]["server_role"] == "mi1_server"
        and row["metadata"]["duplicate_of"] is None
    ]
    assert len(matrix) == 42
    conditions = {row["metadata"]["condition"] for row in matrix}
    assert conditions == {
        "no_bank",
        "visible_bank",
        "latent_sparse_low",
        "latent_sparse_moderate",
        "latent_sparse_strong",
        "latent_broad_moderate",
        "latent_irrelevant_sparse_moderate",
    }


def test_calibration_duplicate_and_base_server_are_exact_request_replays() -> None:
    rows = {row["coordinate_id"]: row for row in build_calibration_coordinates(_suite())}
    source = rows["CAL-REL-01-no_bank-34111"]
    for coordinate_id, role in (
        ("CAL-REL-01-no_bank-34111-duplicate", "mi1_server"),
        ("CAL-REL-01-no_bank-34111-base-server", "base_server"),
    ):
        replay = rows[coordinate_id]
        assert replay["request"] == source["request"]
        expected_hash = hashlib.sha256(canonical_bytes(source["request"])).hexdigest()
        assert replay["request_sha256"] == expected_hash
        assert replay["metadata"]["server_role"] == role
        assert replay["metadata"]["duplicate_of"] == source["coordinate_id"]


def test_latent_calibration_hides_relationship_bank_from_request() -> None:
    rows = build_calibration_coordinates(_suite())
    for row in rows:
        metadata = row["metadata"]
        if metadata["condition"] == "visible_bank":
            continue
        source = row["bank_source"]
        if source is None:
            continue
        request_bytes = canonical_bytes(row["request"])
        assert source.encode("utf-8") not in request_bytes
        assert hashlib.sha256(source.encode("utf-8")).hexdigest() == row["bank_source_sha256"]


def test_visible_calibration_is_text_only_and_clears_native_bank() -> None:
    rows = build_calibration_coordinates(_suite())
    visible = [row for row in rows if row["metadata"]["condition"] == "visible_bank"]
    assert len(visible) == 6
    for row in visible:
        assert row["bank_action"] == "clear"
        assert row["bank_source"] is None
        assert row["bank_source_sha256"] is None
        assert row["bank_config"]["selector"] == "none"
        user_text = row["request"]["messages"][1]["content"]
        assert user_text.startswith("Reference relationships:\n")
        assert any(
            phrase in user_text
            for phrase in (
                "Aster activates Beryl.",
                "Moro unlocks Pavi.",
                "Neri prepares Sulo.",
            )
        )


def test_variant_key_binds_source_and_exact_config() -> None:
    source = "a" * 64
    config = {"selector": "sparse", "gain": {"logit_bias": 0.0}}
    assert variant_key(source, config) == variant_key(source, dict(config))
    assert variant_key(source, config) != variant_key("b" * 64, config)
    assert variant_key(source, config) != variant_key(
        source, {"selector": "broad", "gain": {"logit_bias": 0.0}}
    )
