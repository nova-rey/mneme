#!/usr/bin/env python3
"""Model-free arithmetic checks for the Phase 3.5 control-vector bench.

This intentionally mirrors only the pinned llama.cpp adapter/mean operations.
It does not import MNEME, load a model, or write developmental state.
"""

from __future__ import annotations

import json
import math
import struct


def mean_normalize(rows: list[list[float]]) -> list[float]:
    n = len(rows)
    d = len(rows[0])
    vector = [sum(row[i] for row in rows) / n for i in range(d)]
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else [float("nan")] * d


def adapter_apply(
    data: list[float],
    embd: int,
    n_layers: int,
    start: int,
    end: int,
    gain: float = 1.0,
    disabled: bool = False,
) -> list[list[float]]:
    """Mirror llama_adapter_cvec::apply_to for synthetic F32 values."""

    output: list[list[float]] = []
    for layer in range(n_layers):
        active = not disabled and layer >= 1 and start <= layer <= end
        offset = embd * (layer - 1)
        if active:
            output.append([gain * value for value in data[offset : offset + embd]])
        else:
            output.append([0.0] * embd)
    return output


def main() -> int:
    checks: list[dict[str, object]] = []
    vector = mean_normalize([[3.0, 4.0], [3.0, 4.0]])
    checks.append(
        {
            "name": "mean_normalization_finite",
            "pass": all(math.isfinite(value) for value in vector)
            and abs(math.sqrt(sum(value * value for value in vector)) - 1) < 1e-6,
            "value": vector,
        }
    )
    zero = mean_normalize([[0.0, 0.0], [0.0, 0.0]])
    checks.append(
        {
            "name": "zero_norm_behavior",
            "pass": not all(math.isfinite(value) for value in zero),
            "value": ["nan" if math.isnan(value) else value for value in zero],
            "finding": (
                "Pinned mean.hpp divides by zero for an all-zero direction; "
                "the caller must reject or guard it."
            ),
        }
    )
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    applied = adapter_apply(data, 2, 5, 2, 3)
    checks.append(
        {
            "name": "layer_mapping_inclusive_and_layer0_noop",
            "pass": applied == [[0, 0], [0, 0], [3, 4], [5, 6], [0, 0]],
            "value": applied,
        }
    )
    scaled = adapter_apply(data, 2, 5, 2, 3, gain=0.5)
    checks.append(
        {
            "name": "gain_scaling",
            "pass": scaled[2] == [1.5, 2.0] and scaled[3] == [2.5, 3.0],
            "value": scaled,
        }
    )
    cleared = adapter_apply(data, 2, 5, 2, 3, disabled=True)
    checks.append(
        {
            "name": "disable_noop",
            "pass": all(all(value == 0 for value in row) for row in cleared),
            "value": cleared,
        }
    )
    checks.append(
        {
            "name": "dimension_contract",
            "pass": len(data) == 2 * (5 - 1),
            "value": {"data_floats": len(data), "expected": 2 * (5 - 1)},
        }
    )
    roundtrip = struct.unpack("<8f", struct.pack("<8f", *map(float, data)))
    checks.append(
        {
            "name": "vector_serialization_roundtrip",
            "pass": roundtrip == tuple(map(float, data)),
            "value": data,
        }
    )
    print(
        json.dumps(
            {
                "schema": "mneme.p35.model-free-checks.v1",
                "checks": checks,
                "all_pass": all(item["pass"] for item in checks),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
