#!/usr/bin/env python3
"""Derive a clean P3 continuation boundary from an interrupted run.

The source run is immutable.  This tool operates on disposable SQLite copies,
removes records after the requested completed-thread boundary, verifies the
result, and publishes new checkpoint artifacts for a separately identified
prospective continuation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore


def _derive_clean_copy(source: Path, destination: Path, cutoff: int) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    connection = sqlite3.connect(destination)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=OFF")
    triggers = list(connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
    for name, _ in triggers:
        connection.execute(f'DROP TRIGGER "{name}"')

    revision = connection.execute(
        "SELECT manifest_id FROM revisions WHERE revision=?", (cutoff,)
    ).fetchone()
    if revision is None:
        raise RuntimeError(f"missing completed revision {cutoff} in {source}")
    base_manifest = str(revision[0])
    future_manifests = {
        str(row[0])
        for row in connection.execute(
            "SELECT manifest_id FROM manifests WHERE revision>?", (cutoff,)
        )
    }
    future_operations = {
        str(row[0])
        for row in connection.execute(
            "SELECT operation_id FROM operations WHERE base_revision>=?", (cutoff,)
        )
    }
    future_interpretation_operations = {
        str(row[0])
        for row in connection.execute(
            "SELECT operation_id FROM interpretation_operations "
            "WHERE base_manifest_id IN ({})".format(",".join("?" * len(future_manifests))),
            tuple(future_manifests),
        )
    } if future_manifests else set()
    future_operations.update(future_interpretation_operations)
    future_episodes = {
        str(row[0])
        for row in connection.execute(
            "SELECT episode_id FROM episodes WHERE operation_id IN ({})".format(
                ",".join("?" * len(future_operations))
            ),
            tuple(future_operations),
        )
    } if future_operations else set()
    future_interpretations = {
        str(row[0])
        for row in connection.execute(
            "SELECT interpretation_id FROM interpretations WHERE accepted_revision>?", (cutoff,)
        )
    }
    future_candidates = {
        str(row[0])
        for row in connection.execute(
            "SELECT candidate_id FROM candidates WHERE interpretation_id IN ({})".format(
                ",".join("?" * len(future_interpretations))
            ),
            tuple(future_interpretations),
        )
    } if future_interpretations else set()
    future_bindings = {
        str(row[0])
        for row in connection.execute(
            "SELECT binding_id FROM semantic_bindings WHERE interpretation_id IN ({})".format(
                ",".join("?" * len(future_interpretations))
            ),
            tuple(future_interpretations),
        )
    } if future_interpretations else set()
    future_sources = {
        str(row[0])
        for row in connection.execute(
            "SELECT source_id FROM sources WHERE operation_id IN ({})".format(
                ",".join("?" * len(future_operations))
            ),
            tuple(future_operations),
        )
    } if future_operations else set()
    future_generations = {
        str(row[0])
        for row in connection.execute(
            "SELECT generation_id FROM generation_records WHERE operation_id IN ({})".format(
                ",".join("?" * len(future_operations))
            ),
            tuple(future_operations),
        )
    } if future_operations else set()
    future_updates = {
        str(row[0])
        for row in connection.execute(
            "SELECT update_id FROM learner_updates WHERE operation_id IN ({})".format(
                ",".join("?" * len(future_operations))
            ),
            tuple(future_operations),
        )
    } if future_operations else set()
    id_sets = {
        "operation_id": future_operations,
        "episode_id": future_episodes,
        "manifest_id": future_manifests,
        "base_manifest_id": future_manifests,
        "parent_manifest_id": future_manifests,
        "inherited_base_manifest_id": future_manifests,
        "source_manifest_id": future_manifests,
        "pinned_manifest_id": future_manifests,
        "interpretation_id": future_interpretations,
        "candidate_id": future_candidates,
        "binding_id": future_bindings,
        "source_id": future_sources,
        "generation_id": future_generations,
        "update_id": future_updates,
    }
    tables = [
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    ]
    for table in tables:
        columns = [str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')]
        if "revision" in columns and table != "revisions":
            connection.execute(f'DELETE FROM "{table}" WHERE revision>?', (cutoff,))
        for column, values in id_sets.items():
            if column not in columns or not values:
                continue
            placeholders = ",".join("?" * len(values))
            connection.execute(
                f'DELETE FROM "{table}" WHERE "{column}" IN ({placeholders})',
                tuple(values),
            )
    connection.execute("DELETE FROM revisions WHERE revision>?", (cutoff,))
    connection.execute(
        "UPDATE current_state SET current_revision=?, current_manifest_id=? WHERE singleton=1",
        (cutoff, base_manifest),
    )
    for name, sql in triggers:
        connection.execute(sql)
    connection.commit()
    connection.execute("PRAGMA foreign_keys=ON")
    connection.close()
    with SQLiteStore(destination, read_only=True) as store:
        problems = store.verify()
        if problems:
            raise RuntimeError(f"derived boundary failed verification: {problems}")
    return {
        "source": str(source),
        "destination": str(destination),
        "cutoff_revision": cutoff,
        "base_manifest": base_manifest,
        "purged_operation_count": len(future_operations),
        "purged_episode_count": len(future_episodes),
        "historical_source_unchanged": True,
    }


def derive(source_root: Path, destination_root: Path, completed_threads: int) -> dict[str, Any]:
    if destination_root.exists():
        raise RuntimeError(f"destination already exists: {destination_root}")
    destination_root.mkdir(parents=True)
    source_subjects = source_root / "subjects"
    dest_subjects = destination_root / "subjects"
    dest_snapshots = destination_root / "snapshots"
    dest_subjects.mkdir()
    dest_snapshots.mkdir()
    # Retain the previously published checkpoint-10 lineage so the new
    # continuation can still perform the frozen 0/10/25/50/75/100 readouts.
    for label in ("I", "N"):
        source_checkpoint = source_root / "snapshots" / f"{label}-10.sqlite3"
        shutil.copy2(source_checkpoint, dest_snapshots / source_checkpoint.name)
    destination_root.joinpath("introspection").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        source_root / "introspection" / "I-10.json",
        destination_root / "introspection" / "I-10.json",
    )
    records = []
    for label, cutoff in (("I", 376), ("N", 378)):
        source = source_subjects / f"{label}.sqlite3"
        working = dest_subjects / f"{label}.sqlite3"
        records.append(_derive_clean_copy(source, working, cutoff))
        with SQLiteStore(working) as store:
            create_checkpoint(
                store,
                dest_snapshots / f"{label}-{completed_threads}.sqlite3",
                checkpoint_id=f"p3-boundary-{label}-{completed_threads}",
            )
    source_ledger = source_root / "introspection" / "I.json"
    destination_ledger = destination_root / "introspection" / f"I-{completed_threads}.json"
    destination_ledger.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_ledger, destination_ledger)
    source_transcripts = sorted(source_root.rglob("transcript-P3-*.json"))
    copied_transcripts = 0
    for item in source_transcripts:
        try:
            index = int(item.stem.rsplit("-", 1)[1])
        except ValueError:
            continue
        if index > completed_threads:
            continue
        target = destination_root / "experiments" / "p3-introspect-100" / "development" / item.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        copied_transcripts += 1
    progress = {
        "threads_completed": completed_threads,
        "checkpoints": {
            "10": {
                label: str(destination_root / "snapshots" / f"{label}-10.sqlite3")
                for label in ("I", "N")
            },
            str(completed_threads): {
                label: str(destination_root / "snapshots" / f"{label}-{completed_threads}.sqlite3")
                for label in ("I", "N")
            }
        },
        "introspection_reviews": completed_threads,
        "derived_from": str(source_root),
    }
    (destination_root / "progress.json").write_text(
        json.dumps(progress, indent=2) + "\n", encoding="utf-8"
    )
    receipt = {
        "status": "DERIVED_CLEAN_CONTINUATION_BOUNDARY",
        "source_run": str(source_root),
        "completed_threads": completed_threads,
        "records": records,
        "copied_transcript_count": copied_transcripts,
        "checkpoint_sha256": {
            label: hashlib.sha256(
                Path(
                    destination_root / "snapshots" / f"{label}-{completed_threads}.sqlite3"
                ).read_bytes()
            ).hexdigest()
            for label in ("I", "N")
        },
        "partial_thread_state_excluded": True,
        "historical_source_unchanged": True,
    }
    (destination_root / "BOUNDARY_DERIVATION.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--destination-root", type=Path, required=True)
    parser.add_argument("--completed-threads", type=int, default=24)
    args = parser.parse_args()
    print(
        json.dumps(
            derive(args.source_root, args.destination_root, args.completed_threads), indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
