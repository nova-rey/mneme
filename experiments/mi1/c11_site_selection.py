"""Frozen C11 Eq.3 query-site selection over prefill-only Gemma captures."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float32]


def _tensor(
    raw: bytes, offset: int, dtype_id: int, shape: tuple[int, ...]
) -> tuple[FloatArray, int]:
    if dtype_id not in (0, 1):
        raise ValueError(f"unsupported GGML tensor type {dtype_id}")
    count = int(np.prod(shape, dtype=np.int64))
    itemsize = 4 if dtype_id == 0 else 2
    byte_count = count * itemsize
    if offset + byte_count > len(raw):
        raise ValueError("truncated tensor in MI1 query capture")
    dtype = "<f4" if dtype_id == 0 else "<f2"
    values = np.frombuffer(raw, dtype=dtype, count=count, offset=offset).astype(np.float32)
    return values.reshape(tuple(reversed(shape))), offset + byte_count


def read_last_queries(path: Path) -> tuple[tuple[int, ...], dict[int, FloatArray]]:
    """Read only the final prompt query row at each layer from MI1QRY01."""
    raw = path.read_bytes()
    if len(raw) < 20 or raw[:8] != b"MI1QRY01":
        raise ValueError("invalid MI1QRY01 header")
    version, layer_count, token_count = struct.unpack_from("<III", raw, 8)
    if version != 1 or layer_count != 42 or token_count == 0:
        raise ValueError("unsupported MI1 query capture dimensions")
    offset = 20
    token_ids = struct.unpack_from(f"<{token_count}i", raw, offset)
    offset += token_count * 4
    queries: dict[int, FloatArray] = {}
    for _ in range(layer_count):
        layer, q_type = struct.unpack_from("<iI", raw, offset)
        offset += 8
        q_shape = struct.unpack_from("<4q", raw, offset)
        offset += 32
        q_bytes = struct.unpack_from("<Q", raw, offset)[0]
        offset += 8
        expected_bytes = int(np.prod(q_shape, dtype=np.int64)) * (4 if q_type == 0 else 2)
        if q_bytes != expected_bytes:
            raise ValueError("query tensor byte length does not match its dimensions")
        q_rows, next_offset = _tensor(raw, offset, q_type, q_shape)
        if (
            next_offset - offset != q_bytes
            or q_rows.shape[0] != 1
            or q_rows.shape[1] != token_count
        ):
            raise ValueError("query tensor rows do not match captured prompt")
        queries[layer] = np.asarray(q_rows[0, -1], dtype=np.float32)
        offset = next_offset
        p_type = struct.unpack_from("<I", raw, offset)[0]
        offset += 4
        p_shape = struct.unpack_from("<4q", raw, offset)
        offset += 32
        p_bytes = struct.unpack_from("<Q", raw, offset)[0]
        offset += 8
        expected_p = int(np.prod(p_shape, dtype=np.int64)) * (4 if p_type == 0 else 2)
        if p_bytes != expected_p or offset + p_bytes > len(raw):
            raise ValueError("attention tensor byte length does not match its dimensions")
        offset += p_bytes
    if offset != len(raw) or set(queries) != set(range(42)):
        raise ValueError("MI1 query capture has trailing data or missing layers")
    return tuple(token_ids), queries


def read_native_keys(path: Path) -> tuple[dict[int, FloatArray], dict[int, int]]:
    """Read key matrices and per-layer dimensions from MI1KV002."""
    raw = path.read_bytes()
    if len(raw) < 24:
        raise ValueError("truncated MI1 bank header")
    magic, version, layer_count, slots, site_count = struct.unpack_from("<8sIIII", raw)
    if magic != b"MI1KV002" or version != 2 or not layer_count or not slots:
        raise ValueError("unsupported MI1 bank format")
    offset = 24
    keys: dict[int, FloatArray] = {}
    dimensions: dict[int, int] = {}
    for _ in range(layer_count):
        layer, dim, kv_heads, layer_slots = struct.unpack_from("<IIII", raw, offset)
        offset += 16
        if layer_slots != slots or not dim or not kv_heads:
            raise ValueError("invalid MI1 bank layer dimensions")
        nbytes = slots * dim * kv_heads * 4
        if offset + 2 * nbytes > len(raw):
            raise ValueError("truncated MI1 bank K/V data")
        keys[layer] = np.frombuffer(
            raw, dtype="<f4", count=slots * kv_heads * dim, offset=offset
        ).reshape(slots, kv_heads, dim)
        dimensions[layer] = dim
        offset += 2 * nbytes  # skip K, then V; only K participates in Eq.3
    trailing = site_count * 8 + 4
    if offset + trailing != len(raw):
        raise ValueError("MI1 bank has trailing or malformed data")
    return keys, dimensions


def query_to_source_layer(
    query_layer: int, query_dim: int, max_query_dim: int, kv_layers: int
) -> int:
    """Mirror Gemma4's pinned shared-KV source-layer rule."""
    if query_layer < kv_layers:
        return query_layer
    return kv_layers - (2 if query_dim != max_query_dim else 1)


def alignment_by_group(
    query: FloatArray, target_keys: FloatArray, reference_keys: FloatArray
) -> FloatArray:
    """Return two mean target-minus-reference max-key margins, one per KV group."""
    q = np.asarray(query, dtype=np.float32)
    target = np.asarray(target_keys, dtype=np.float32)
    reference = np.asarray(reference_keys, dtype=np.float32)
    if q.ndim != 2 or target.ndim != 3 or reference.ndim != 3:
        raise ValueError("expected query [heads,d] and keys [slots,kv_heads,d]")
    if (
        target.shape[1:] != reference.shape[1:]
        or q.shape[0] != target.shape[1] * 4
        or q.shape[1] != target.shape[2]
    ):
        raise ValueError("Gemma4 query and KV-bank dimensions do not align")
    scale = np.float32(1.0 / np.sqrt(q.shape[-1]))
    result = np.empty(target.shape[1], dtype=np.float32)
    for group in range(target.shape[1]):
        head_scores = []
        for head in range(group * 4, (group + 1) * 4):
            target_max = np.max(target[:, group, :] @ q[head] * scale)
            reference_max = np.max(reference[:, group, :] @ q[head] * scale)
            head_scores.append(target_max - reference_max)
        result[group] = np.mean(head_scores, dtype=np.float32)
    return result


def choose_sites(
    layer_group_margins: FloatArray, *, top_layers: int = 4
) -> tuple[list[list[int]], list[float]]:
    """Choose each layer's best group, then the top layers, deterministically."""
    values = np.asarray(layer_group_margins, dtype=np.float32)
    if values.shape != (42, 2) or not 1 <= top_layers <= 42 or not np.isfinite(values).all():
        raise ValueError("expected finite alignment margins for 42 layers by 2 KV groups")
    best_groups = np.argmax(values, axis=1)  # np.argmax gives the frozen lower-index tie break
    best_scores = values[np.arange(42), best_groups]
    order = np.lexsort((np.arange(42), -best_scores))[:top_layers]
    groups = [[int(layer), int(best_groups[layer])] for layer in order]
    sites = [[layer, head] for layer, group in groups for head in range(group * 4, group * 4 + 4)]
    return sites, [float(best_scores[layer]) for layer in order]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def score_manifest(
    capture_map_path: Path, bank_map_path: Path, *, top_layers: int = 4
) -> dict[str, Any]:
    """Score calibration fixtures only; source maps contain no evaluation outputs."""
    capture_map = json.loads(capture_map_path.read_text(encoding="utf-8"))
    bank_map = json.loads(bank_map_path.read_text(encoding="utf-8"))
    banks = {entry["fixture_id"]: entry for entry in bank_map["entries"]}
    fixture_scores: dict[str, dict[str, Any]] = {}
    for entry in capture_map["entries"]:
        fixture = entry["fixture_id"]
        token_ids, queries = read_last_queries(Path(entry["capture_path"]))
        target = {
            pol: read_native_keys(Path(banks[fixture][pol]["remote_bank_path"]))
            for pol in ("A", "B")
        }
        dims = tuple(int(queries[layer].shape[-1]) for layer in range(42))
        max_dim = max(dims)
        margins: dict[str, list[list[float]]] = {}
        for polarity, opposite in (("A", "B"), ("B", "A")):
            target_keys, target_dims = target[polarity]
            reference_keys, reference_dims = target[opposite]
            if target_dims != reference_dims:
                raise ValueError(f"{fixture} bank layer layouts differ")
            kv_layers = len(target_keys)
            layer_margins: list[list[float]] = []
            for layer in range(42):
                src = query_to_source_layer(layer, dims[layer], max_dim, kv_layers)
                if target_dims[src] != dims[layer]:
                    raise ValueError(
                        f"{fixture} layer {layer} maps to dimension-mismatched KV layer {src}"
                    )
                group_margins = alignment_by_group(
                    queries[layer], target_keys[src], reference_keys[src]
                )
                layer_margins.append([float(x) for x in group_margins])
            margins[polarity] = layer_margins
        fixture_scores[fixture] = {
            "prompt_sha256": entry["prompt_sha256"],
            "capture_sha256": _sha256(Path(entry["capture_path"])),
            "prompt_token_ids_sha256": hashlib.sha256(
                np.asarray(token_ids, dtype="<i4").tobytes()
            ).hexdigest(),
            "prompt_token_count": len(token_ids),
            "bank_sha256": {
                pol: _sha256(Path(banks[fixture][pol]["remote_bank_path"])) for pol in ("A", "B")
            },
            "layer_group_margins": margins,
        }
    aggregate: dict[str, Any] = {}
    for polarity in ("A", "B"):
        matrix = np.mean(
            np.stack(
                [
                    np.asarray(fixture_scores[f]["layer_group_margins"][polarity], dtype=np.float32)
                    for f in sorted(fixture_scores)
                ]
            ),
            axis=0,
            dtype=np.float32,
        )
        sites, scores = choose_sites(matrix, top_layers=top_layers)
        aggregate[polarity] = {
            "selection_rule": (
                "mean over A01-A04 per KV group; best group per layer; top layers by "
                "descending score with ascending layer tie-break; expand selected KV "
                "group to its four contiguous Q heads"
            ),
            "selected_groups": [[site[0], site[1] // 4] for site in sites[::4]],
            "selected_query_sites": sites,
            "selected_layer_scores": scores,
            "aggregate_layer_group_margins": matrix.tolist(),
        }
    return {
        "schema_version": 1,
        "source": "frozen C11 A01-A04 no-bank query prefill and raw A/B target banks",
        "top_layers": top_layers,
        "fixtures": fixture_scores,
        "aggregate": aggregate,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-map", type=Path, required=True)
    parser.add_argument("--bank-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top-layers", type=int, default=4)
    args = parser.parse_args()
    result = score_manifest(args.capture_map, args.bank_map, top_layers=args.top_layers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)


if __name__ == "__main__":
    main()
