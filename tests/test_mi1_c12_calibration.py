from __future__ import annotations

from experiments.mi1.c12_calibration import (
    BIAS,
    CALIBRATION_FIXTURES,
    HELDOUT_FIXTURES,
    build_calibration_plan,
    build_holdout_plan,
)


def _selection() -> dict[str, object]:
    return {
        "model": {"gguf_sha256": "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03"}
    }


def test_c12_freeze_has_exact_controlled_matrix_without_bank_fact_leakage() -> None:
    plan = build_calibration_plan(c11_selection=_selection(), c11_selection_sha256="a" * 64)
    assert plan["call_count"] == 88
    assert len(plan["coordinates"]) == 88
    assert len(CALIBRATION_FIXTURES) == 4
    for row in plan["coordinates"]:
        request = row["request"]
        model_text = "\n".join(message["content"] for message in request["messages"])
        source = row["bank_source"] or ""
        assert request["cache_prompt"] is False
        if row["metadata"]["condition"].startswith("latent_"):
            assert source and source not in model_text
            assert row["bank_action"] == "attach"
        else:
            assert row["bank_action"] == "clear"


def test_c12_holdout_is_distinct_and_uses_only_predeclared_passing_strength() -> None:
    plan = build_holdout_plan(calibration_plan_sha256="b" * 64, selected_bias_name="twofold")
    assert plan["call_count"] == 112
    assert len(plan["coordinates"]) == 112
    assert {row["metadata"]["fixture_id"] for row in plan["coordinates"]} == {
        row["fixture_id"] for row in HELDOUT_FIXTURES
    }
    assert not (
        {row["fixture_id"] for row in HELDOUT_FIXTURES}
        & {row["fixture_id"] for row in CALIBRATION_FIXTURES}
    )
    assert BIAS["twofold"] > BIAS["zero"]
    for row in plan["coordinates"]:
        if row["metadata"]["condition"].startswith("latent_"):
            assert row["request"]["cache_prompt"] is False
