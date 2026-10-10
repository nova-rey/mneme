"""Token-level KV-bank model and Eq. 2 CPU attention oracle."""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float32]


def native_bank_fingerprint(path: Path) -> str:
    """Return llama.cpp MI1's FNV-1a identity for a serialized bank.

    This deliberately mirrors ``llama_mi1::bank_fingerprint`` rather than
    using the file SHA: the server fingerprints parsed tensor content and
    query-head routing, not the binary header or source metadata.
    """
    raw = path.read_bytes()
    if len(raw) < struct.calcsize("<8sIIII"):
        raise ValueError("native MI1 bank is truncated before its header")
    magic, version, layer_count, slots, site_count = struct.unpack_from("<8sIIII", raw)
    if magic != b"MI1KV002" or version != 2 or not layer_count or not slots:
        raise ValueError("unsupported native MI1 bank fingerprint format")
    offset = struct.calcsize("<8sIIII")
    value = 14695981039346656037

    def update(data: bytes) -> None:
        nonlocal value
        for byte in data:
            value = ((value ^ byte) * 1099511628211) & 0xFFFFFFFFFFFFFFFF

    query_heads: dict[int, list[int]] = {}
    for _ in range(layer_count):
        if offset + struct.calcsize("<IIII") > len(raw):
            raise ValueError("native MI1 bank is truncated in a layer descriptor")
        layer, head_dim, kv_heads, layer_slots = struct.unpack_from("<IIII", raw, offset)
        if not head_dim or not kv_heads or layer_slots != slots:
            raise ValueError("native MI1 bank has inconsistent layer dimensions")
        update(raw[offset : offset + struct.calcsize("<IIII")])
        offset += struct.calcsize("<IIII")
        tensor_bytes = slots * head_dim * kv_heads * struct.calcsize("<f")
        if offset + 2 * tensor_bytes > len(raw):
            raise ValueError("native MI1 bank is truncated in layer K/V")
        update(raw[offset : offset + tensor_bytes])
        offset += tensor_bytes
        update(raw[offset : offset + tensor_bytes])
        offset += tensor_bytes
    for _ in range(site_count):
        if offset + struct.calcsize("<II") > len(raw):
            raise ValueError("native MI1 bank is truncated in query sites")
        layer, head = struct.unpack_from("<II", raw, offset)
        query_heads.setdefault(layer, []).append(head)
        offset += struct.calcsize("<II")
    for layer, heads in sorted(query_heads.items()):
        update(struct.pack("<I", layer))
        update(struct.pack(f"<{len(heads)}I", *heads))
    bias_bytes = struct.calcsize("<f")
    if offset + bias_bytes != len(raw):
        raise ValueError("native MI1 bank has invalid trailing data")
    update(raw[offset : offset + bias_bytes])
    return f"{value:016x}"


@dataclass(frozen=True)
class BankManifest:
    """Shape and provenance needed to bind a bank to a particular host."""

    model_sha256: str
    llama_commit: str
    architecture: str
    layer_ids: tuple[int, ...]
    head_dim: int
    kv_heads_by_layer: tuple[int, ...]
    slot_count: int
    key_rope_phase: str = "zero_relative_phase"
    operator: str = "eq2_augmented_attention"
    schema_version: int = 1
    tokenizer: str = "llama.cpp pinned Gemma4 tokenizer"
    tokenization: str = "llama_tokenize(add_special=true,parse_special=false)"
    selector_rule: str = "Appendix-C Eq.3 KV-group margin; per-layer top-k, global top-m"
    query_groups: tuple[tuple[int, int], ...] = ()
    query_sites: tuple[tuple[int, int], ...] = ()
    source_kv_by_query_layer: tuple[tuple[int, int], ...] = ()
    bank_logit_bias: float = 0.0
    # Gemma4 mixes local-window and global layers with different head widths.
    # An empty tuple retains the legacy uniform ``head_dim`` representation.
    head_dim_by_layer: tuple[int, ...] = ()


@dataclass(frozen=True)
class MemoryBank:
    """Per-token key/value slots, indexed by layer and KV-head group.

    Arrays are float32 with shape ``[slots, kv_heads, head_dim]``. No vector
    averaging is performed; slot order and token identity are retained.
    """

    manifest: BankManifest
    keys: dict[int, FloatArray]
    values: dict[int, FloatArray]
    source_text: str
    token_ids: tuple[int, ...]

    def _head_dims(self) -> tuple[int, ...]:
        if self.manifest.head_dim_by_layer:
            if len(self.manifest.head_dim_by_layer) != len(self.manifest.layer_ids):
                raise ValueError("per-layer head dimensions do not match layer IDs")
            if self.manifest.head_dim not in (0, *set(self.manifest.head_dim_by_layer)):
                raise ValueError("legacy head dimension conflicts with per-layer dimensions")
            return self.manifest.head_dim_by_layer
        if self.manifest.head_dim <= 0:
            raise ValueError("uniform head dimension must be positive")
        return (self.manifest.head_dim,) * len(self.manifest.layer_ids)

    def validate(self) -> None:
        if self.manifest.slot_count != len(self.token_ids):
            raise ValueError("manifest slot count does not match token IDs")
        if self.manifest.slot_count == 0:
            raise ValueError("empty banks are not serializable")
        if set(self.keys) != set(self.manifest.layer_ids):
            raise ValueError("key layer IDs do not match manifest")
        if set(self.values) != set(self.manifest.layer_ids):
            raise ValueError("value layer IDs do not match manifest")
        if not np.isfinite(self.manifest.bank_logit_bias):
            raise ValueError("bank-level logit prior must be finite")
        if len(set(self.manifest.query_sites)) != len(self.manifest.query_sites):
            raise ValueError("query selector sites must be unique")
        if len(set(self.manifest.query_groups)) != len(self.manifest.query_groups):
            raise ValueError("query selector KV groups must be unique")
        if any(
            layer < 0 or layer >= 42 or group < 0 or group >= 2
            for layer, group in self.manifest.query_groups
        ):
            raise ValueError("query selector KV group index exceeds Gemma4's 2 KV groups")
        if any(
            layer < 0 or layer >= 42 or head < 0 or head >= 8
            for layer, head in self.manifest.query_sites
        ):
            raise ValueError("query selector site head index exceeds Gemma4's 8 query heads")
        head_dims = self._head_dims()
        for i, layer in enumerate(self.manifest.layer_ids):
            expected = (
                self.manifest.slot_count,
                self.manifest.kv_heads_by_layer[i],
                head_dims[i],
            )
            if self.keys[layer].shape != expected or self.values[layer].shape != expected:
                raise ValueError(f"layer {layer} bank shape must be {expected}")
            if not np.isfinite(self.keys[layer]).all() or not np.isfinite(self.values[layer]).all():
                raise ValueError(f"layer {layer} contains non-finite bank values")

    def save(self, path: Path) -> str:
        """Write NPZ payload plus JSON manifest atomically and return SHA-256."""
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        arrays: dict[str, NDArray[Any]] = {}
        for layer in self.manifest.layer_ids:
            arrays[f"k_{layer}"] = np.asarray(self.keys[layer], dtype=np.float32)
            arrays[f"v_{layer}"] = np.asarray(self.values[layer], dtype=np.float32)
        with tmp.open("wb") as stream:
            np.savez(stream, **cast(Any, arrays))
            stream.flush()
        tmp.replace(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        native_hash = self.save_native(path.with_suffix(".mi1"))
        manifest_path = path.with_suffix(path.suffix + ".json")
        manifest_tmp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
        payload = {
            "manifest": asdict(self.manifest),
            "source_text": self.source_text,
            "source_text_sha256": hashlib.sha256(self.source_text.encode("utf-8")).hexdigest(),
            "token_ids": list(self.token_ids),
            "bank_sha256": digest,
            "native_bank_sha256": native_hash,
        }
        manifest_tmp.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        manifest_tmp.replace(manifest_path)
        return digest

    def save_native(self, path: Path) -> str:
        """Write the little-endian bank file consumed by the isolated C++ port."""
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("wb") as stream:
            stream.write(
                struct.pack(
                    "<8sIIII",
                    b"MI1KV002",
                    2,
                    len(self.manifest.layer_ids),
                    self.manifest.slot_count,
                    len(self.manifest.query_sites),
                )
            )
            head_dims = self._head_dims()
            for index, layer in enumerate(self.manifest.layer_ids):
                keys = np.ascontiguousarray(self.keys[layer], dtype="<f4")
                values = np.ascontiguousarray(self.values[layer], dtype="<f4")
                kv_heads = self.manifest.kv_heads_by_layer[self.manifest.layer_ids.index(layer)]
                stream.write(
                    struct.pack(
                        "<IIII", layer, head_dims[index], kv_heads, self.manifest.slot_count
                    )
                )
                stream.write(keys.tobytes(order="C"))
                stream.write(values.tobytes(order="C"))
            for layer, head in self.manifest.query_sites:
                stream.write(struct.pack("<II", layer, head))
            stream.write(struct.pack("<f", self.manifest.bank_logit_bias))
            stream.flush()
        tmp.replace(path)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @classmethod
    def load(cls, path: Path) -> MemoryBank:
        sidecar = json.loads(path.with_suffix(path.suffix + ".json").read_text(encoding="utf-8"))
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != sidecar["bank_sha256"]:
            raise ValueError("memory-bank payload hash mismatch")
        raw = sidecar["manifest"]
        raw["layer_ids"] = tuple(raw["layer_ids"])
        raw["kv_heads_by_layer"] = tuple(raw["kv_heads_by_layer"])
        raw["query_sites"] = tuple(tuple(site) for site in raw.get("query_sites", ()))
        raw["query_groups"] = tuple(tuple(site) for site in raw.get("query_groups", ()))
        raw["source_kv_by_query_layer"] = tuple(
            tuple(site) for site in raw.get("source_kv_by_query_layer", ())
        )
        raw["head_dim_by_layer"] = tuple(raw.get("head_dim_by_layer", ()))
        manifest = BankManifest(**raw)
        with np.load(path, allow_pickle=False) as data:
            keys = {
                layer: np.asarray(data[f"k_{layer}"], dtype=np.float32)
                for layer in manifest.layer_ids
            }
            values = {
                layer: np.asarray(data[f"v_{layer}"], dtype=np.float32)
                for layer in manifest.layer_ids
            }
        result = cls(manifest, keys, values, sidecar["source_text"], tuple(sidecar["token_ids"]))
        result.validate()
        return result

    @classmethod
    def from_native_capture(
        cls,
        path: Path,
        *,
        source_text: str,
        model_sha256: str,
        llama_commit: str,
        architecture: str = "gemma4-e4b",
        tokenizer: str = "llama.cpp pinned Gemma4 tokenizer",
    ) -> MemoryBank:
        """Read the isolated native encoder's exact per-token K/V capture.

        The capture contains token IDs followed by each KV layer's canonical
        normalized pre-RoPE K and normalized V. Arrays retain token order and
        have the same ``[slots, kv_heads, head_dim]`` layout consumed by the
        native MI1 side-bank serializer.
        """
        raw = path.read_bytes()
        header_size = struct.calcsize("<8sIII")
        if len(raw) < header_size:
            raise ValueError("native capture is truncated before its header")
        magic, version, layer_count, slot_count = struct.unpack("<8sIII", raw[:header_size])
        if magic != b"MI1CAP01" or version != 1:
            raise ValueError("unsupported native capture format")
        offset = header_size
        token_bytes = slot_count * struct.calcsize("<i")
        if len(raw) < offset + token_bytes:
            raise ValueError("native capture is truncated in token IDs")
        token_ids = tuple(struct.unpack_from(f"<{slot_count}i", raw, offset))
        offset += token_bytes
        layer_ids: list[int] = []
        kv_heads_by_layer: list[int] = []
        head_dim_by_layer: list[int] = []
        keys: dict[int, FloatArray] = {}
        values: dict[int, FloatArray] = {}
        layer_header_size = struct.calcsize("<iiii")
        for _ in range(layer_count):
            if len(raw) < offset + layer_header_size:
                raise ValueError("native capture is truncated in a layer header")
            layer, head_dim, kv_heads, layer_slots = struct.unpack_from("<iiii", raw, offset)
            offset += layer_header_size
            if layer_slots != slot_count or min(head_dim, kv_heads) <= 0:
                raise ValueError("native capture layer dimensions are inconsistent")
            value_count = slot_count * kv_heads * head_dim
            value_bytes = value_count * np.dtype("<f4").itemsize
            if len(raw) < offset + 2 * value_bytes:
                raise ValueError("native capture is truncated in K/V values")
            key_array = np.frombuffer(raw, dtype="<f4", count=value_count, offset=offset).astype(
                np.float32, copy=True
            )
            offset += value_bytes
            value_array = np.frombuffer(raw, dtype="<f4", count=value_count, offset=offset).astype(
                np.float32, copy=True
            )
            offset += value_bytes
            layer_ids.append(layer)
            kv_heads_by_layer.append(kv_heads)
            head_dim_by_layer.append(head_dim)
            keys[layer] = key_array.reshape(slot_count, kv_heads, head_dim)
            values[layer] = value_array.reshape(slot_count, kv_heads, head_dim)
        if offset != len(raw):
            raise ValueError("native capture has trailing or malformed bytes")
        if not layer_ids:
            raise ValueError("native capture contains no KV layers")
        dimensions = set(head_dim_by_layer)
        manifest = BankManifest(
            model_sha256=model_sha256,
            llama_commit=llama_commit,
            architecture=architecture,
            layer_ids=tuple(layer_ids),
            head_dim=next(iter(dimensions)) if len(dimensions) == 1 else 0,
            kv_heads_by_layer=tuple(kv_heads_by_layer),
            slot_count=slot_count,
            tokenizer=tokenizer,
            head_dim_by_layer=tuple(head_dim_by_layer),
        )
        bank = cls(manifest, keys, values, source_text, token_ids)
        bank.validate()
        return bank


class BankAttachment:
    """Explicit process-local bank lifecycle for research harnesses.

    Replacement is atomic under a lock. Disabling retains the bank for fast
    re-enable; clear removes it. Each operation increments an audit revision.
    """

    def __init__(self) -> None:
        self._bank: MemoryBank | None = None
        self._enabled = False
        self._revision = 0
        self._lock = RLock()

    def attach(self, bank: MemoryBank) -> int:
        bank.validate()
        with self._lock:
            self._bank = bank
            self._enabled = True
            self._revision += 1
            return self._revision

    def replace(self, bank: MemoryBank) -> int:
        return self.attach(bank)

    def disable(self) -> int:
        with self._lock:
            self._enabled = False
            self._revision += 1
            return self._revision

    def clear(self) -> int:
        with self._lock:
            self._bank = None
            self._enabled = False
            self._revision += 1
            return self._revision

    def snapshot(self) -> tuple[MemoryBank | None, bool, int]:
        with self._lock:
            return self._bank, self._enabled, self._revision


def _rms_norm(x: FloatArray, scale: FloatArray, eps: float) -> FloatArray:
    variance = np.mean(np.square(x.astype(np.float64)), axis=-1, keepdims=True)
    normalized = (x / np.sqrt(variance + eps).astype(np.float32)) * scale
    return np.asarray(normalized, dtype=np.float32)


def encode_slots(
    hidden: dict[int, FloatArray],
    w_k: dict[int, FloatArray],
    w_v: dict[int, FloatArray],
    k_norm: dict[int, FloatArray],
    v_norm_scale: dict[int, FloatArray],
    *,
    eps: float,
    model_sha256: str,
    llama_commit: str,
    architecture: str,
    token_ids: tuple[int, ...],
    source_text: str = "",
) -> MemoryBank:
    """Apply Gemma's native KV projections/norms without averaging slots.

    ``hidden`` is the per-token attention-normalized representation at each
    selected layer (layer-indexed in the input dict). Gemma's RMS key norm is
    applied after projection. V uses the same RMS formula and epsilon as the
    pinned graph's value normalization. The caller must capture selected
    vectors from the frozen base host and supply native projection weights.
    Keys are intentionally stored at relative RoPE phase zero per Appendix G.
    """
    layers = tuple(sorted(hidden))
    if not layers or len(token_ids) == 0:
        raise ValueError("a bank requires at least one selected layer and token slot")
    if len(token_ids) != next(iter(hidden.values())).shape[0]:
        raise ValueError("token IDs do not align with hidden token slots")
    keys: dict[int, FloatArray] = {}
    values: dict[int, FloatArray] = {}
    kv_heads: list[int] = []
    head_dims: list[int] = []
    for layer in layers:
        projected_k = hidden[layer] @ w_k[layer].T
        projected_v = hidden[layer] @ w_v[layer].T
        head_dim = k_norm[layer].shape[-1]
        if projected_k.shape[-1] % head_dim or projected_v.shape[-1] % head_dim:
            raise ValueError(f"layer {layer} projection cannot be divided into head dimensions")
        n_kv = projected_k.shape[-1] // head_dim
        if projected_v.shape[-1] // head_dim != n_kv:
            raise ValueError(f"layer {layer} K/V head counts differ")
        keys[layer] = _rms_norm(
            projected_k.reshape(len(token_ids), n_kv, head_dim), k_norm[layer], eps
        ).astype(np.float32)
        values[layer] = _rms_norm(
            projected_v.reshape(len(token_ids), n_kv, head_dim), v_norm_scale[layer], eps
        ).astype(np.float32)
        kv_heads.append(n_kv)
        head_dims.append(head_dim)
    manifest = BankManifest(
        model_sha256=model_sha256,
        llama_commit=llama_commit,
        architecture=architecture,
        layer_ids=layers,
        head_dim=head_dims[0] if len(set(head_dims)) == 1 else 0,
        kv_heads_by_layer=tuple(kv_heads),
        slot_count=len(token_ids),
        head_dim_by_layer=tuple(head_dims),
    )
    result = MemoryBank(manifest, keys, values, source_text, token_ids)
    result.validate()
    return result


def augmented_attention(
    query: FloatArray,
    prompt_keys: FloatArray,
    prompt_values: FloatArray,
    *,
    bank_keys: FloatArray | None = None,
    bank_values: FloatArray | None = None,
    mask: FloatArray | None = None,
    scale: float | None = None,
    enabled: bool = True,
) -> FloatArray:
    """CPU oracle for causal GQA Eq. 2 attention.

    Shapes: Q ``[queries, q_heads, d]``; K/V ``[slots, kv_heads, d]``.
    Query heads map contiguously to KV heads. The mask applies to prompt slots
    only and uses zero for visible / negative infinity for masked. Bank slots
    are visible to every query at virtual RoPE phase zero. The disabled or
    empty-bank path is exactly ordinary prompt attention. The Gemma runtime
    uses the separately tested generation-side selector below.
    """
    q = np.asarray(query, dtype=np.float32)
    pk = np.asarray(prompt_keys, dtype=np.float32)
    pv = np.asarray(prompt_values, dtype=np.float32)
    if q.ndim != 3 or pk.ndim != 3 or pv.shape != pk.shape:
        raise ValueError("Q and prompt K/V must have [tokens, heads, head_dim] shapes")
    if q.shape[-1] != pk.shape[-1] or q.shape[1] % pk.shape[1]:
        raise ValueError("query heads must evenly group over matching KV heads")
    if pk.shape[0] == 0:
        raise ValueError("prompt attention requires at least one unmasked key")
    if mask is None:
        prompt_mask = np.zeros((q.shape[0], pk.shape[0]), dtype=np.float32)
    else:
        prompt_mask = np.asarray(mask, dtype=np.float32)
        if prompt_mask.shape != (q.shape[0], pk.shape[0]):
            raise ValueError("mask must have shape [queries, prompt_slots]")
    use_bank = (
        enabled
        and bank_keys is not None
        and bank_values is not None
        and np.asarray(bank_keys).shape[0] > 0
    )
    if use_bank:
        bk = np.asarray(bank_keys, dtype=np.float32)
        bv = np.asarray(bank_values, dtype=np.float32)
        if bk.ndim != 3 or bv.shape != bk.shape or bk.shape[1:] != pk.shape[1:]:
            raise ValueError("bank K/V must match prompt KV-head and head dimensions")
        keys = np.concatenate((pk, bk), axis=0)
        values = np.concatenate((pv, bv), axis=0)
        additive = np.concatenate(
            (prompt_mask, np.zeros((q.shape[0], bk.shape[0]), dtype=np.float32)), axis=1
        )
    else:
        keys, values, additive = pk, pv, prompt_mask
    gqa = q.shape[1] // keys.shape[1]
    output = np.empty_like(q)
    factor = scale if scale is not None else 1.0 / np.sqrt(q.shape[-1])
    for qi in range(q.shape[0]):
        for head in range(q.shape[1]):
            kvh = head // gqa
            scores = (keys[:, kvh] @ q[qi, head]) * factor + additive[qi]
            finite = np.isfinite(scores)
            if not finite.any():
                raise ValueError("attention mask excludes every prompt and bank slot")
            scores = scores - np.max(scores[finite])
            weights = np.exp(scores, where=finite, out=np.zeros_like(scores))
            weights /= weights.sum()
            output[qi, head] = weights @ values[:, kvh]
    return output


def _rope_interleaved(x: FloatArray, position: int, *, base: float = 10000.0) -> FloatArray:
    """Small RoPE oracle using interleaved even/odd pairs for phase checks."""
    value = np.asarray(x, dtype=np.float32)
    if value.shape[-1] % 2:
        raise ValueError("RoPE head dimension must be even")
    pair = value.reshape(*value.shape[:-1], value.shape[-1] // 2, 2)
    theta = np.power(base, -np.arange(pair.shape[-2], dtype=np.float64) * 2.0 / value.shape[-1])
    angle = float(position) * theta
    cos = np.cos(angle).astype(np.float32)
    sin = np.sin(angle).astype(np.float32)
    even, odd = pair[..., 0], pair[..., 1]
    result = np.stack((even * cos - odd * sin, even * sin + odd * cos), axis=-1)
    return result.reshape(value.shape)


def generation_side_attention(
    query_pre_rope: FloatArray,
    prompt_keys_rope: FloatArray,
    prompt_values: FloatArray,
    *,
    bank_keys_pre_rope: FloatArray,
    bank_values: FloatArray,
    positions: tuple[int, ...],
    scale: float | None = None,
    rope_base: float = 10000.0,
) -> FloatArray:
    """Apply MI1 at the last query with bank K aligned to that absolute pos.

    Earlier prompt queries are masked from the bank. The final query sees
    relative phase ``delta = 0``. Prompt K is already RoPE-rotated and shaped
    ``[queries, prompt_slots, kv_heads, head_dim]``.
    """
    q = np.asarray(query_pre_rope, dtype=np.float32)
    pk = np.asarray(prompt_keys_rope, dtype=np.float32)
    pv = np.asarray(prompt_values, dtype=np.float32)
    bk = np.asarray(bank_keys_pre_rope, dtype=np.float32)
    bv = np.asarray(bank_values, dtype=np.float32)
    if q.ndim != 3 or pk.ndim != 4 or pv.shape != pk.shape:
        raise ValueError(
            "expected Q [queries, heads, d] and prompt K/V [queries, slots, kv_heads, d]"
        )
    if len(positions) != q.shape[0] or pk.shape[0] != q.shape[0]:
        raise ValueError("one absolute position and prompt K/V row is required per query")
    if q.shape[-1] % 2 or bk.ndim != 3 or bv.shape != bk.shape:
        raise ValueError("bank tensors must be [slots, kv_heads, even head_dim]")
    output = np.empty_like(q)
    final = q.shape[0] - 1
    for index, position in enumerate(positions):
        q_rot = _rope_interleaved(q[index : index + 1], position, base=rope_base)
        if index == final:
            bank_rot = _rope_interleaved(bk, position, base=rope_base)
            output[index : index + 1] = augmented_attention(
                q_rot,
                pk[index],
                pv[index],
                bank_keys=bank_rot,
                bank_values=bv,
                scale=scale,
            )
        else:
            output[index : index + 1] = augmented_attention(
                q_rot, pk[index], pv[index], scale=scale
            )
    return output
