"""Build the immutable runner coordinates for the frozen C11 site experiment."""

from __future__ import annotations

import copy
import hashlib
from typing import Any


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_execution_plan(
    frozen_plan: dict[str, Any],
    *,
    frozen_plan_sha256: str,
    site_selection: dict[str, Any],
    site_selection_sha256: str,
) -> dict[str, Any]:
    """Expand frozen C11 design rows into exact cache-disabled runner requests."""
    if frozen_plan.get("experiment") != "MNEME Phase 4 MI1 C11 query-alignment selector diagnostic":
        raise ValueError("not the frozen C11 query-site plan")
    if frozen_plan.get("status") != "FROZEN_BEFORE_SELECTOR_CAPTURE_AND_GENERATION":
        raise ValueError("C11 design must be frozen before query capture and generation")
    if len(frozen_plan.get("coordinates", [])) != 144:
        raise ValueError("C11 execution requires its frozen 144-coordinate matrix")
    aggregate = site_selection.get("selection", {}).get("aggregate")
    if not isinstance(aggregate, dict):
        raise ValueError("frozen C11 query-site result lacks polarity selections")
    selected_sites = {
        polarity: aggregate[polarity].get("selected_query_sites") for polarity in ("A", "B")
    }
    if any(not isinstance(rows, list) or len(rows) != 16 for rows in selected_sites.values()):
        raise ValueError("C11 selected bank site lists must contain 16 query heads")

    site_spec = frozen_plan["site_selection"]
    selector_sites = {
        "selected_A": selected_sites["A"],
        "selected_B": selected_sites["B"],
        "old_sparse": site_spec["old_selector_sites"],
        "random": site_spec["random_control_sites"],
    }
    config = frozen_plan["generation_config"]
    sampler = config["sampler"]
    prompts = frozen_plan["heldout_prompts"]
    system = frozen_plan["coordinates"][0]["messages"][0]["content"]
    coordinates: list[dict[str, Any]] = []
    for frozen in frozen_plan["coordinates"]:
        coordinate = copy.deepcopy(frozen)
        condition = coordinate["condition"]
        fixture = coordinate["fixture_id"]
        seed = coordinate["seed"]
        bank_key = coordinate.get("bank_key")
        is_bank = coordinate["bank_action"] == "attach"
        if is_bank:
            if bank_key not in ("A", "B"):
                raise ValueError(f"bank coordinate {condition} has no A/B bank key")
            source = prompts[fixture][f"bank_{bank_key}"]
            source_sha = digest_text(source)
            if condition in ("selected_A", "selected_B"):
                selector = condition
            elif condition.startswith("old_sparse_"):
                selector = "old_sparse"
            elif condition.startswith("random_"):
                selector = "random"
            else:
                raise ValueError(f"unrecognized C11 bank condition: {condition}")
            bank_config = {"selector": selector, "gain": {"logit_bias": 0.0}}
        else:
            source = None
            source_sha = None
            selector = "none"
            bank_config = {"selector": "none", "gain": None}
        messages = coordinate["messages"]
        if not messages or messages[0].get("content") != system:
            raise ValueError("C11 system framing differs across frozen coordinates")
        request = {
            "messages": messages,
            "seed": seed,
            "cache_prompt": False,
            "stream": True,
            "max_tokens": config["max_tokens"],
            "reasoning_format": config["reasoning_format"],
            "chat_template_kwargs": config["chat_template_kwargs"],
            **sampler,
        }
        coordinate.update(
            {
                "bank_source": source,
                "bank_source_sha256": source_sha,
                "bank_config": bank_config,
                "metadata": {
                    "condition": condition,
                    "fixture_id": fixture,
                    "seed": seed,
                    "server_role": "mi1_server",
                    "suite": "c11_query_site_diagnostic",
                    "selector": selector,
                },
                "request": request,
            }
        )
        if request["cache_prompt"] is not False or request["seed"] != seed:
            raise AssertionError("C11 request lost its deterministic frozen controls")
        coordinates.append(coordinate)

    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4-MI1 C11 query-site diagnostic execution",
        "status": "FROZEN_BEFORE_HELDOUT_GENERATION",
        "design_plan_sha256": frozen_plan_sha256,
        "site_selection_receipt_sha256": site_selection_sha256,
        "generation_config": config,
        "coordinate_count": len(coordinates),
        "coordinate_ids": [row["coordinate_id"] for row in coordinates],
        "coordinates": coordinates,
        "bank_selectors": {
            selector: {"query_sites": rows, "logit_bias": 0.0}
            for selector, rows in selector_sites.items()
        },
    }
