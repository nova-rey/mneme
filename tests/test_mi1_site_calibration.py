from __future__ import annotations

import numpy as np

from experiments.mi1.native.bank import BankManifest, MemoryBank
from experiments.mi1.native.query_capture import QueryCapture, QueryLayerCapture
from experiments.mi1.site_calibration import _source_layer_mapping, select_query_sites


def _bank(key_value: float, source_text: str) -> MemoryBank:
    layers = tuple(range(42))
    keys = {
        layer: np.full((1, 2, 2), key_value, dtype=np.float32) for layer in layers
    }
    values = {layer: np.ones((1, 2, 2), dtype=np.float32) for layer in layers}
    return MemoryBank(
        BankManifest(
            model_sha256="a" * 64,
            llama_commit="pin",
            architecture="gemma4-e4b",
            layer_ids=layers,
            head_dim=2,
            kv_heads_by_layer=(2,) * 42,
            slot_count=1,
            head_dim_by_layer=(2,) * 42,
        ),
        keys,
        values,
        source_text,
        (7,),
    )


def _capture() -> QueryCapture:
    layers = {
        layer: QueryLayerCapture(
            query=np.ones((1, 8, 2), dtype=np.float32),
            # [tokens, heads, prompt+bank slots]
            attention=np.full((1, 8, 2), 0.5, dtype=np.float32),
        )
        for layer in range(42)
    }
    return QueryCapture((1,), layers)


def test_site_selection_is_stable_and_expands_sparse_and_broad_sites() -> None:
    target = _bank(1.0, "target")
    reference = _bank(-1.0, "reference")
    selection = select_query_sites(
        {"task-1": _capture(), "task-2": _capture()},
        {"task-1": target, "task-2": target},
        reference,
    )
    assert selection.alignment.shape == (42, 2)
    assert selection.sparse_groups == ((0, 0), (1, 0), (2, 0), (3, 0))
    assert len(selection.sparse_query_sites) == 16
    assert selection.broad_groups[0] == (0, 0)
    assert selection.broad_groups[-1] == (41, 1)
    assert len(selection.broad_query_sites) == 336


def test_gemma4_shared_kv_mapping_uses_swa_and_full_attention_sources() -> None:
    dims = (256, 256, 512, 256, 512, 256)
    mapping = _source_layer_mapping(dims, (0, 1, 2, 3))
    assert mapping == ((0, 0), (1, 1), (2, 2), (3, 3), (4, 3), (5, 2))
