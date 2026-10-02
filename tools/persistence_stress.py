#!/usr/bin/env python3
"""Model-free bounded persistence stress and recovery qualification.

This tool never opens or writes a research P3 database.  It creates synthetic
compact stores under the requested output directory and reports current-state
size, bounded journal size, checkpoint size, and restart recovery.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from mneme.state.compact import CompactStore


def _size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def run_case(events: int, root: Path, *, batch_size: int = 5_000) -> dict[str, Any]:
    path = root / f"compact-{events}.sqlite3"
    checkpoint = root / f"compact-{events}.checkpoint.sqlite3"
    rows: list[dict[str, Any]] = []
    start = time.monotonic()
    with CompactStore.create(path, journal_retention=10_000) as store:
        for offset in range(0, events, batch_size):
            end = min(events, offset + batch_size)
            records = []
            for index in range(offset, end):
                # Most opportunities are unchanged re-observations.  A value
                # changes only at a coarse epoch boundary, approximating the
                # P3 workload without using any model or hosted service.
                value = {"accessibility": index // 100_000, "support": 1, "context": "general"}
                records.append(
                    (f"edge-{index % 256}", f"context-{index % 8}", value, f"op-{index}")
                )
            store.put_learner_batch(records)
            if end in {10_000, 100_000, 1_000_000} or end == events:
                rows.append(
                    {
                        "events": end,
                        "sqlite_bytes": _size(path),
                        "wal_bytes": _size(Path(f"{path}-wal")),
                        "live_bytes_including_wal": _size(path) + _size(Path(f"{path}-wal")),
                        "learner_state_rows": int(
                            store.connection.execute(
                                "SELECT COUNT(*) FROM learner_state"
                            ).fetchone()[0]
                        ),
                        "journal_rows": int(
                            store.connection.execute(
                                "SELECT COUNT(*) FROM learner_journal"
                            ).fetchone()[0]
                        ),
                    }
                )
        state_digest = store.state_digest()
        problems = store.verify()
        checkpoint_id = store.checkpoint(checkpoint, checkpoint_id=f"stress-{events}")
        checkpoint_bytes = _size(checkpoint)
    with CompactStore(checkpoint, read_only=True) as restored:
        checkpoint_digest = restored.state_digest()
        checkpoint_problems = restored.verify()
    elapsed = time.monotonic() - start
    return {
        "events": events,
        "elapsed_seconds": round(elapsed, 3),
        "samples": rows,
        "final_sqlite_bytes": _size(path),
        "checkpoint_bytes": checkpoint_bytes,
        "checkpoint_id": checkpoint_id,
        "state_digest": state_digest,
        "checkpoint_digest": checkpoint_digest,
        "digest_match": state_digest == checkpoint_digest,
        "verify": problems,
        "checkpoint_verify": checkpoint_problems,
        "bytes_per_event": round(_size(path) / events, 6),
    }


def crash_recovery(root: Path) -> dict[str, Any]:
    path = root / "compact-crash.sqlite3"
    with CompactStore.create(path) as store:
        store.put_learner("edge", "general", {"accessibility": 1}, operation_id="initial")
    code = (
        "import sqlite3,sys,os; c=sqlite3.connect(sys.argv[1]); "
        "c.execute('BEGIN IMMEDIATE'); "
        "c.execute(\"UPDATE learner_state SET value_json='corrupt'\"); os._exit(17)"
    )
    result = subprocess.run([sys.executable, "-c", code, str(path)], check=False)
    with CompactStore(path, read_only=True) as recovered:
        return {
            "child_exit": result.returncode,
            "verify": recovered.verify(),
            "recovered_value": recovered.learner_state()[("edge", "general")],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--events", nargs="+", type=int, default=[10_000, 100_000, 1_000_000])
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="mneme-compact-stress-", dir=args.output) as raw:
        root = Path(raw)
        report = {
            "cases": [run_case(events, root) for events in args.events],
            "crash_recovery": crash_recovery(root),
        }
        print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
