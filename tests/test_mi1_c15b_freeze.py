from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


def test_c15b_freeze_changes_only_run_identity_and_single_slot_runtime(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    parent = json.loads(
        (
            root / "docs/receipts/MNEME_Phase_4_MI1_C15_Encoding_Calibration_Freeze_20261011.json"
        ).read_text()
    )
    parent["status"] = "FROZEN_BEFORE_CALIBRATION_GENERATION"
    parent_path = tmp_path / "parent.json"
    parent_path.write_text(json.dumps(parent))
    execution = tmp_path / "execution.json"
    execution.write_text(json.dumps({"generation_issued": False}))
    failure = tmp_path / "failed.json"
    failure.write_text(
        json.dumps(
            {
                "attempt_id": "C15-calibration-A33-latent_raw_A-34201",
                "status": "FAILED",
                "metadata": {"stream": {"stream_event_count": 0}},
            }
        )
    )
    crash = tmp_path / "crash.log"
    crash.write_text("GGML_ASSERT(ubatch->n_seqs == 1 && ubatch->n_seqs_unq == 1)")
    output = tmp_path / "c15b.json"
    subprocess.run(
        [
            sys.executable,
            str(root / "tools/freeze_mi1_c15b.py"),
            "--parent-plan",
            str(parent_path),
            "--parent-execution",
            str(execution),
            "--failed-receipt",
            str(failure),
            "--crash-log",
            str(crash),
            "--output",
            str(output),
        ],
        check=True,
        cwd=root,
        capture_output=True,
        text=True,
    )
    result = json.loads(output.read_text())
    assert result["call_count"] == 80
    assert result["server_runtime"]["parallel_slots"] == 1
    assert len(result["coordinates"]) == len(parent["coordinates"])
    for before, after in zip(parent["coordinates"], result["coordinates"], strict=True):
        assert before["request"] == after["request"]
        assert before["request_sha256"] == after["request_sha256"]
        assert before["bank_source_sha256"] == after["bank_source_sha256"]
        assert after["coordinate_id"].startswith("C15B-")
    assert (
        hashlib.sha256(parent_path.read_bytes()).hexdigest() == result["parents"]["c15_plan_sha256"]
    )
