"""Metadata-only query-site patching for immutable native MI1 bank payloads."""

from __future__ import annotations

import math
import os
import struct
import tempfile
from pathlib import Path


def patch_native_bank_selector(
    source: Path,
    destination: Path,
    *,
    query_sites: tuple[tuple[int, int], ...],
    bank_logit_bias: float,
) -> None:
    """Copy a no-selector MI1 bank and replace only its selector metadata.

    K/V bytes are preserved verbatim. This is appropriate for distributing
    frozen selector variants of one already encoded source bank.
    """
    if not math.isfinite(bank_logit_bias):
        raise ValueError("bank logit bias must be finite")
    if len(set(query_sites)) != len(query_sites):
        raise ValueError("query sites must be unique")
    if any(not (0 <= layer < 42 and 0 <= head < 8) for layer, head in query_sites):
        raise ValueError("query site is outside Gemma4 layer/head dimensions")
    raw = source.read_bytes()
    header_size = struct.calcsize("<8sIIII")
    if len(raw) < header_size + 4:
        raise ValueError("truncated MI1 bank")
    magic, version, layer_count, slots, old_site_count = struct.unpack_from("<8sIIII", raw)
    if magic != b"MI1KV002" or version != 2 or not layer_count or not slots:
        raise ValueError("unsupported MI1 bank")
    if old_site_count != 0:
        raise ValueError("source MI1 bank must have no query-site selector")
    old_bias = struct.unpack_from("<f", raw, len(raw) - 4)[0]
    if old_bias != 0.0:
        raise ValueError("source MI1 bank must have neutral logit bias")
    payload = bytearray(
        struct.pack("<8sIIII", magic, version, layer_count, slots, len(query_sites))
    )
    payload.extend(raw[header_size:-4])
    for layer, head in query_sites:
        payload.extend(struct.pack("<II", layer, head))
    payload.extend(struct.pack("<f", bank_logit_bias))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        directory = os.open(destination.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
