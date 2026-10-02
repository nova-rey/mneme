#!/usr/bin/env python3
"""Copy a historical P3 head into a CompactStore ancestor.

This command is deliberately separate from the live experiment runner.  It
opens the source SQLite store read-only, creates a new compact store, and
emits a small manifest proving the logical current-state comparison.  The
source database and all historical receipts remain untouched.

The compact schema is intentionally small, but semantic bindings are part of
the runtime identity contract.  They are copied into an additive table in the
new database (never into the source) so a descendant can resolve inherited
graph keys after restart.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from mneme.development.field import compute_saa_field
from mneme.development.learner import CreditWindow, EdgeState, LearnerState
from mneme.memory.graph import GraphConcept, GraphEdge
from mneme.state.compact import CompactStore, _digest, _source_graph, migrate_sqlite


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_snapshot(path: Path) -> dict[str, Any]:
    """Read the source head and all current logical rows without mutation."""

    uri = f"file:{path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        head = connection.execute(
            "SELECT active_instance_id,current_revision,current_manifest_id FROM current_state"
        ).fetchone()
        if head is None:
            raise ValueError("source has no current_state row")
        instance_id = str(head[0])
        manifest_id = str(head[2])
        nodes, edges, routes = _source_graph(connection, instance_id)
        learner: dict[tuple[str, str], dict[str, Any]] = {}
        for row in connection.execute(
            "SELECT v.edge_key,v.context,u.after_json "
            "FROM learner_values v JOIN learner_updates u ON u.update_id=v.update_id "
            "WHERE v.instance_id=? ORDER BY v.rowid",
            (instance_id,),
        ):
            learner[(str(row[0]), str(row[1]))] = json.loads(str(row[2]))
        bindings = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM semantic_bindings WHERE instance_id=? ORDER BY binding_id",
                (instance_id,),
            )
        ]
        key_bindings: dict[tuple[str, str], dict[str, Any]] = {}
        for binding in bindings:
            canonical_key = str(binding.get("canonical_key", ""))
            local_key = str(binding.get("local_key", ""))
            if not canonical_key or not local_key:
                continue
            pair = (canonical_key, local_key)
            if pair not in key_bindings:
                key_bindings[pair] = {
                    "canonical_label": binding.get("canonical_label"),
                    "source_binding_ids": [],
                }
            key_bindings[pair]["source_binding_ids"].append(
                str(binding["binding_id"])
            )
        key_binding_rows = [
            {
                "canonical_key": canonical_key,
                "local_key": local_key,
                "canonical_label": value["canonical_label"],
                "source_binding_ids_json": json.dumps(
                    value["source_binding_ids"], separators=(",", ":")
                ),
            }
            for (canonical_key, local_key), value in sorted(key_bindings.items())
        ]
        manifest_row = connection.execute(
            "SELECT * FROM manifests WHERE manifest_id=?", (manifest_id,)
        ).fetchone()
        manifest = None if manifest_row is None else dict(manifest_row)
        graph = {"nodes": nodes, "edges": edges, "routes": routes}
        learner_rows = [
            {"edge_key": edge_key, "context": context, "value": value}
            for (edge_key, context), value in sorted(learner.items())
        ]
        core_digest = _digest({"graph": graph, "learner": learner_rows})
        binding_digest = _digest(bindings)
        return {
            "active_instance_id": instance_id,
            "source_revision": int(head[1]),
            "source_manifest_id": manifest_id,
            "graph": graph,
            "learner": learner,
            "bindings": bindings,
            "manifest": manifest,
            "core_digest": core_digest,
            "binding_digest": binding_digest,
            "key_bindings": key_binding_rows,
            "key_binding_digest": _digest(key_binding_rows),
        }
    finally:
        connection.close()


def _install_bindings(destination: Path, bindings: list[dict[str, Any]]) -> None:
    """Install inherited semantic bindings into the new copy only."""

    connection = sqlite3.connect(destination)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS semantic_bindings ("
            "binding_id TEXT PRIMARY KEY, instance_id TEXT NOT NULL, "
            "canonical_key TEXT NOT NULL, local_key TEXT NOT NULL, "
            "canonical_label TEXT, value_json TEXT NOT NULL, content_digest TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS semantic_key_bindings ("
            "canonical_key TEXT NOT NULL, local_key TEXT NOT NULL, "
            "canonical_label TEXT, source_binding_ids_json TEXT NOT NULL)"
        )
        key_bindings: dict[tuple[str, str], dict[str, Any]] = {}
        for binding in bindings:
            binding_id = str(binding["binding_id"])
            payload = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            connection.execute(
                "INSERT INTO semantic_bindings VALUES(?,?,?,?,?,?,?)",
                (
                    binding_id,
                    str(binding.get("instance_id", "")),
                    str(binding.get("canonical_key", "")),
                    str(binding.get("local_key", "")),
                    (
                        None
                        if binding.get("canonical_label") is None
                        else str(binding["canonical_label"])
                    ),
                    payload,
                    hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                ),
            )
            canonical_key = str(binding.get("canonical_key", ""))
            local_key = str(binding.get("local_key", ""))
            if canonical_key and local_key:
                pair = (canonical_key, local_key)
                if pair not in key_bindings:
                    key_bindings[pair] = {
                        "canonical_label": binding.get("canonical_label"),
                        "source_binding_ids": [],
                    }
                key_bindings[pair]["source_binding_ids"].append(binding_id)
        for (canonical_key, local_key), value in sorted(key_bindings.items()):
            connection.execute(
                "INSERT INTO semantic_key_bindings VALUES(?,?,?,?)",
                (
                    canonical_key,
                    local_key,
                    None if value["canonical_label"] is None else str(value["canonical_label"]),
                    json.dumps(value["source_binding_ids"], separators=(",", ":")),
                ),
            )
        connection.commit()
    finally:
        connection.close()


def _field_inputs(
    graph: dict[str, dict[str, Any]],
    learner_values: dict[tuple[str, str], dict[str, Any]],
    local_to_canonical: dict[str, str],
) -> tuple[tuple[GraphConcept, ...], tuple[GraphEdge, ...], LearnerState]:
    concepts = tuple(
        GraphConcept(
            key,
            str(value.get("label", key)),
            str(value.get("kind", "concept")),
            annotations={
                k: v for k, v in value.items() if k not in {"concept_key", "label", "kind"}
            },
        )
        for key, value in sorted(graph["nodes"].items())
    )
    edges: list[GraphEdge] = []
    for local_key, value in sorted(graph["edges"].items()):
        canonical_key = local_to_canonical.get(local_key)
        if canonical_key is None:
            continue
        evidence = json.loads(str(value.get("evidence_json", "[]")))
        edges.append(
            GraphEdge(
                canonical_key,
                str(value["source_key"]),
                str(value["target_key"]),
                str(value["relationship"]),
                evidence=tuple(evidence),
                annotations={
                    k: v
                    for k, v in value.items()
                    if k
                    not in {"edge_key", "source_key", "target_key", "relationship", "evidence_json"}
                },
            )
        )
    states: list[EdgeState] = []
    for (edge_key, context), value in sorted(learner_values.items()):
        states.append(
            EdgeState(
                target_key=edge_key,
                context=context,
                accessibility=int(value.get("accessibility", 0)),
                support=int(value.get("support", 0)),
                consequence=int(value.get("consequence", 0)),
                relevant_opportunities=int(value.get("relevant_opportunities", 0)),
                inactivity_ticks=int(value.get("inactivity_ticks", 0)),
                unsupported_streak=int(value.get("unsupported_streak", 0)),
                lifetime_by_group=tuple(
                    sorted(
                        (str(k), int(v))
                        for k, v in dict(value.get("lifetime_by_group", {})).items()
                    )
                ),
                induced_by_group=tuple(
                    sorted(
                        (str(k), int(v))
                        for k, v in dict(value.get("induced_by_group", {})).items()
                    )
                ),
                rolling_credits=tuple(
                    CreditWindow(int(item["opportunity"]), int(item["amount"]))
                    for item in value.get("rolling_credits", [])
                ),
                last_consolidation_opportunity=value.get("last_consolidation_opportunity"),
                raw_occurrence_count=int(value.get("raw_occurrence_count", 0)),
                episode_keys=tuple(sorted(str(item) for item in value.get("episode_keys", []))),
            )
        )
    return concepts, tuple(edges), LearnerState(
        edge_states=tuple(sorted(states, key=lambda item: item.key)),
        global_opportunity=max(
            (int(value.get("relevant_opportunities", 0)) for value in learner_values.values()),
            default=0,
        ),
    )


def _saa_replay_equivalence(
    source_snapshot: dict[str, Any], destination: Path
) -> list[dict[str, Any]]:
    """Replay a small frozen SAA probe set against source and compact state."""

    source_map = {
        str(row["local_key"]): str(row["canonical_key"])
        for row in source_snapshot["key_bindings"]
    }
    source_inputs = _field_inputs(
        source_snapshot["graph"], source_snapshot["learner"], source_map
    )
    connection = sqlite3.connect(destination)
    connection.row_factory = sqlite3.Row
    try:
        compact_graph = {
            table: {
                str(row[0]): json.loads(str(row[1]))
                for row in connection.execute(
                    "SELECT "
                    f"{ {'nodes': 'node_key', 'edges': 'edge_key', 'routes': 'route_key'}[table] },"
                    f"value_json FROM graph_{table}"
                )
            }
            for table in ("nodes", "edges", "routes")
        }
        compact_learner = {
            (str(row[0]), str(row[1])): json.loads(str(row[2]))
            for row in connection.execute(
                "SELECT edge_key,context,value_json FROM learner_state"
            )
        }
        compact_map = {
            str(row["local_key"]): str(row["canonical_key"])
            for row in connection.execute(
                "SELECT local_key,canonical_key FROM semantic_key_bindings"
            )
        }
    finally:
        connection.close()
    compact_inputs = _field_inputs(compact_graph, compact_learner, compact_map)
    records: list[dict[str, Any]] = []
    for query in (
        "How might a remote habitat operate under uncertain conditions?",
        "What happens when a support system fails while unattended?",
        "How should limited options preserve recovery?",
    ):
        for seed in (1001, 1002, 1003):
            source_result = compute_saa_field(query, *source_inputs, field_seed=seed)
            compact_result = compute_saa_field(query, *compact_inputs, field_seed=seed)
            source_payload = source_result.to_dict()
            compact_payload = compact_result.to_dict()
            records.append(
                {
                    "query": query,
                    "field_seed": seed,
                    "distribution_equal": source_payload["accessibility_distribution"]
                    == compact_payload["accessibility_distribution"],
                    "landing_equal": source_payload["selected_landing"]
                    == compact_payload["selected_landing"],
                    "pressure_equal": source_payload["total_pressure"]
                    == compact_payload["total_pressure"],
                    "payload_equal": source_payload["payload"] == compact_payload["payload"],
                    "source_landing": source_payload["selected_landing"],
                    "compact_landing": compact_payload["selected_landing"],
                }
            )
    return records


def migrate(
    source: Path,
    destination: Path,
    manifest_path: Path,
    *,
    ancestor_name: str = "D100-I",
    source_run_id: str = "p3-introspect-100-20261001-r23",
    source_commit: str | None = None,
    saa_config_reference: str | None = None,
) -> dict[str, Any]:
    if source.resolve() == destination.resolve():
        raise ValueError("destination must differ from historical source")
    if destination.exists():
        raise FileExistsError(destination)
    source_snapshot = _source_snapshot(source)
    report = migrate_sqlite(source, destination)
    _install_bindings(destination, source_snapshot["bindings"])

    with CompactStore(destination, read_only=True) as compact:
        compact_digest = compact.state_digest()
        compact_verify = compact.verify()
        compact_graph = compact.graph_state()
        compact_learner = compact.learner_state()
    connection = sqlite3.connect(destination)
    connection.row_factory = sqlite3.Row
    try:
        binding_rows = [
            json.loads(str(row[0]))
            for row in connection.execute(
                "SELECT value_json FROM semantic_bindings ORDER BY binding_id"
            )
        ]
        key_binding_rows = [
            dict(row)
            for row in connection.execute(
                "SELECT canonical_key,local_key,canonical_label,source_binding_ids_json "
                "FROM semantic_key_bindings ORDER BY canonical_key"
            )
        ]
    finally:
        connection.close()
    binding_digest = _digest(binding_rows)
    key_binding_digest = _digest(key_binding_rows)
    source_before_sha = _sha256(source)
    # Re-read the source after migration: this guards the copy-only contract.
    source_after = _source_snapshot(source)
    if source_after["core_digest"] != source_snapshot["core_digest"]:
        raise RuntimeError("source logical state changed during migration")
    if source_after["binding_digest"] != source_snapshot["binding_digest"]:
        raise RuntimeError("source semantic bindings changed during migration")
    if compact_digest != source_snapshot["core_digest"]:
        raise RuntimeError(
            f"core state mismatch: source={source_snapshot['core_digest']} compact={compact_digest}"
        )
    if binding_digest != source_snapshot["binding_digest"]:
        raise RuntimeError(
            "semantic binding mismatch: "
            f"source={source_snapshot['binding_digest']} compact={binding_digest}"
        )
    if key_binding_digest != source_snapshot["key_binding_digest"]:
        raise RuntimeError(
            "canonical-to-materialized semantic binding map differs from source"
        )
    saa_replay = _saa_replay_equivalence(source_snapshot, destination)
    if not all(
        item["distribution_equal"]
        and item["landing_equal"]
        and item["pressure_equal"]
        and item["payload_equal"]
        for item in saa_replay
    ):
        raise RuntimeError("SAA replay differs between source and compact state")
    if _sha256(source) != source_before_sha:
        raise RuntimeError("source SHA-256 changed during migration")

    manifest: dict[str, Any] = {
        "schema": "mneme.d100.compact-ancestor.v1",
        "ancestor_name": ancestor_name,
        "normative_status": "reusable_developed_ancestor_not_normative_reference",
        "source_run_id": source_run_id,
        "source_commit": source_commit,
        "source": {
            "path": str(source),
            "sha256": source_before_sha,
            "active_instance_id": source_snapshot["active_instance_id"],
            "revision": source_snapshot["source_revision"],
            "manifest_id": source_snapshot["source_manifest_id"],
            "graph_counts": {key: len(value) for key, value in source_snapshot["graph"].items()},
            "learner_values": len(source_snapshot["learner"]),
            "semantic_bindings": len(source_snapshot["bindings"]),
            "semantic_key_bindings": len(source_snapshot["key_bindings"]),
            "core_digest": source_snapshot["core_digest"],
            "binding_digest": source_snapshot["binding_digest"],
            "key_binding_digest": source_snapshot["key_binding_digest"],
            "manifest_digest": _digest(source_snapshot["manifest"]),
        },
        "compact": {
            "path": str(destination),
            "sha256": _sha256(destination),
            "schema_version": 1,
            "bytes": destination.stat().st_size,
            "state_digest": compact_digest,
            "graph_counts": {key: len(value) for key, value in compact_graph.items()},
            "learner_values": len(compact_learner),
            "semantic_bindings": len(binding_rows),
            "semantic_key_bindings": len(key_binding_rows),
            "semantic_key_binding_digest": key_binding_digest,
            "verification": compact_verify,
        },
        "equivalence": {
            "core_state": compact_digest == source_snapshot["core_digest"],
            "semantic_bindings": binding_digest == source_snapshot["binding_digest"],
            "canonical_to_materialized_key_bindings": bool(key_binding_rows),
            "canonical_to_materialized_key_binding_digest": key_binding_digest,
            "source_immutable": True,
            "restart_state_digest": compact_digest,
            "saa_candidate_distribution": all(item["distribution_equal"] for item in saa_replay),
            "seeded_landings_and_payloads": all(
                item["landing_equal"]
                and item["pressure_equal"]
                and item["payload_equal"]
                for item in saa_replay
            ),
        },
        "saa_replay": saa_replay,
        "saa_configuration_reference": saa_config_reference,
        "migration": {
            "copy_only": True,
            "historical_source_mutated": False,
            "migration_report": report,
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ancestor-name", default="D100-I")
    parser.add_argument("--source-run-id", default="p3-introspect-100-20261001-r23")
    parser.add_argument("--source-commit")
    parser.add_argument("--saa-config-reference")
    args = parser.parse_args()
    values = vars(args)
    values["manifest_path"] = values.pop("manifest")
    print(json.dumps(migrate(**values), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
