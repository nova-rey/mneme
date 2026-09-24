# MNEME P2.3 Extractor Enum Negative Clarification V5

- Date: 2026-09-24
- Scope: bounded prompt clarification after preserved recovery-v6 stop
- Provider calls: 0
- Historical evidence: unchanged

The residue-v4 extractor prompt now states that complete vocabulary membership is
closed and gives `holds` and `precedes` as invalid examples unless listed. The
relationship vocabulary and strict validator are unchanged; no unsupported
label is accepted or normalized. This is a prompt-only correction for the
preserved Gemma output at `extraction-s1-e7`.

Offline validation: 355 pytest, Ruff, strict mypy, wheel build, and
fresh-install smoke passed.
