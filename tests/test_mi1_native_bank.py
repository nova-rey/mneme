from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from experiments.mi1.native.bank import (
    BankAttachment,
    BankManifest,
    MemoryBank,
    augmented_attention,
    encode_slots,
    generation_side_attention,
)


def test_eq2_bank_adds_token_level_slots_and_routes_over_gqa_heads() -> None:
    # Two query heads share one KV head. The bank has two distinct slots; its
    # output must be their attention-weighted combination, not an averaged KV.
    q = np.array([[[1.0, 0.0], [1.0, 0.0]]], dtype=np.float32)
    pk = np.zeros((1, 1, 2), dtype=np.float32)
    pv = np.zeros_like(pk)
    bk = np.array([[[4.0, 0.0]], [[-1.0, 0.0]]], dtype=np.float32)
    bv = np.array([[[3.0, 1.0]], [[-2.0, 0.0]]], dtype=np.float32)
    out = augmented_attention(q, pk, pv, bank_keys=bk, bank_values=bv)
    assert out.shape == (1, 2, 2)
    assert np.allclose(out[0, 0], out[0, 1])
    # A collapsed mean key/value would produce a materially different result.
    collapsed = augmented_attention(
        q,
        pk,
        pv,
        bank_keys=bk.mean(axis=0, keepdims=True),
        bank_values=bv.mean(axis=0, keepdims=True),
    )
    assert not np.allclose(out, collapsed)


def test_mask_applies_to_prompt_but_not_virtual_phase_zero_bank_slots() -> None:
    q = np.array([[[1.0, 0.0]]], dtype=np.float32)
    pk = np.array([[[10.0, 0.0]], [[0.0, 1.0]]], dtype=np.float32)
    pv = np.array([[[10.0, 0.0]], [[0.0, 1.0]]], dtype=np.float32)
    bk = np.array([[[1.0, 0.0]]], dtype=np.float32)
    bv = np.array([[[0.0, 5.0]]], dtype=np.float32)
    mask = np.array([[-np.inf, 0.0]], dtype=np.float32)
    out = augmented_attention(q, pk, pv, bank_keys=bk, bank_values=bv, mask=mask)
    assert out[0, 0, 1] > 2.0
    assert np.isfinite(out).all()


def test_disabled_or_empty_bank_is_exact_noop() -> None:
    q = np.array([[[0.2, 0.5], [0.8, -0.1]]], dtype=np.float32)
    pk = np.array([[[1.0, 0.0]], [[0.0, 1.0]]], dtype=np.float32)
    pv = np.array([[[2.0, 0.0]], [[0.0, 4.0]]], dtype=np.float32)
    expected = augmented_attention(q, pk, pv)
    empty = np.empty((0, 1, 2), dtype=np.float32)
    assert np.array_equal(
        expected, augmented_attention(q, pk, pv, bank_keys=empty, bank_values=empty)
    )
    bk = np.array([[[2.0, 0.0]]], dtype=np.float32)
    bv = np.array([[[8.0, 0.0]]], dtype=np.float32)
    assert np.array_equal(
        expected, augmented_attention(q, pk, pv, bank_keys=bk, bank_values=bv, enabled=False)
    )


def test_rejects_masking_every_prompt_and_bank_slot() -> None:
    q = np.ones((1, 1, 2), dtype=np.float32)
    kv = np.ones((1, 1, 2), dtype=np.float32)
    with pytest.raises(ValueError, match="excludes every"):
        augmented_attention(q, kv, kv, mask=np.array([[-np.inf]], dtype=np.float32))


@pytest.mark.parametrize("final_position", [0, 127, 511, 512, 900])
def test_generation_side_bank_uses_zero_relative_rope_phase(final_position: int) -> None:
    # Query zero is an earlier prefill token and must not see the bank. The
    # final query sees the bank after both Q and K are rotated to the same
    # absolute position, including positions beyond the Gemma SWA window.
    q = np.array([[[1.0, 0.2, -0.3, 0.7]], [[0.4, -0.9, 0.1, 0.2]]], dtype=np.float32)
    pk = np.zeros((2, 1, 1, 4), dtype=np.float32)
    pv = np.zeros_like(pk)
    bk = np.array([[[0.3, 0.8, 0.6, -0.2]]], dtype=np.float32)
    bv = np.array([[[2.0, 1.0, -1.0, 0.5]]], dtype=np.float32)
    result = generation_side_attention(
        q,
        pk,
        pv,
        bank_keys_pre_rope=bk,
        bank_values=bv,
        positions=(final_position - 1, final_position),
    )
    baseline = augmented_attention(q[0:1], pk[0], pv[0])
    np.testing.assert_allclose(result[0:1], baseline, rtol=1e-6, atol=1e-6)

    # Equal-position rotations preserve q·k, so the bank contribution is
    # invariant to absolute position (the δ=0 claim).
    expected = augmented_attention(q[1:2], pk[1], pv[1], bank_keys=bk, bank_values=bv)
    np.testing.assert_allclose(result[1:2], expected, rtol=1e-5, atol=1e-5)


def test_gemma_projection_norms_keep_each_token_slot() -> None:
    hidden = {3: np.array([[1.0, 2.0], [4.0, 1.0]], dtype=np.float32)}
    wk = {3: np.eye(2, dtype=np.float32)}
    wv = {3: np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32)}
    norm = {3: np.ones((2,), dtype=np.float32)}
    bank = encode_slots(
        hidden,
        wk,
        wv,
        norm,
        norm,
        eps=1e-6,
        model_sha256="a" * 64,
        llama_commit="4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        architecture="gemma4-e4b",
        token_ids=(13, 29),
    )
    assert bank.manifest.layer_ids == (3,)
    assert bank.manifest.head_dim == 2
    assert bank.manifest.kv_heads_by_layer == (1,)
    assert bank.keys[3].shape == (2, 1, 2)
    assert bank.values[3].shape == (2, 1, 2)
    assert not np.array_equal(bank.keys[3][0], bank.keys[3][1])


def test_bank_save_reload_and_fresh_process_reopen(tmp_path: Path) -> None:
    manifest = BankManifest(
        model_sha256="b" * 64,
        llama_commit="4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        architecture="gemma4-e4b",
        layer_ids=(1, 4),
        head_dim=2,
        kv_heads_by_layer=(1, 2),
        slot_count=2,
        query_groups=((2, 0),),
        query_sites=((2, 1), (2, 2)),
        source_kv_by_query_layer=((2, 1),),
        bank_logit_bias=float(np.log(2.0)),
    )
    bank = MemoryBank(
        manifest,
        {
            1: np.arange(4, dtype=np.float32).reshape(2, 1, 2),
            4: np.arange(8, dtype=np.float32).reshape(2, 2, 2),
        },
        {
            1: np.arange(4, dtype=np.float32).reshape(2, 1, 2) + 1,
            4: np.arange(8, dtype=np.float32).reshape(2, 2, 2) + 1,
        },
        "fixture memory, stored outside the recipient prompt",
        (11, 22),
    )
    path = tmp_path / "bank.npz"
    expected_hash = bank.save(path)
    native_path = path.with_suffix(".mi1")
    native_hash = bank.save_native(native_path)
    reopened = MemoryBank.load(path)
    assert expected_hash
    assert native_hash and native_path.read_bytes()[:8] == b"MI1KV002"
    native_header = struct.unpack("<8sIIII", native_path.read_bytes()[:24])
    assert native_header == (b"MI1KV002", 2, 2, 2, 2)
    assert reopened.manifest == manifest
    assert reopened.source_text == bank.source_text
    sidecar = __import__("json").loads(path.with_suffix(".npz.json").read_text())
    assert sidecar["native_bank_sha256"] == native_hash
    for layer in manifest.layer_ids:
        np.testing.assert_array_equal(reopened.keys[layer], bank.keys[layer])
        np.testing.assert_array_equal(reopened.values[layer], bank.values[layer])
    program = (
        "from pathlib import Path; "
        "from experiments.mi1.native.bank import MemoryBank; "
        f"b=MemoryBank.load(Path({str(path)!r})); "
        "print(b.manifest.architecture, b.manifest.slot_count, b.manifest.layer_ids)"
    )
    result = subprocess.run(
        [sys.executable, "-c", program], check=True, capture_output=True, text=True
    )
    assert result.stdout.strip() == "gemma4-e4b 2 (1, 4)"


@pytest.mark.parametrize(
    ("query_groups", "query_sites", "message"),
    [
        (((2, 2),), (), "KV group index exceeds Gemma4's 2 KV groups"),
        (((2, 0),), ((2, 8),), "query selector site head index exceeds Gemma4's 8 query heads"),
    ],
)
def test_bank_selector_indices_match_gemma4_dimensions(
    query_groups: tuple[tuple[int, int], ...],
    query_sites: tuple[tuple[int, int], ...],
    message: str,
) -> None:
    manifest = BankManifest(
        model_sha256="b" * 64,
        llama_commit="4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        architecture="gemma4-e4b",
        layer_ids=(1,),
        head_dim=2,
        kv_heads_by_layer=(2,),
        slot_count=1,
        query_groups=query_groups,
        query_sites=query_sites,
    )
    bank = MemoryBank(
        manifest,
        {1: np.zeros((1, 2, 2), dtype=np.float32)},
        {1: np.zeros((1, 2, 2), dtype=np.float32)},
        "selector validation fixture",
        (11,),
    )
    with pytest.raises(ValueError, match=message):
        bank.validate()


def test_reads_exact_tokenwise_native_encoder_capture(tmp_path: Path) -> None:
    path = tmp_path / "captured.mi1cap"
    with path.open("wb") as stream:
        stream.write(struct.pack("<8sIII", b"MI1CAP01", 1, 2, 2))
        stream.write(struct.pack("<2i", 2, 991))
        for layer, kv_heads in ((0, 2), (3, 1)):
            keys = np.arange(2 * kv_heads * 4, dtype="<f4") + layer
            values = keys + 100
            stream.write(struct.pack("<iiii", layer, 4, kv_heads, 2))
            stream.write(keys.tobytes())
            stream.write(values.tobytes())

    bank = MemoryBank.from_native_capture(
        path,
        source_text="known source text",
        model_sha256="a" * 64,
        llama_commit="4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
    )
    assert bank.token_ids == (2, 991)
    assert bank.manifest.layer_ids == (0, 3)
    assert bank.manifest.kv_heads_by_layer == (2, 1)
    assert bank.keys[0].shape == (2, 2, 4)
    assert bank.values[3].shape == (2, 1, 4)
    np.testing.assert_array_equal(bank.keys[3].reshape(-1), np.arange(8) + 3)


def test_native_encoder_capture_rejects_truncation_and_trailing_bytes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "captured.mi1cap"
    path.write_bytes(struct.pack("<8sIII", b"MI1CAP01", 1, 0, 1))
    with pytest.raises(ValueError, match="truncated in token IDs"):
        MemoryBank.from_native_capture(
            path,
            source_text="source",
            model_sha256="a" * 64,
            llama_commit="pin",
        )


def test_native_capture_preserves_mixed_swa_and_global_head_widths(tmp_path: Path) -> None:
    path = tmp_path / "mixed-width.mi1cap"
    with path.open("wb") as stream:
        stream.write(struct.pack("<8sIII", b"MI1CAP01", 1, 2, 2))
        stream.write(struct.pack("<2i", 2, 3))
        for layer, width in ((0, 256), (1, 512)):
            stream.write(struct.pack("<4i", layer, width, 1, 2))
            values = np.arange(2 * width, dtype="<f4")
            stream.write(values.tobytes())
            stream.write((values + 1).tobytes())

    bank = MemoryBank.from_native_capture(
        path,
        source_text="two-token source",
        model_sha256="e" * 64,
        llama_commit="pinned",
    )
    assert bank.manifest.layer_ids == (0, 1)
    assert bank.manifest.head_dim == 0
    assert bank.manifest.head_dim_by_layer == (256, 512)
    assert bank.keys[0].shape == (2, 1, 256)
    assert bank.keys[1].shape == (2, 1, 512)

    path_npy = tmp_path / "mixed-width.npz"
    bank.save(path_npy)
    reopened = MemoryBank.load(path_npy)
    assert reopened.manifest.head_dim_by_layer == (256, 512)
    native = path_npy.with_suffix(".mi1").read_bytes()
    offset = struct.calcsize("<8sIIII")
    first = struct.unpack_from("<IIII", native, offset)
    second_offset = offset + struct.calcsize("<IIII") + 2 * 1 * 256 * 4 * 2
    second = struct.unpack_from("<IIII", native, second_offset)
    assert first == (0, 256, 1, 2)
    assert second == (1, 512, 1, 2)


def test_corrupt_bank_payload_fails_closed(tmp_path: Path) -> None:
    manifest = BankManifest("c" * 64, "pin", "gemma4-e4b", (1,), 2, (1,), 1)
    bank = MemoryBank(
        manifest,
        {1: np.ones((1, 1, 2), dtype=np.float32)},
        {1: np.ones((1, 1, 2), dtype=np.float32)},
        "source",
        (1,),
    )
    path = tmp_path / "bank.npz"
    bank.save(path)
    with path.open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(ValueError, match="hash mismatch"):
        MemoryBank.load(path)


def _small_bank(value: float) -> MemoryBank:
    manifest = BankManifest("d" * 64, "pin", "gemma4-e4b", (1,), 2, (1,), 1)
    vals = np.full((1, 1, 2), value, dtype=np.float32)
    return MemoryBank(manifest, {1: vals}, {1: vals}, f"fixture-{value}", (1,))


def test_attachment_lifecycle_attach_disable_replace_clear() -> None:
    handle = BankAttachment()
    assert handle.snapshot() == (None, False, 0)
    assert handle.attach(_small_bank(1.0)) == 1
    first, enabled, _ = handle.snapshot()
    assert enabled and first is not None and first.source_text == "fixture-1.0"
    assert handle.disable() == 2
    retained, enabled, _ = handle.snapshot()
    assert not enabled and retained is first
    assert handle.replace(_small_bank(2.0)) == 3
    replacement, enabled, _ = handle.snapshot()
    assert enabled and replacement is not None and replacement.source_text == "fixture-2.0"
    assert handle.clear() == 4
    assert handle.snapshot() == (None, False, 4)
