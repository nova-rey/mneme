#!/usr/bin/env python3
"""Plan, verify, or execute the D100-derived ten-thread trial.

The live execution is intentionally injected through a runtime factory.  That
keeps this schedule/publication boundary independent from the CompactStore
controller integration and prevents accidental fallback to the historical
SQLite P3 runner.  A factory must return an object implementing
``TrialRuntime.run_trial(config)``.
"""

from __future__ import annotations

import argparse
import importlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

from mneme.experiments.d100_trial import (
    REPORT_NAME,
    TRIAL_VERSION,
    TrialConfig,
    ancestor_equivalence,
    copy_ancestor,
    render_report,
    validate_schedule,
    validate_trial_evidence,
)


def _load_factory(spec: str) -> Callable[[TrialConfig], Mapping[str, Any]]:
    module_name, separator, attribute = spec.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("runtime factory must use module:callable syntax")
    factory = getattr(importlib.import_module(module_name), attribute, None)
    if not callable(factory):
        raise TypeError(f"runtime factory is not callable: {spec}")
    return cast(Callable[[TrialConfig], Mapping[str, Any]], factory)


def _plan(config: TrialConfig) -> dict[str, Any]:
    config.validate()
    validate_schedule(config.schedule)
    return {
        "trial_version": TRIAL_VERSION,
        "status": "FROZEN_PLAN_ONLY",
        "run_id": config.run_id,
        "d100_normative_status": "convenience_developed_ancestor",
        "ancestor": str(config.ancestor_path),
        "thread_schedule": [item.__dict__ for item in config.schedule],
        "probe_bank": list(config.probes),
        "gemma_seeds": list(config.gemma_seeds),
        "field_seeds": list(config.field_seeds),
        "introspection_version": config.introspection_version,
        "filing_level": config.filing_level,
        "compact_schema_version": config.compact_schema_version,
        "historical_p3_mutation": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ancestor", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--ancestor-copy", type=Path)
    parser.add_argument("--emit-plan", type=Path)
    parser.add_argument("--verify-ancestor", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--runtime-factory", help="module:callable; required with --execute")
    args = parser.parse_args(argv)

    copy_receipt: dict[str, Any] | None = None
    ancestor_path = args.ancestor
    if args.ancestor_copy is not None:
        copy_receipt = copy_ancestor(args.ancestor, args.ancestor_copy)
        ancestor_path = args.ancestor_copy
    config = TrialConfig(ancestor_path=ancestor_path, output_root=args.output_root)
    plan = _plan(config)
    if args.emit_plan:
        args.emit_plan.parent.mkdir(parents=True, exist_ok=True)
        args.emit_plan.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    if args.verify_ancestor:
        source = ancestor_path if copy_receipt is None else args.ancestor
        target = ancestor_path if copy_receipt is None else args.ancestor_copy
        if target is None:
            target = source
        plan["ancestor_equivalence"] = ancestor_equivalence(source, target)
        if copy_receipt is not None:
            plan["ancestor_copy"] = copy_receipt
    if not args.execute:
        print(json.dumps(plan, indent=2))
        return 0
    if not args.runtime_factory:
        raise SystemExit("--execute requires --runtime-factory module:callable")
    if not args.verify_ancestor or "ancestor_equivalence" not in plan:
        raise SystemExit("--execute requires --verify-ancestor")
    if not plan["ancestor_equivalence"].get("pass"):
        raise SystemExit("ancestor equivalence failed; live execution is blocked")
    payload = dict(_load_factory(args.runtime_factory)(config))
    payload.setdefault("trial_version", TRIAL_VERSION)
    payload.setdefault("run_id", config.run_id)
    payload.setdefault("d100_normative_status", "convenience_developed_ancestor")
    payload.setdefault("ancestor_equivalence", plan["ancestor_equivalence"])
    problems = validate_trial_evidence(payload)
    payload["evidence_validation"] = {"problems": problems, "pass": not problems}
    output_root = config.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / f"{REPORT_NAME}.json"
    md_path = output_root / f"{REPORT_NAME}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_report(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "COMPLETE" if not problems else "INVALID_EVIDENCE",
                "json": str(json_path),
                "markdown": str(md_path),
                "problems": problems,
            },
            indent=2,
        )
    )
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
