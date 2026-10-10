"""Freeze the original simple C3 fixture/prompt matrix at corrected context."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from experiments.mi1.calibration import canonical_bytes
from experiments.mi1.calibration_c3 import build_c3_plan


def build_c8_plan() -> dict[str, Any]:
    """Reissue C3's exact requests with fresh IDs; only server context changes."""
    parent = build_c3_plan()
    coordinates: list[dict[str, Any]] = []
    for source in parent["coordinates"]:
        coordinate = copy.deepcopy(source)
        previous_id = coordinate["coordinate_id"]
        coordinate["coordinate_id"] = previous_id.replace("C3-", "C8-", 1)
        coordinate["suite"] = "calibration_c8"
        coordinate["metadata"]["parent_coordinate_id"] = previous_id
        coordinates.append(coordinate)
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "revision": "C8-C3-simple-prompts-context-8192",
        "purpose": (
            "Retest the exact simple directed-reachability prompts whose visible controls "
            "scored 8/8 in C3, now with context capacity 8192. Prompts, seeds, request "
            "allowance, source banks, selector configurations, and rubric remain unchanged. "
            "Diagnostic calibration, not scored Test A/B/C."
        ),
        "host_model": parent["host_model"],
        "model_gguf_sha256": parent["model_gguf_sha256"],
        "llama_cpp_commit": parent["llama_cpp_commit"],
        "server_context_size": 8192,
        "request_matrix_sha256": hashlib.sha256(
            canonical_bytes([row["request_sha256"] for row in coordinates])
        ).hexdigest(),
        "coordinates": coordinates,
    }
