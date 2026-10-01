#!/usr/bin/env python3
"""Create an experiment-safe compact copy of a P3 SQLite checkpoint.

The source is never modified.  The compact copy retains the latest materialized
learner value/update for each instance/edge/context and the latest learner
snapshot; the complete removed learner rows are streamed to an exact zstd
archive before compaction.  Graph, source, provenance, interpretation, and
development tables are left untouched.  Use a scratch filesystem with enough
room for the temporary copy (the P3 continuation uses ``/dev/shm``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any


LEARNER_TABLES = ("learner_updates", "learner_values", "learner_snapshots")


def _archive_rows(connection: sqlite3.Connection, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = subprocess.Popen(
        ["zstd", "-q", "-T0", "-3", "-o", str(destination)], stdin=subprocess.PIPE
    )
    assert writer.stdin is not None
    digest = hashlib.sha256()
    counts: dict[str, int] = {}
    try:
        for table in LEARNER_TABLES:
            columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
            count = 0
            for row in connection.execute(f"SELECT * FROM {table}"):
                line = (
                    json.dumps(
                        {"table": table, "columns": columns, "row": list(row)},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
                digest.update(line)
                writer.stdin.write(line)
                count += 1
            counts[table] = count
        writer.stdin.close()
        result = writer.wait()
        if result != 0:
            raise RuntimeError(f"zstd exited with status {result}")
    except BaseException:
        writer.kill()
        writer.wait()
        raise
    return {"sha256": digest.hexdigest(), "rows": counts, "bytes": destination.stat().st_size}


def compact(source: Path, output: Path, learner_archive: Path) -> dict[str, Any]:
    if source.resolve() == output.resolve():
        raise ValueError("source and output must be different; historical source is immutable")
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_suffix(output.suffix + ".staging")
    if staging.exists():
        staging.unlink()
    shutil.copyfile(source, staging)
    connection = sqlite3.connect(staging)
    try:
        connection.execute("PRAGMA foreign_keys=off")
        archive = _archive_rows(connection, learner_archive)
        triggers = connection.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='trigger' "
            "AND tbl_name IN ('learner_updates','learner_values','learner_snapshots')"
        ).fetchall()
        for name, _sql in triggers:
            connection.execute(f'DROP TRIGGER "{name}"')
        connection.execute(
            "CREATE TEMP TABLE keep_values AS SELECT * FROM learner_values "
            "WHERE rowid IN (SELECT max(rowid) FROM learner_values "
            "GROUP BY instance_id,edge_key,context)"
        )
        connection.execute(
            "CREATE TEMP TABLE keep_updates AS SELECT * FROM learner_updates "
            "WHERE update_id IN (SELECT DISTINCT update_id FROM keep_values) "
            "OR rowid IN (SELECT max(rowid) FROM learner_updates GROUP BY edge_key,context)"
        )
        connection.execute("DELETE FROM learner_values")
        connection.execute("DELETE FROM learner_updates")
        connection.execute("INSERT INTO learner_updates SELECT * FROM keep_updates")
        connection.execute("INSERT INTO learner_values SELECT * FROM keep_values")
        connection.execute(
            "DELETE FROM learner_snapshots WHERE rowid NOT IN "
            "(SELECT max(rowid) FROM learner_snapshots GROUP BY instance_id)"
        )
        for _name, sql in triggers:
            connection.execute(sql)
        connection.commit()
        connection.execute("PRAGMA integrity_check")
        connection.execute("VACUUM INTO ?", (str(output),))
    finally:
        connection.close()
        if staging.exists():
            staging.unlink()
    check = sqlite3.connect(output)
    try:
        integrity = str(check.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_keys = [tuple(row) for row in check.execute("PRAGMA foreign_key_check")]
        counts = {
            table: int(check.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            for table in LEARNER_TABLES
        }
    finally:
        check.close()
    if integrity != "ok" or foreign_keys:
        raise RuntimeError(f"compact copy validation failed: {integrity}, {foreign_keys[:1]}")
    return {
        "source": str(source),
        "output": str(output),
        "output_bytes": output.stat().st_size,
        "learner_archive": archive,
        "retained_rows": counts,
        "integrity": integrity,
        "foreign_key_errors": foreign_keys,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--learner-archive", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compact(args.source, args.output, args.learner_archive), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
