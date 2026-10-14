"""Freeze the MI4 Qwen3 shared query-site set from calibration-only captures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from experiments.mi1.native.bank import MemoryBank
from experiments.mi1.native.query_capture import QueryCapture, read_query_capture
from experiments.mi1.native.selector import attention_mass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _grouped_pairwise_margin(
    query: np.ndarray, target: np.ndarray, refs: list[np.ndarray]
) -> np.ndarray:
    """Return mean target-minus-each-reference max alignment by KV group."""
    if query.ndim != 2 or target.ndim != 3 or not refs:
        raise ValueError("expected Q [heads,d], K [slots,groups,d], and references")
    groups = target.shape[1]
    if query.shape[0] % groups or query.shape[1] != target.shape[2]:
        raise ValueError("Qwen3 query and KV shapes do not align")
    if any(ref.ndim != 3 or ref.shape[1:] != target.shape[1:] for ref in refs):
        raise ValueError("reference key layouts do not match target")
    heads_per_group = query.shape[0] // groups
    scale = np.float32(1.0 / np.sqrt(query.shape[-1]))
    scores = np.empty(groups, dtype=np.float32)
    for group in range(groups):
        margins: list[float] = []
        for head in range(group * heads_per_group, (group + 1) * heads_per_group):
            q = query[head]
            target_max = float(np.max(target[:, group, :] @ q * scale))
            for reference in refs:
                reference_max = float(np.max(reference[:, group, :] @ q * scale))
                margins.append(target_max - reference_max)
        scores[group] = np.mean(np.asarray(margins, dtype=np.float32), dtype=np.float32)
    return scores


def select_sites(
    captures: dict[str, dict[str, QueryCapture]],
    banks: dict[str, MemoryBank],
    *,
    top_layers: int = 4,
) -> dict[str, Any]:
    """Aggregate D1/D2 × A/B/irrelevant pairwise evidence and freeze sites."""
    names = ("A_resilience", "B_simplicity", "irrelevant_visual_composition")
    if set(banks) != set(names) or not captures:
        raise ValueError("expected the three frozen MI4 banks and calibration captures")
    if set(captures) != {"D1_after_school_program", "D2_community_repair_group"}:
        raise ValueError("site selection may use only the two frozen calibration prompts")
    first = next(iter(next(iter(captures.values())).values()))
    layers = tuple(sorted(first.layers))
    if layers != tuple(range(36)):
        raise ValueError("Qwen3-4B calibration requires all 36 query layers")
    reference_scores: list[np.ndarray] = []
    bank_masses: list[np.ndarray] = []
    capture_facts: list[dict[str, Any]] = []
    for prompt_id in sorted(captures):
        if set(captures[prompt_id]) != set(names):
            raise ValueError(f"{prompt_id}: missing one of the three bank captures")
        for target_name in names:
            capture = captures[prompt_id][target_name]
            target = banks[target_name]
            refs = [banks[name] for name in names if name != target_name]
            if set(capture.layers) != set(layers):
                raise ValueError("query capture layer set differs across calibration cells")
            for bank in (target, *refs):
                if bank.manifest.layer_ids != layers:
                    raise ValueError("bank/query layer identities do not align")
            per_layer_margin: list[np.ndarray] = []
            per_layer_mass: list[np.ndarray] = []
            for layer in layers:
                q = capture.layers[layer].query[-1]
                target_keys = target.keys[layer]
                ref_keys = [bank.keys[layer] for bank in refs]
                per_layer_margin.append(_grouped_pairwise_margin(q, target_keys, ref_keys))
                probabilities = capture.layers[layer].attention[-1].T
                prompt_mass, bank_mass = attention_mass(
                    probabilities,
                    prompt_slots=len(capture.token_ids),
                    bank_slots=target.manifest.slot_count,
                )
                groups = target_keys.shape[1]
                heads_per_group = q.shape[0] // groups
                per_layer_mass.append(
                    bank_mass.reshape(groups, heads_per_group).mean(axis=1, dtype=np.float32)
                )
            reference_scores.append(np.stack(per_layer_margin))
            bank_masses.append(np.stack(per_layer_mass))
            capture_facts.append(
                {
                    "prompt_id": prompt_id,
                    "target_bank": target_name,
                    "token_count": len(capture.token_ids),
                    "token_ids_sha256": hashlib.sha256(
                        np.asarray(capture.token_ids, dtype="<i4").tobytes()
                    ).hexdigest(),
                }
            )
    alignment = np.mean(np.stack(reference_scores), axis=0, dtype=np.float32)
    mass = np.mean(np.stack(bank_masses), axis=0, dtype=np.float32)
    if alignment.shape != (36, 8) or mass.shape != (36, 8):
        raise ValueError("unexpected Qwen3 selector matrix dimensions")
    selected_groups: list[tuple[int, int, float, float]] = []
    for layer in range(36):
        order = np.lexsort((np.arange(8), -mass[layer], -alignment[layer]))
        group = int(order[0])
        selected_groups.append(
            (layer, group, float(alignment[layer, group]), float(mass[layer, group]))
        )
    top = sorted(selected_groups, key=lambda item: (-item[2], -item[3], item[0]))[:top_layers]
    groups = [(layer, group) for layer, group, _, _ in top]
    sites = [
        [layer, group * 4 + offset]
        for layer, group in groups
        for offset in range(4)
    ]
    return {
        "algorithm": (
            "For each D1/D2 × target-bank capture, mean target-minus-each-other-bank "
            "maximum pre-RoPE QK alignment by KV group; average six matrices; per layer "
            "choose top group (bank attention mass tie-break), then global top four layers; "
            "map each KV group to four contiguous Q heads."
        ),
        "capture_facts": capture_facts,
        "layer_count": 36,
        "query_heads": 32,
        "kv_groups": 8,
        "heads_per_kv_group": 4,
        "alignment": alignment.astype(float).tolist(),
        "bank_attention_mass": mass.astype(float).tolist(),
        "per_layer_selected_group": [
            {
                "layer": layer,
                "kv_group": group,
                "alignment": score,
                "bank_attention_mass": bank_mass_value,
            }
            for layer, group, score, bank_mass_value in selected_groups
        ],
        "selected_layers": [
            {
                "layer": layer,
                "kv_group": group,
                "alignment": score,
                "bank_attention_mass": bank_mass_value,
            }
            for layer, group, score, bank_mass_value in top
        ],
        "selected_query_sites": sites,
    }


def _load_banks(paths: dict[str, Path]) -> dict[str, MemoryBank]:
    return {name: MemoryBank.load(path) for name, path in paths.items()}


def _load_captures(paths: dict[str, dict[str, Path]]) -> dict[str, dict[str, QueryCapture]]:
    return {
        prompt: {name: read_query_capture(path) for name, path in cells.items()}
        for prompt, cells in paths.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--banks", type=Path, required=True, help="JSON name→NPZ path map")
    parser.add_argument("--captures", type=Path, required=True, help="JSON prompt→bank→capture map")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bank_paths = {name: Path(path) for name, path in json.loads(args.banks.read_text()).items()}
    capture_paths = {
        prompt: {name: Path(path) for name, path in cells.items()}
        for prompt, cells in json.loads(args.captures.read_text()).items()
    }
    result = select_sites(_load_captures(capture_paths), _load_banks(bank_paths))
    result["input_sha256"] = {
        "banks": {name: sha256(path) for name, path in bank_paths.items()},
        "captures": {
            prompt: {name: sha256(path) for name, path in cells.items()}
            for prompt, cells in capture_paths.items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temp.replace(args.output)


if __name__ == "__main__":
    main()
