"""Freeze a larger generation-budget replay of the C5 MI1 matrix."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from experiments.mi1.calibration import canonical_bytes
from experiments.mi1.calibration_c5 import build_c5_plan


def build_c7_plan() -> dict[str, Any]:
    """Keep C5 semantics fixed while lifting generation and context limits."""
    parent = build_c5_plan()
    coordinates: list[dict[str, Any]] = []
    for source in parent["coordinates"]:
        coordinate = copy.deepcopy(source)
        previous_id = coordinate["coordinate_id"]
        coordinate["coordinate_id"] = previous_id.replace("C5-", "C7-", 1)
        coordinate["suite"] = "calibration_c7"
        coordinate["metadata"]["parent_coordinate_id"] = previous_id
        coordinate["request"]["max_tokens"] = 4096
        coordinate["request_sha256"] = hashlib.sha256(
            canonical_bytes(coordinate["request"])
        ).hexdigest()
        coordinates.append(coordinate)
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "revision": "C7-same-prompts-max-tokens-4096",
        "purpose": (
            "Test whether C6's remaining visible-control truncation came from the request "
            "generation cap. C5 prompts, seeds, bank exposures, and rubric are retained; "
            "request max_tokens increases to 4096 and server context to 8192. Diagnostic, "
            "not scored Test A/B/C."
        ),
        "host_model": parent["host_model"],
        "model_gguf_sha256": parent["model_gguf_sha256"],
        "llama_cpp_commit": parent["llama_cpp_commit"],
        "server_context_size": 8192,
        "request_max_tokens": 4096,
        "request_matrix_sha256": hashlib.sha256(
            canonical_bytes([row["request_sha256"] for row in coordinates])
        ).hexdigest(),
        "coordinates": coordinates,
    }
