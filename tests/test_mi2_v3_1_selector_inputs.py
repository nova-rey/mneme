from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "mi2_freeze_selector_v3_1.py"
SPEC = importlib.util.spec_from_file_location("mi2_freeze_selector_v3_1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_selector_reads_only_the_three_frozen_v3_1_calibration_rows() -> None:
    plan = {
        "calibration_version": "v3.1",
        "calibration": {
            "items": [
                {"id": "atomic/1-48"},
                {"id": "atomic/1-12"},
                {"id": "atomic/1-41"},
            ]
        },
        "heldout_embargo": {"items": [{"id": "atomic/1-50"}]},
    }

    assert [row["id"] for row in MODULE.calibration_items(plan)] == [
        "atomic/1-48",
        "atomic/1-12",
        "atomic/1-41",
    ]


def test_selector_rejects_prior_v2_artifact_path_before_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / "calibration-run-v3.1"
    old = run_root / "v2" / "banks" / "target.npz"
    load_attempts: list[Path] = []

    def record_load(path: Path) -> None:
        load_attempts.append(path)

    monkeypatch.setattr(MODULE.MemoryBank, "load", staticmethod(record_load))
    with pytest.raises(ValueError, match="prior MI2 artifact forbidden"):
        MODULE.load_v3_1_banks({}, old, old.with_name("reference.npz"), run_root)
    assert load_attempts == []


def test_selector_rejects_inputs_outside_the_v3_1_run_root(tmp_path: Path) -> None:
    run_root = tmp_path / "calibration-run-v3.1"
    old_run = tmp_path / "calibration-run-v2" / "banks" / "reference.npz"

    with pytest.raises(ValueError, match="outside v3.1 run root"):
        MODULE.assert_v3_1_inputs([old_run], run_root)


def test_selector_fails_closed_on_v2_plan_or_changed_calibration_ids() -> None:
    with pytest.raises(ValueError, match="calibration_version=v3.1"):
        MODULE.calibration_items({"calibration_version": "v2"})
    with pytest.raises(ValueError, match="unexpected v3.1 calibration IDs"):
        MODULE.calibration_items(
            {
                "calibration_version": "v3.1",
                "calibration": {"items": [{"id": "quantum/3-3013"}] * 3},
            }
        )


def test_bank_text_is_checked_against_frozen_exact_text_hash() -> None:
    bank = SimpleNamespace(
        source_text="frozen source text",
        manifest=SimpleNamespace(
            model_sha256="model",
            llama_commit="commit",
            layer_ids=tuple(range(24)),
            kv_heads_by_layer=(2,) * 24,
        ),
        validate=lambda: None,
    )
    freeze = {"seed_and_runtime": {"gguf_sha256": "model", "llama_commit": "commit"}}

    with pytest.raises(ValueError, match="exact-text SHA-256 mismatch"):
        MODULE.validate_bank(
            bank,
            expected_card_text="frozen source text",
            expected_source_text="frozen source text",
            expected_text_sha256="0" * 64,
            label="target",
            freeze=freeze,
        )
