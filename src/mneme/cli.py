import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .hosts import FakeHost, GemmaHost
from .qualification import qualify


def _host(name: str) -> Any:
    if name == "fake":
        return FakeHost()
    if name == "gemma":
        return GemmaHost(
            model_id=os.getenv("MNEME_MODEL_ID", "google/gemma-4-E4B"),
            provider=os.getenv("MNEME_HF_PROVIDER"),
            revision=os.getenv("MNEME_MODEL_REVISION"),
        )
    raise SystemExit(f"unknown host: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mneme")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    host = sub.add_parser("host")
    hsub = host.add_subparsers(dest="action", required=True)
    hsub.add_parser("list")
    for action in ("inspect", "qualify"):
        p = hsub.add_parser(action)
        p.add_argument("host")
        if action == "qualify":
            p.add_argument("--json", type=Path)
            p.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.command == "doctor":
        print(
            json.dumps(
                {
                    "version": __version__,
                    "python": sys.version.split()[0],
                    "gemma_configured": bool(os.getenv("MNEME_HF_TOKEN")),
                },
                indent=2,
            )
        )
        return 0
    if args.action == "list":
        print("fake\ngemma")
        return 0
    selected = _host(args.host)
    if args.action == "inspect":
        print(json.dumps(selected.fingerprint().to_dict(), indent=2))
        return 0
    report = qualify(selected)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report.text())
    print(report.text(), end="")
    return 0 if report.summary["overall"] == "pass" else 1
