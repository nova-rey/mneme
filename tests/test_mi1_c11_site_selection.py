from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest

from experiments.mi1.c11_site_selection import (
    alignment_by_group,
    choose_sites,
    query_to_source_layer,
    read_last_queries,
    read_native_keys,
)


def test_c11_group_alignment_selects_target_over_reference_per_kv_group() -> None:
    query = np.zeros((8, 2), dtype=np.float32)
    query[0:4, 0] = 1.0
    query[4:8, 1] = 1.0
    target = np.zeros((2, 2, 2), dtype=np.float32)
    reference = np.zeros((2, 2, 2), dtype=np.float32)
    target[0, 0, 0] = 1.0
    reference[0, 1, 1] = 1.0

    margins = alignment_by_group(query, target, reference)

    assert margins[0] == pytest.approx(1 / np.sqrt(2))
    assert margins[1] == pytest.approx(-1 / np.sqrt(2))


def test_c11_site_selection_uses_top_layer_and_lowest_index_ties() -> None:
    margins = np.zeros((42, 2), dtype=np.float32)
    margins[8, 1] = 0.5
    margins[2, 0] = 0.5
    margins[6, 1] = 0.25
    margins[28, 0] = 0.1

    sites, scores = choose_sites(margins, top_layers=3)

    assert sites == [
        [2, 0],
        [2, 1],
        [2, 2],
        [2, 3],
        [8, 4],
        [8, 5],
        [8, 6],
        [8, 7],
        [6, 4],
        [6, 5],
        [6, 6],
        [6, 7],
    ]
    assert scores == pytest.approx([0.5, 0.5, 0.25])


def test_gemma4_shared_kv_mapping_distinguishes_swa_and_full_attention() -> None:
    assert query_to_source_layer(23, 256, 512, 24) == 23
    assert query_to_source_layer(24, 256, 512, 24) == 22
    assert query_to_source_layer(24, 512, 512, 24) == 23


def test_c11_alignment_rejects_incompatible_group_dimensions() -> None:
    query = np.zeros((8, 2), dtype=np.float32)
    target = np.zeros((3, 2, 2), dtype=np.float32)
    reference = np.zeros((3, 2, 4), dtype=np.float32)

    with pytest.raises(ValueError, match="dimensions"):
        alignment_by_group(query, target, reference)


def test_c11_query_capture_reader_extracts_last_token_for_each_layer(tmp_path: Path) -> None:
    path = tmp_path / "query.mi1qry"
    with path.open("wb") as stream:
        stream.write(b"MI1QRY01")
        stream.write(struct.pack("<III", 1, 42, 1))
        stream.write(struct.pack("<i", 123))
        for layer in range(42):
            q = np.arange(16, dtype="<f4") + layer * 20
            p = np.zeros(24, dtype="<f4")
            stream.write(struct.pack("<iI4qQ", layer, 0, 2, 8, 1, 1, q.nbytes))
            stream.write(q.tobytes())
            stream.write(struct.pack("<I4qQ", 0, 3, 1, 8, 1, p.nbytes))
            stream.write(p.tobytes())

    token_ids, queries = read_last_queries(path)

    assert token_ids == (123,)
    assert set(queries) == set(range(42))
    np.testing.assert_array_equal(queries[7], np.arange(16, dtype=np.float32).reshape(8, 2) + 140)


def test_c11_native_bank_reader_keeps_keys_and_skips_values(tmp_path: Path) -> None:
    path = tmp_path / "bank.mi1"
    keys = np.arange(4, dtype="<f4")
    values = np.arange(4, dtype="<f4") + 20
    with path.open("wb") as stream:
        stream.write(struct.pack("<8sIIII", b"MI1KV002", 2, 1, 1, 0))
        stream.write(struct.pack("<IIII", 0, 2, 2, 1))
        stream.write(keys.tobytes())
        stream.write(values.tobytes())
        stream.write(struct.pack("<f", 0.0))

    read_keys, dimensions = read_native_keys(path)

    assert dimensions == {0: 2}
    np.testing.assert_array_equal(read_keys[0], keys.reshape(1, 2, 2))
