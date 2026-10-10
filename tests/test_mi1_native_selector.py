from __future__ import annotations

import numpy as np
import pytest

from experiments.mi1.native.selector import (
    appendix_c_sparse_selector,
    attention_mass,
    expand_kv_groups,
    gemma4_source_kv_mapping,
    grouped_alignment_margin,
    sparse_site_list,
    target_reference_alignment,
)


def test_alignment_margin_maps_grouped_query_heads_to_kv_heads() -> None:
    q = np.array([[1, 0], [2, 0], [0, 1], [0, 2]], dtype=np.float32)
    target = np.array([[[1, 0], [0, 1]]], dtype=np.float32)
    reference = np.array([[[0, -1], [-1, 0]]], dtype=np.float32)
    score = target_reference_alignment(q, target, reference)
    assert score.shape == (4,)
    assert score[0] > 0
    assert score[1] > score[0]
    assert score[2] > 0
    assert score[3] > score[2]
    grouped = grouped_alignment_margin(q, target, reference)
    np.testing.assert_allclose(grouped, [score[:2].mean(), score[2:].mean()])


def test_attention_mass_splits_prompt_and_bank_by_query_head() -> None:
    weights = np.array([[0.2, 0.1], [0.3, 0.4], [0.5, 0.5]], dtype=np.float32)
    prompt, bank = attention_mass(weights, prompt_slots=2, bank_slots=1)
    np.testing.assert_allclose(prompt, [0.5, 0.5])
    np.testing.assert_allclose(bank, [0.5, 0.5])


def test_sparse_site_selection_is_stable_and_per_layer() -> None:
    values = np.array([[0.1, 0.8, 0.8], [0.9, 0.2, 0.3]], dtype=np.float32)
    assert sparse_site_list(values, keep_per_layer=1) == ((0, 1), (1, 0))


def test_appendix_c_selector_uses_group_top_k_then_global_layer_top_m() -> None:
    alignment = np.array([[0.7, 0.1], [0.2, 0.9], [0.8, 0.2]], dtype=np.float32)
    mass = np.array([[0.1, 0.9], [0.1, 0.1], [0.1, 0.1]], dtype=np.float32)
    prompt = 1.0 - mass
    selected = appendix_c_sparse_selector(alignment, mass, prompt, groups_per_layer=1, top_layers=2)
    assert selected == ((1, 1), (2, 0))
    assert expand_kv_groups(selected, query_heads=8, kv_groups=2) == (
        (1, 4),
        (1, 5),
        (1, 6),
        (1, 7),
        (2, 0),
        (2, 1),
        (2, 2),
        (2, 3),
    )


def test_gemma4_shared_kv_mapping_records_query_and_source_layers() -> None:
    mapping = gemma4_source_kv_mapping(
        n_layers=6,
        n_kv_layers_from_start=4,
        is_swa=(False, False, False, False, False, True),
    )
    assert mapping == ((0, 0), (1, 1), (2, 2), (3, 3), (4, 3), (5, 2))


def test_attention_mass_ignores_zeroed_prompt_cache_capacity_before_bank() -> None:
    # Actual prompt slots, two masked cache-capacity slots, then one bank slot.
    weights = np.asarray([[0.2], [0.3], [0.0], [0.0], [0.5]], dtype=np.float32)
    prompt, bank = attention_mass(weights, prompt_slots=2, bank_slots=1)
    np.testing.assert_allclose(prompt, [0.5])
    np.testing.assert_allclose(bank, [0.5])


def test_attention_mass_rejects_unmasked_prompt_cache_capacity() -> None:
    weights = np.asarray([[0.2], [0.3], [0.1], [0.0], [0.4]], dtype=np.float32)
    with pytest.raises(ValueError, match="unused prompt-capacity slots"):
        attention_mass(weights, prompt_slots=2, bank_slots=1)


@pytest.mark.parametrize("prompt_slots,bank_slots", [(0, 1), (2, 0)])
def test_attention_mass_rejects_missing_slot_groups(prompt_slots: int, bank_slots: int) -> None:
    with pytest.raises(ValueError):
        attention_mass(
            np.ones((2, 1), dtype=np.float32), prompt_slots=prompt_slots, bank_slots=bank_slots
        )
