from __future__ import annotations

import struct
from pathlib import Path

import pytest

from experiments.mi1.native.native_selector_patch import patch_native_bank_selector


def test_native_selector_patch_preserves_tensor_bytes_and_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "base.mi1"
    output_a = tmp_path / "a.mi1"
    output_b = tmp_path / "b.mi1"
    keys_and_values = struct.pack("<8f", *range(8))
    source.write_bytes(
        struct.pack("<8sIIII", b"MI1KV002", 2, 1, 1, 0)
        + struct.pack("<IIII", 0, 2, 2, 1)
        + keys_and_values
        + struct.pack("<f", 0.0)
    )
    sites = ((3, 0), (3, 1), (3, 2), (3, 3))

    patch_native_bank_selector(source, output_a, query_sites=sites, bank_logit_bias=0.0)
    patch_native_bank_selector(source, output_b, query_sites=sites, bank_logit_bias=0.0)

    expected = (
        struct.pack("<8sIIII", b"MI1KV002", 2, 1, 1, len(sites))
        + struct.pack("<IIII", 0, 2, 2, 1)
        + keys_and_values
        + b"".join(struct.pack("<II", layer, head) for layer, head in sites)
        + struct.pack("<f", 0.0)
    )
    assert output_a.read_bytes() == expected
    assert output_b.read_bytes() == expected
    assert source.read_bytes() != expected


def test_native_selector_patch_rejects_nonempty_or_nonneutral_source(tmp_path: Path) -> None:
    source = tmp_path / "bad.mi1"
    source.write_bytes(struct.pack("<8sIIII", b"MI1KV002", 2, 1, 1, 1) + b"\0" * 20)

    with pytest.raises(ValueError, match="no query-site selector"):
        patch_native_bank_selector(
            source, tmp_path / "out.mi1", query_sites=((1, 0),), bank_logit_bias=0.0
        )
