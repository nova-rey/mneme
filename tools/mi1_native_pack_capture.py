"""Convert pinned llama.cpp MI1CAP01 capture into audited bank artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.mi1.native.bank import MemoryBank


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("source_text", type=Path)
    parser.add_argument("output", type=Path, help="portable NPZ path; writes .mi1 and JSON")
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--llama-commit", required=True)
    args = parser.parse_args()
    text = args.source_text.read_text(encoding="utf-8")
    bank = MemoryBank.from_native_capture(
        args.capture,
        source_text=text,
        model_sha256=args.model_sha256,
        llama_commit=args.llama_commit,
    )
    digest = bank.save(args.output)
    print(
        f"slots={bank.manifest.slot_count} layers={len(bank.manifest.layer_ids)} "
        f"native={args.output.with_suffix('.mi1')} sha256={digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
