import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .chat import ChatSession
from .demo import DemoError, run_phase_one_gate
from .experiments.cli import add_parser as add_experiment_parser
from .experiments.cli import dispatch as dispatch_experiment
from .experiments.cli import normalize_args as normalize_experiment_args
from .experiments.inspection import inspect_store, inspect_turn
from .hosts import DeepInfraGemmaHost, FakeHost, GemmaHost
from .identity import IdentityService
from .qualification import qualify
from .state import SQLiteStore
from .state.contracts import StoragePermissions
from .state.policy import PolicyService
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
    demo = sub.add_parser("demo")
    dsub = demo.add_subparsers(dest="demo_action", required=True)
    phase_one = dsub.add_parser("phase-one")
    phase_one.add_argument("--gate", choices=("p1.1", "p1.2", "p1.3"), required=True)
    phase_one.add_argument("--host", default="fake")
    phase_one.add_argument("--live-budget")
    phase_one.add_argument("--workspace", type=Path, required=True)
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
    create.add_argument("--development-enabled", action="store_true")
    create.add_argument("--host")
    isub.add_parser("list")
    inspect = isub.add_parser("inspect")
    inspect.add_argument("id")
    inspect.add_argument("--json", action="store_true")
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
    inspect_cmd = sub.add_parser("inspect")
    inspect_sub = inspect_cmd.add_subparsers(dest="inspect_action", required=True)
    inspect_turn_cmd = inspect_sub.add_parser("turn")
    inspect_turn_cmd.add_argument("operation_id")
    chat = sub.add_parser("chat")
    chat.add_argument("text", nargs="?")
    chat.add_argument("--mode", choices=("develop", "observe", "evaluate"), default="develop")
    chat.add_argument("--memory", choices=("graph", "episodic", "off"), default="graph")
    chat.add_argument("--host", default="fake")
    chat.add_argument("--json", action="store_true")
    identity = sub.add_parser("identity")
    idsub = identity.add_subparsers(dest="identity_action", required=True)
    adopt = idsub.add_parser("adopt")
    adopt.add_argument("--host", default="fake")
    adopt.add_argument("--name")
    idshow = idsub.add_parser("show")
    idshow.add_argument("--json", action="store_true")
    alias = idsub.add_parser("alias")
    alias_sub = alias.add_subparsers(dest="alias_action", required=True)
    alias_add = alias_sub.add_parser("add")
    alias_add.add_argument("alias")
    permission = sub.add_parser("permission")
    psub = permission.add_subparsers(dest="permission_action", required=True)
    pshow = psub.add_parser("show")
    pshow.add_argument("--json", action="store_true")
    pgrant = psub.add_parser("grant")
    pgrant.add_argument("--interpret", action="store_true")
    pgrant.add_argument("--recall", action="store_true")
    pgrant.add_argument("--provider-reuse", action="store_true")
    pgrant.add_argument("--host")
    prevoke = psub.add_parser("revoke")
    prevoke.add_argument("--interpret", action="store_true")
    prevoke.add_argument("--recall", action="store_true")
    prevoke.add_argument("--provider-reuse", action="store_true")
    add_experiment_parser(sub)
    args = normalize_experiment_args(parser.parse_args(argv))
    if args.command == "demo":
        if args.demo_action not in {"phase-one", "phase_one"}:
            raise SystemExit(f"unknown demo action: {args.demo_action}")
        try:
            demo_report = run_phase_one_gate(
                gate=args.gate,
                host=args.host,
                live_budget=args.live_budget,
                workspace=args.workspace,
            )
        except DemoError as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps(demo_report, indent=2, sort_keys=True))
        return 0
    if args.command == "experiment":
        return dispatch_experiment(args)
    if args.command in {
        "instance",
        "episode",
        "operation",
        "checkpoint",
        "backup",
        "store",
        "chat",
        "identity",
        "permission",
        "inspect",
    }:
        if args.store is None:
            raise SystemExit("--store PATH is required for state commands")
        if args.command == "instance" and args.instance_action == "create":
            if args.development_enabled and not args.host:
                raise SystemExit("--host is required with --development-enabled")
            if args.store.exists() and args.store.is_dir():
                path = args.store / f"{args.id or 'instance'}.sqlite3"
            elif args.store.suffix.lower() in {".sqlite3", ".sqlite", ".db"}:
                args.store.parent.mkdir(parents=True, exist_ok=True)
                path = args.store
            else:
                args.store.mkdir(parents=True, exist_ok=True)
                path = args.store / f"{args.id or 'instance'}.sqlite3"
            with SQLiteStore(path) as store:
                selected_host = _host(args.host) if args.host else None
                instance_id = store.create_root(
                    instance_id=args.id,
                    scope_id=args.scope,
                    permissions=StoragePermissions(
                        store=True,
                        export=args.export,
                        interpret=args.development_enabled,
                        recall=args.development_enabled,
                        provider_reuse=args.development_enabled,
                    ),
                    host_binding=(
                        selected_host.fingerprint().to_dict() if selected_host is not None else None
                    ),
                )
            print(instance_id)
            return 0
        if args.command == "permission":
            with SQLiteStore(args.store) as store:
                current = store.current()
                service = PolicyService(store, str(current["active_instance_id"]))
                if args.permission_action == "show":
                    print(json.dumps(service.show(), indent=2, sort_keys=True))
                    return 0
                permissions = [
                    name
                    for name, selected in (
                        ("interpret", args.interpret),
                        ("recall", args.recall),
                        ("provider_reuse", args.provider_reuse),
                    )
                    if selected
                ]
                if not permissions:
                    raise SystemExit("select at least one Phase One permission")
                if args.permission_action == "revoke":
                    revision = service.revoke(permissions)
                else:
                    selected_host = _host(args.host) if args.host else None
                    revision = service.grant(
                        permissions,
                        host_fingerprint=(
                            selected_host.fingerprint().to_dict()
                            if selected_host is not None
                            else None
                        ),
                    )
                print(json.dumps({"revision": revision, **service.show()}, indent=2, sort_keys=True))
                return 0
        if args.command == "chat":
            text = args.text if args.text is not None else sys.stdin.readline().rstrip("\n")
            with SQLiteStore(args.store) as store:
                current = store.current()
                session = ChatSession(
                    store,
                    str(current["active_instance_id"]),
                    _host(args.host),
                    mode=args.mode,
                    memory=args.memory,
                )
                result = session.turn(text)
            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(result.output_text)
            return 0
        if args.command == "identity":
            with SQLiteStore(args.store) as store:
                current = store.current()
                identity_service = IdentityService(store, str(current["active_instance_id"]))
                if args.identity_action == "adopt":
                    adopted_view = (
                        identity_service.adopt(args.name, source={"actor": "operator"})
                        if args.name is not None
                        else identity_service.adopt_from_host(_host(args.host))
                    )
                    print(json.dumps(adopted_view.to_dict(), indent=2))
                elif args.identity_action == "show":
                    shown_view = identity_service.current()
                    payload = shown_view.to_dict() if shown_view is not None else None
                    print(json.dumps(payload, indent=2))
                elif args.identity_action == "alias" and args.alias_action == "add":
                    print(identity_service.add_alias(args.alias, source={"actor": "operator"}))
                return 0
        if args.command == "inspect":
            if args.inspect_action == "turn":
                print(json.dumps(inspect_turn(args.store, args.operation_id), indent=2))
                return 0
            raise SystemExit(f"unknown inspection action: {args.inspect_action}")
        if args.command == "instance" and args.instance_action == "list":
            paths = sorted(args.store.glob("*.sqlite3")) if args.store.is_dir() else [args.store]
            print(json.dumps([str(p) for p in paths], indent=2))
            return 0
        if args.command == "instance" and args.instance_action == "inspect":
            print(json.dumps(inspect_store(args.store), indent=2, default=str))
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
                        "SELECT * FROM operations WHERE instance_id=? ORDER BY created_at",
                        (args.id,),
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
                continuity = ContinuityService(
                    store, lookup_id, _host(getattr(args, "host", "fake"))
                )
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
                            continuity.prepare_episode(
                                req, operation_id=args.operation_id
                            ).__dict__,
                            indent=2,
                        )
                    )
                    return 0
                if args.episode_action == "generate":
                    print(
                        json.dumps(continuity.generate_operation(args.operation).__dict__, indent=2)
                    )
                    return 0
                if args.episode_action == "accept":
                    print(json.dumps(continuity.accept_episode(args.operation).__dict__, indent=2))
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
