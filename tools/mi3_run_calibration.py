#!/usr/bin/env python3
"""Run the frozen 18-call MI3 development-only generation calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.runner import (
    GenerationBudget,
    MI1CoordinateRunner,
    ResolvedBank,
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def safe(value: str) -> str:
    return "".join(c if c.isalnum() or c in "_.-" else "_" for c in value)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--bank-build", type=Path, required=True)
    ap.add_argument("--selector", type=Path, required=True)
    ap.add_argument("--journal", type=Path, required=True)
    ap.add_argument("--bank-dir-remote", type=str, required=True)
    ap.add_argument("--base-url", default="http://127.0.0.1:18473")
    ap.add_argument("--output-root", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    protocol: dict[str, Any] = json.loads(args.protocol.read_text(encoding="utf-8"))
    build = json.loads(args.bank_build.read_text(encoding="utf-8"))
    sites = json.loads(args.selector.read_text(encoding="utf-8"))["selected_query_sites"]
    selector_sha = sha(args.selector)
    sampler = protocol["generation"]["sampler"]
    visible = protocol["calibration"]["visible_prompt_wrapper"]
    neighborhoods = protocol["neighborhoods"]
    variants = build["variants"]
    condition_bank_ids = {
        "A": "A_resilience",
        "B": "B_simplicity",
        "A_resilience": "A_resilience",
        "B_simplicity": "B_simplicity",
        "irrelevant": "irrelevant_visual_composition",
    }

    def resolve(source: str, source_sha: str, config: dict[str, Any]) -> ResolvedBank:
        bank_id = next(
            key
            for key, row in neighborhoods.items()
            if row["descriptor_text"] == source
            and hashlib.sha256(source.encode("utf-8")).hexdigest() == source_sha
        )
        gain = float(config["bank_logit_bias"])
        variant_id = f"{bank_id}__bias-{str(gain).replace('.', 'p')}"
        row = variants[variant_id]
        path = args.bank_dir_remote.rstrip("/") + f"/{variant_id}.mi1"
        return ResolvedBank(
            path=Path(path),
            native_sha256=row["sha256"],
            bank_fingerprint=row["native_fingerprint"],
            selector_sha256=selector_sha,
            selector={"query_sites": sites, "bank_logit_bias": gain},
        )

    requests: list[dict[str, Any]] = []
    for prompt in protocol["calibration"]["prompts"]:
        latent_started = False
        for condition in protocol["calibration"]["conditions"]:
            gain: float | None = None
            bank_id: str | None = None
            if condition.startswith("visible_"):
                bank_id = condition_bank_ids[condition.removeprefix("visible_")]
                content = (
                    visible["prefix"]
                    + neighborhoods[bank_id]["descriptor_text"]
                    + visible["suffix"]
                    + prompt["user"]
                )
                action = "clear"
            elif condition.startswith("latent_"):
                tail = condition.removeprefix("latent_")
                bank_short, gain_text = tail.rsplit("_bias_", 1)
                bank_id = condition_bank_ids[bank_short]
                gain = float(gain_text.replace("p", "."))
                content = prompt["user"]
                action = "replace" if latent_started else "attach"
                latent_started = True
            else:
                content = prompt["user"]
                action = "clear"
            request = {
                "model": protocol["host"]["model"],
                "messages": [
                    {"role": "system", "content": protocol["generation"]["system"]},
                    {"role": "user", "content": content},
                ],
                "stream": True,
                "cache_prompt": False,
                "seed": protocol["calibration"]["seed"],
                "max_tokens": sampler["max_tokens"],
                "chat_template_kwargs": sampler["chat_template_kwargs"],
                **{key: sampler[key] for key in ("temperature", "top_k", "top_p", "min_p")},
            }
            bank_source = (
                None
                if bank_id is None or condition.startswith("visible_")
                else neighborhoods[bank_id]["descriptor_text"]
            )
            coordinate = {
                "coordinate_id": safe(f"MI3-CAL-{prompt['id']}-{condition}-{request['seed']}"),
                "request": request,
                "bank_action": action,
                "bank_source": bank_source,
                "bank_source_sha256": None
                if bank_source is None
                else hashlib.sha256(bank_source.encode("utf-8")).hexdigest(),
                "bank_config": {} if gain is None else {"bank_logit_bias": gain},
                "metadata": {
                    "server_role": "mi1_server",
                    "package_id": protocol["protocol_id"],
                    "protocol_sha256": sha(args.protocol),
                    "phase": "calibration",
                    "prompt_id": prompt["id"],
                    "condition": condition,
                    "bank_identity": bank_id,
                    "gain": gain,
                    "seed": request["seed"],
                    "reasoning": "ON",
                    "prompt_cache": False,
                    "selector_sha256": selector_sha,
                },
            }
            requests.append(coordinate)

    expected_calls = int(protocol["calibration"]["call_count"])
    if len(requests) != expected_calls:
        raise ValueError(
            f"frozen calibration expects {expected_calls} calls, built {len(requests)}"
        )
    # Ensure latent prompt/request bytes are identical across bank identities.
    for prompt in protocol["calibration"]["prompts"]:
        latent = [
            row["request"]
            for row in requests
            if row["metadata"]["prompt_id"] == prompt["id"]
            and row["metadata"]["condition"].startswith("latent_")
        ]
        if len({canonical(row) for row in latent}) != 1:
            raise ValueError(f"latent request bytes differ across banks for {prompt['id']}")
        secret_texts = [row["descriptor_text"] for row in neighborhoods.values()]
        if any(secret in canonical(latent[0]).decode("utf-8") for secret in secret_texts):
            raise ValueError(f"bank descriptor text leaked into latent request for {prompt['id']}")
    atomic_json_write(
        args.output_root / "coordinates.json",
        {
            "protocol_sha256": sha(args.protocol),
            "selector_sha256": selector_sha,
            "coordinates": requests,
        },
    )
    if args.dry_run:
        print(f"dry-run: validated {len(requests)} calibration coordinates")
        return 0

    journal = EvidenceJournal(args.journal, hard_call_limit=100)
    budget = GenerationBudget(
        args.journal / "budget.json",
        prior_calibration_calls=0,
        calibration_limit=30,
        hard_limit=100,
    )
    runner = MI1CoordinateRunner(
        base_url=args.base_url,
        journal=journal,
        budget=budget,
        bank_resolver=resolve,
    )
    existing = json.loads((args.journal / "index.json").read_text(encoding="utf-8"))
    existing_rows = {row["attempt_id"]: row["status"] for row in existing["attempts"]}
    for index, coordinate in enumerate(requests, start=1):
        attempt_id = coordinate["coordinate_id"]
        if attempt_id in existing_rows:
            if existing_rows[attempt_id] == "COMPLETE":
                continue
            raise RuntimeError(
                f"calibration attempt {attempt_id} already has status "
                f"{existing_rows[attempt_id]}; refusing to retry"
            )
        print(f"[{index}/{len(requests)}] {attempt_id}", flush=True)
        runner.execute(coordinate, phase="calibration")
        atomic_json_write(
            args.output_root / "progress.json",
            {
                "completed": index,
                "total": len(requests),
                "last_coordinate": coordinate["coordinate_id"],
                "journal_index_sha256": sha(journal._index_path),
            },
        )

    # Only the latent A/B outputs used to select global gain are sent to the
    # blind scorer. The opaque ID map is written separately and withheld.
    packet_rows: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    index = json.loads((args.journal / "index.json").read_text(encoding="utf-8"))
    by_attempt = {row["attempt_id"]: row for row in index["attempts"]}
    rng = random.Random(2026101409)
    raw_rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for coordinate in requests:
        condition = coordinate["metadata"]["condition"]
        if not condition.startswith("latent_A_bias_") and not condition.startswith(
            "latent_B_bias_"
        ):
            continue
        attempt = coordinate["coordinate_id"]
        outcome_row = by_attempt[attempt]
        outcome = json.loads(
            (args.journal / "attempts" / outcome_row["outcome_file"]).read_text(encoding="utf-8")
        )
        response = outcome["payload"]
        choice = response["choices"][0]
        message = choice["message"]
        raw_rows.append(
            (
                coordinate,
                {
                    "task": next(
                        row["user"]
                        for row in protocol["calibration"]["prompts"]
                        if row["id"] == coordinate["metadata"]["prompt_id"]
                    ),
                    "reasoning": message.get("reasoning_content", message.get("reasoning", "")),
                    "final": message.get("content", ""),
                    "finish_reason": choice.get("finish_reason"),
                },
            )
        )
    order = list(range(len(raw_rows)))
    rng.shuffle(order)
    for opaque_index, raw_index in enumerate(order, start=1):
        coordinate, payload = raw_rows[raw_index]
        opaque_id = f"blind-{opaque_index:02d}"
        packet_rows.append({"opaque_id": opaque_id, **payload})
        key_rows.append(
            {
                "opaque_id": opaque_id,
                "attempt_id": coordinate["coordinate_id"],
                **coordinate["metadata"],
            }
        )
    atomic_json_write(
        args.output_root / "blind-calibration-packet.json",
        {
            "purpose": (
                "Blind A/B direction scoring to select one global gain; contains only "
                "calibration latent outputs and no condition labels."
            ),
            "rubric": protocol["scoring"]["blind_semantic_rubric"],
            "outputs": packet_rows,
        },
    )
    atomic_json_write(
        args.output_root / "blind-calibration-key.json",
        {
            "sealed_until_scores_final": True,
            "randomization_seed": 2026101409,
            "mapping": key_rows,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
