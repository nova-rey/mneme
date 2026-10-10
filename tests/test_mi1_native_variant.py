from __future__ import annotations

import numpy as np

from experiments.mi1.native.bank import BankManifest, MemoryBank
from experiments.mi1.native.variant import configure_bank


def test_configure_bank_preserves_memory_and_changes_only_selector_prior() -> None:
    manifest = BankManifest(
        model_sha256="a" * 64,
        llama_commit="pin",
        architecture="gemma4-e4b",
        layer_ids=(0,),
        head_dim=2,
        kv_heads_by_layer=(2,),
        slot_count=1,
        head_dim_by_layer=(2,),
    )
    key = np.array([[[1.0, 2.0], [3.0, 4.0]]], dtype=np.float32)
    value = key + 1
    bank = MemoryBank(manifest, {0: key}, {0: value}, "source", (3,))
    configured = configure_bank(bank, query_sites=((0, 4), (0, 5)), bank_logit_bias=-0.25)
    assert configured.source_text == bank.source_text
    assert configured.token_ids == bank.token_ids
    np.testing.assert_array_equal(configured.keys[0], bank.keys[0])
    np.testing.assert_array_equal(configured.values[0], bank.values[0])
    assert configured.manifest.query_sites == ((0, 4), (0, 5))
    assert configured.manifest.bank_logit_bias == -0.25
