from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest

from experiments.mi1.native.query_capture import read_query_capture


def test_reopens_prefill_queries_and_attention_probabilities(tmp_path: Path) -> None:
    path = tmp_path / "calibration.mi1qry"
    query = np.array([[[[1, 2], [3, 4]]]], dtype="<f4")
    # GGML order [keys, heads, tokens, stream].
    attention = np.array([[[[0.1, 0.3, 0.6], [0.2, 0.4, 0.4]]]], dtype="<f4")
    with path.open("wb") as stream:
        stream.write(b"MI1QRY01")
        stream.write(struct.pack("<III", 1, 1, 2))
        stream.write(struct.pack("<2i", 17, 29))
        stream.write(struct.pack("<iI", 6, 0))
        stream.write(struct.pack("<4q", 2, 1, 2, 1))
        stream.write(struct.pack("<Q", query.nbytes))
        stream.write(query.tobytes())
        stream.write(struct.pack("<I", 0))
        stream.write(struct.pack("<4q", 3, 1, 2, 1))
        stream.write(struct.pack("<Q", attention.nbytes))
        stream.write(attention.tobytes())

    capture = read_query_capture(path)
    assert capture.token_ids == (17, 29)
    np.testing.assert_array_equal(capture.layers[6].query, [[[1, 2]], [[3, 4]]])
    np.testing.assert_allclose(
        capture.layers[6].attention,
        [[[0.1, 0.3, 0.6]], [[0.2, 0.4, 0.4]]],
    )


def test_reads_llama_softmax_token_head_axis_order(tmp_path: Path) -> None:
    path = tmp_path / "llama-softmax.mi1qry"
    query = np.array([[[[1, 2], [3, 4]]]], dtype="<f4")
    # Native softmax GGML order is [key_slots, tokens, heads, stream].
    attention = np.array(
        [[[[0.1, 0.3, 0.6]], [[0.2, 0.4, 0.4]]]], dtype="<f4"
    )
    with path.open("wb") as stream:
        stream.write(b"MI1QRY01")
        stream.write(struct.pack("<III", 1, 1, 2))
        stream.write(struct.pack("<2i", 17, 29))
        stream.write(struct.pack("<iI", 6, 0))
        stream.write(struct.pack("<4q", 2, 1, 2, 1))
        stream.write(struct.pack("<Q", query.nbytes))
        stream.write(query.tobytes())
        stream.write(struct.pack("<I", 0))
        stream.write(struct.pack("<4q", 3, 2, 1, 1))
        stream.write(struct.pack("<Q", attention.nbytes))
        stream.write(attention.tobytes())

    capture = read_query_capture(path)
    np.testing.assert_allclose(
        capture.layers[6].attention,
        [[[0.1, 0.3, 0.6]], [[0.2, 0.4, 0.4]]],
    )


def test_query_capture_reader_rejects_truncation_and_bad_shape(tmp_path: Path) -> None:
    path = tmp_path / "bad.mi1qry"
    path.write_bytes(b"MI1QRY01" + struct.pack("<III", 1, 1, 1))
    with pytest.raises(ValueError, match="truncated token IDs"):
        read_query_capture(path)
