import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .hosts import DeepInfraGemmaHost, FakeHost, GemmaHost
from .qualification import qualify
from .state import SQLiteStore
from .state.contracts import StoragePermissions
from .state.reader import CheckpointReader
from .state.service import ContinuityService
from .state.snapshots import backup_instance, create_checkpoint, fork_from_checkpoint


def _host(name: str) -> Any:
    if name == "fake":
        return FakeHost()
    if name == "gemma":
        return GemmaHost(
            model_id=os.getenv("MNEME_MODEL_ID", "google/gemma-4-E4B"),
            provider=os.getenv("MNEME_HF_PROVIDER"),
            revision=os.getenv("MNEME_MODEL_REVISION"),
        )
    if name == "gemma-deepinfra":
        return DeepInfraGemmaHost(
            model_id=os.getenv("MNEME_DEEPINFRA_MODEL_ID", "google/gemma-4-E4B-it"),
            token=os.getenv("DEEPINFRA_TOKEN"),
        )
    raise SystemExit(f"unknown host: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mneme")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--store", type=Path)
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
    instance = sub.add_parser("instance")
    isub = instance.add_subparsers(dest="instance_action", required=True)
    create = isub.add_parser("create")
    create.add_argument("--id")
    create.add_argument("--scope", default="local")
    create.add_argument("--export", action="store_true")
    isub.add_parser("list")
    inspect = isub.add_parser("inspect")
    inspect.add_argument("id")
    fork = isub.add_parser("fork")
    fork.add_argument("--checkpoint", required=True)
    fork.add_argument("--output", required=True)
    fork.add_argument("--id")
    episode = sub.add_parser("episode")
    esub = episode.add_subparsers(dest="episode_action", required=True)
    prep = esub.add_parser("prepare")
    prep.add_argument("id")
    prep.add_argument("--request", required=True, type=Path)
    prep.add_argument("--host", default="fake")
    prep.add_argument("--operation-id")
    gen = esub.add_parser("generate")
    gen.add_argument("operation")
    accept = esub.add_parser("accept")
    accept.add_argument("operation")
    elist = esub.add_parser("list")
    elist.add_argument("id")
    operation = sub.add_parser("operation")
    osub = operation.add_subparsers(dest="operation_action", required=True)
    oi = osub.add_parser("inspect")
    oi.add_argument("id")
    ol = osub.add_parser("list")
    ol.add_argument("id")
    checkpoint = sub.add_parser("checkpoint")
    csub = checkpoint.add_subparsers(dest="checkpoint_action", required=True)
    cc = csub.add_parser("create")
    cc.add_argument("id")
    cc.add_argument("--output", required=True)
    cc.add_argument("--id")
    csub.add_parser("list")
    ci = csub.add_parser("inspect")
    ci.add_argument("id")
    backup = sub.add_parser("backup")
    backup.add_argument("id")
    backup.add_argument("--output", required=True)
    store_cmd = sub.add_parser("store")
    ssub = store_cmd.add_subparsers(dest="store_action", required=True)
    recover = ssub.add_parser("recover")
    recover.add_argument("id")
    args = parser.parse_args(argv)
    if args.command in {"instance", "episode", "operation", "checkpoint", "backup", "store"}:
        if args.store is None:
            raise SystemExit("--store PATH is required for state commands")
        if args.command == "instance" and args.instance_action == "create":
            args.store.mkdir(parents=True, exist_ok=True)
            path = (
                args.store / f"{args.id or 'instance'}.sqlite3"
                if args.store.is_dir()
                else args.store
            )
            with SQLiteStore(path) as store:
                instance_id = store.create_root(
                    instance_id=args.id,
                    scope_id=args.scope,
                    permissions=StoragePermissions(store=True, export=args.export),
                )
            print(instance_id)
            return 0
        if args.command == "instance" and args.instance_action == "list":
            paths = sorted(args.store.glob("*.sqlite3")) if args.store.is_dir() else [args.store]
            print(json.dumps([str(p) for p in paths], indent=2))
            return 0
        if args.command == "instance" and args.instance_action == "inspect":
            with SQLiteStore(args.store, read_only=True) as store:
                print(json.dumps(dict(store.current()), indent=2, default=str))
            return 0
        if args.command == "instance" and args.instance_action == "fork":
            print(fork_from_checkpoint(args.checkpoint, args.output, args.id))
            return 0
        if args.command == "checkpoint" and args.checkpoint_action == "create":
            with SQLiteStore(args.store) as store:
                print(create_checkpoint(store, args.output, args.id))
            return 0
        if args.command == "checkpoint" and args.checkpoint_action == "list":
            paths = sorted(args.store.glob("*.sqlite3")) if args.store.is_dir() else [args.store]
            output = []
            for path in paths:
                try:
                    with CheckpointReader(path) as reader:
                        output.append(reader.manifest())
                except (ValueError, sqlite3.Error):
                    continue
            print(json.dumps(output, indent=2))
            return 0
        if args.command == "checkpoint" and args.checkpoint_action == "inspect":
            with CheckpointReader(args.id) as reader:
                print(json.dumps(reader.manifest(), indent=2))
            return 0
        if args.command == "backup":
            with SQLiteStore(args.store) as store:
                backup_instance(store, args.output)
            return 0
        if args.command == "operation":
            with SQLiteStore(args.store, read_only=True) as store:
                if args.operation_action == "inspect":
                    row = store.connection.execute(
                        "SELECT * FROM operations WHERE operation_id=?", (args.id,)
                    ).fetchone()
                    if row is None:
                        raise SystemExit("unknown operation")
                    print(json.dumps(dict(row), indent=2))
                else:
                    rows = store.connection.execute(
                        "SELECT * FROM operations WHERE instance_id=? ORDER BY created_at", (args.id,)
                    )
                    print(json.dumps([dict(row) for row in rows], indent=2))
            return 0
        if args.command == "store" and args.store_action == "recover":
            with SQLiteStore(args.store, read_only=False) as store:
                print(json.dumps({"instance_id": args.id, "problems": store.verify()}, indent=2))
            return 0
        if args.command == "episode":
            from .contracts import GenerationRequest

            with SQLiteStore(args.store) as store:
                lookup_id = getattr(args, "id", "")
                if args.episode_action in {"generate", "accept"}:
                    lookup = store.connection.execute(
                        "SELECT instance_id FROM operations WHERE operation_id=?",
                        (args.operation,),
                    ).fetchone()
                    lookup_id = str(lookup[0]) if lookup else ""
                row = store.connection.execute(
                    "SELECT instance_id FROM lineages WHERE instance_id=?", (lookup_id,)
                ).fetchone()
                if row is None:
                    raise SystemExit("unknown instance")
                service = ContinuityService(store, lookup_id, _host(getattr(args, "host", "fake")))
                if args.episode_action == "prepare":
                    data = json.loads(args.request.read_text())
                    req = GenerationRequest(
                        tuple(data["messages"]),
                        data.get("system"),
                        data.get("parameters", {}),
                        data.get("seed"),
                        data.get("response_format"),
                        {},
                    )
                    print(
                        json.dumps(
                            service.prepare_episode(req, operation_id=args.operation_id).__dict__,
                            indent=2,
                        )
                    )
                    return 0
                if args.episode_action == "generate":
                    print(json.dumps(service.generate_operation(args.operation).__dict__, indent=2))
                    return 0
                if args.episode_action == "accept":
                    print(json.dumps(service.accept_episode(args.operation).__dict__, indent=2))
                    return 0
                print(
                    json.dumps(
                        [
                            dict(r)
                            for r in store.connection.execute(
                                "SELECT * FROM episodes ORDER BY accepted_revision"
                            )
                        ],
                        indent=2,
                    )
                )
                return 0
    if args.command == "doctor":
        print(
            json.dumps(
                {
                    "version": __version__,
                    "python": sys.version.split()[0],
                    "gemma_configured": bool(os.getenv("MNEME_HF_TOKEN")),
                    "deepinfra_configured": bool(os.getenv("DEEPINFRA_TOKEN")),
                },
                indent=2,
            )
        )
        return 0
    if args.action == "list":
        print("fake\ngemma\ngemma-deepinfra")
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
