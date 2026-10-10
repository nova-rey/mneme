"""Reader for prefill-only native MI1 calibration captures."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float32]


@dataclass(frozen=True)
class QueryLayerCapture:
    query: FloatArray  # [tokens, q_heads, head_dim], normalized pre-RoPE
    attention: FloatArray  # [tokens, q_heads, key_slots], softmax probabilities


@dataclass(frozen=True)
class QueryCapture:
    token_ids: tuple[int, ...]
    layers: dict[int, QueryLayerCapture]


def _decode_tensor(
    raw: bytes, offset: int, nbytes: int, dtype_id: int, shape: tuple[int, ...]
) -> tuple[FloatArray, int]:
    # llama.cpp's stable ggml type IDs: F32=0 and F16=1.
    if dtype_id not in (0, 1):
        raise ValueError(f"unsupported calibration tensor ggml type {dtype_id}")
    count = int(np.prod(shape, dtype=np.int64))
    itemsize = 4 if dtype_id == 0 else 2
    needed = count * itemsize
    if nbytes != needed or offset + nbytes > len(raw):
        raise ValueError("calibration tensor byte count does not match dimensions")
    dtype_code = "<f4" if dtype_id == 0 else "<f2"
    values = np.frombuffer(raw, dtype=dtype_code, count=count, offset=offset).astype(np.float32)
    # ggml's first dimension is contiguous; reverse dimension order for NumPy.
    return values.reshape(tuple(reversed(shape))), offset + nbytes


def read_query_capture(path: Path) -> QueryCapture:
    """Read the binary output from `mi1-native-query-capture` without inference."""
    raw = path.read_bytes()
    if len(raw) < 20 or raw[:8] != b"MI1QRY01":
        raise ValueError("invalid or truncated MI1 query-capture header")
    version, layer_count, token_count = struct.unpack_from("<III", raw, 8)
    if version != 1 or layer_count == 0 or token_count == 0:
        raise ValueError("unsupported or empty MI1 query capture")
    offset = 20
    token_bytes = token_count * 4
    if offset + token_bytes > len(raw):
        raise ValueError("truncated token IDs in MI1 query capture")
    token_ids = tuple(struct.unpack_from(f"<{token_count}i", raw, offset))
    offset += token_bytes
    layers: dict[int, QueryLayerCapture] = {}
    for _ in range(layer_count):
        if offset + 4 + 4 + 32 + 8 > len(raw):
            raise ValueError("truncated query-capture layer header")
        layer, q_type = struct.unpack_from("<iI", raw, offset)
        offset += 8
        q_shape = struct.unpack_from("<4q", raw, offset)
        offset += 32
        q_bytes = struct.unpack_from("<Q", raw, offset)[0]
        offset += 8
        query, offset = _decode_tensor(raw, offset, q_bytes, q_type, q_shape)
        if offset + 4 + 32 + 8 > len(raw):
            raise ValueError("truncated attention-capture header")
        p_type = struct.unpack_from("<I", raw, offset)[0]
        offset += 4
        p_shape = struct.unpack_from("<4q", raw, offset)
        offset += 32
        p_bytes = struct.unpack_from("<Q", raw, offset)[0]
        offset += 8
        attention, offset = _decode_tensor(raw, offset, p_bytes, p_type, p_shape)
        # GGML attention tensor is [key_slots, heads, tokens, stream].
        if query.ndim != 4 or attention.ndim != 4 or query.shape[0] != 1 or attention.shape[0] != 1:
            raise ValueError("unexpected query-capture tensor rank/stream count")
        q_rows = query[0]
        p_rows = attention[0]
        if q_rows.shape[0] != token_count:
            raise ValueError("captured query rows do not align with token IDs")
        if p_rows.shape[:2] == (token_count, q_rows.shape[1]):
            pass
        elif p_rows.shape[:2] == (q_rows.shape[1], token_count):
            # llama.cpp's softmax tensor uses [keys, tokens, heads, stream],
            # unlike the query tensor's [dim, heads, tokens, stream].
            p_rows = p_rows.transpose(1, 0, 2)
        else:
            raise ValueError("captured attention rows do not align with query heads/tokens")
        if layer in layers:
            raise ValueError("duplicate layer in MI1 query capture")
        layers[layer] = QueryLayerCapture(q_rows, p_rows)
    if offset != len(raw):
        raise ValueError("MI1 query capture has trailing bytes")
    return QueryCapture(token_ids, layers)
