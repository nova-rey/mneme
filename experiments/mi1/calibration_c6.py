"""Freeze a direct context-window test of the C5 request matrix."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from experiments.mi1.calibration import canonical_bytes
from experiments.mi1.calibration_c5 import build_c5_plan


def build_c6_plan() -> dict[str, Any]:
    """Reuse C5 requests byte-for-byte while increasing server context to 4096."""
    parent = build_c5_plan()
    coordinates: list[dict[str, Any]] = []
    for source in parent["coordinates"]:
        coordinate = copy.deepcopy(source)
        previous_id = coordinate["coordinate_id"]
        coordinate["coordinate_id"] = previous_id.replace("C5-", "C6-", 1)
        coordinate["suite"] = "calibration_c6"
        coordinate["metadata"]["parent_coordinate_id"] = previous_id
        coordinates.append(coordinate)
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "revision": "C6-same-requests-context-4096",
        "purpose": (
            "Directly test C5's observed 512-token context exhaustion. Every request, seed, "
            "bank, and scoring expectation is copied unchanged; only the isolated server "
            "context capacity increases to 4096. Diagnostic, not scored Test A/B/C."
        ),
        "host_model": parent["host_model"],
        "model_gguf_sha256": parent["model_gguf_sha256"],
        "llama_cpp_commit": parent["llama_cpp_commit"],
        "server_context_size": 4096,
        "request_matrix_sha256": hashlib.sha256(
            canonical_bytes([row["request_sha256"] for row in parent["coordinates"]])
        ).hexdigest(),
        "coordinates": coordinates,
    }
