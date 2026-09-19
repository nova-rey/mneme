"""Transparent no-learning baseline measurements and reports.

This module consumes completed evaluation observations and produces small,
inspectable summaries.  It has no dependency on a lineage store and never
returns or persists model output text.  The measurements describe ordinary
output variation; they are not individuality or personality scores.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import subprocess
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, cast

from .artifacts import canonical_json


class BaselineError(ValueError):
    """An observation or report field is not safe for baseline measurement."""


_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_SECRET_PARTS = (
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "api_key",
    "apikey",
    "bearer",
    "cookie",
    "header",
)


@dataclass(frozen=True)
class BaselineObservation:
    """One completed evaluation response identified by scientific coordinates."""

    subject_slot: int | str
    probe_ordinal: int
    repetition: int
    output: str

    def __post_init__(self) -> None:
        if isinstance(self.subject_slot, bool) or not isinstance(self.subject_slot, (int, str)):
            raise BaselineError("subject_slot must be an integer or non-empty string")
        if isinstance(self.subject_slot, int) and self.subject_slot < 0:
            raise BaselineError("subject_slot must be non-negative")
        if isinstance(self.subject_slot, str) and not self.subject_slot:
            raise BaselineError("subject_slot must be non-empty")
        for field_name, value in (
            ("probe_ordinal", self.probe_ordinal),
            ("repetition", self.repetition),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BaselineError(f"{field_name} must be a non-negative integer")
        if not isinstance(self.output, str):
            raise BaselineError("output must be a string")

    @property
    def coordinate(self) -> tuple[int | str, int, int]:
        return self.subject_slot, self.probe_ordinal, self.repetition


def _observation(value: BaselineObservation | Mapping[str, Any]) -> BaselineObservation:
    if isinstance(value, BaselineObservation):
        return value
    if not isinstance(value, Mapping):
        raise BaselineError("observations must be BaselineObservation values or mappings")
    required = {"subject_slot", "probe_ordinal", "repetition", "output"}
    missing = sorted(required - set(value))
    if missing:
        raise BaselineError(f"observation missing field(s): {', '.join(missing)}")
    return BaselineObservation(
        value["subject_slot"], value["probe_ordinal"], value["repetition"], value["output"]
    )


def _normalize(text: str) -> str:
    """Normalize only presentation differences for a transparent equality check."""

    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return " ".join(normalized.split()).casefold()


def _words(text: str) -> frozenset[str]:
    return frozenset(match.group(0).casefold() for match in _WORD_RE.finditer(text))


def _jaccard(left: str, right: str) -> float:
    left_words = _words(left)
    right_words = _words(right)
    if not left_words and not right_words:
        return 1.0
    return len(left_words & right_words) / len(left_words | right_words)


def _pair(left: BaselineObservation, right: BaselineObservation) -> dict[str, float | bool]:
    return {
        "exact_match": left.output == right.output,
        "normalized_match": _normalize(left.output) == _normalize(right.output),
        "lexical_jaccard": _jaccard(left.output, right.output),
        "token_length_delta": float(abs(len(_words(left.output)) - len(_words(right.output)))),
        "character_length_delta": float(abs(len(left.output) - len(right.output))),
    }


def _pair_summary(pairs: Sequence[Mapping[str, float | bool]]) -> dict[str, int | float | None]:
    if not pairs:
        return {
            "pair_count": 0,
            "exact_match_rate": None,
            "normalized_match_rate": None,
            "mean_lexical_jaccard": None,
            "mean_token_length_delta": None,
            "mean_character_length_delta": None,
        }
    count = len(pairs)

    def mean(name: str) -> float:
        return sum(float(pair[name]) for pair in pairs) / count

    return {
        "pair_count": count,
        "exact_match_rate": sum(bool(pair["exact_match"]) for pair in pairs) / count,
        "normalized_match_rate": sum(bool(pair["normalized_match"]) for pair in pairs) / count,
        "mean_lexical_jaccard": mean("lexical_jaccard"),
        "mean_token_length_delta": mean("token_length_delta"),
        "mean_character_length_delta": mean("character_length_delta"),
    }


def _feature_summary(observations: Sequence[BaselineObservation]) -> dict[str, int | float | None]:
    if not observations:
        return {
            "response_count": 0,
            "mean_token_length": None,
            "mean_character_length": None,
        }
    return {
        "response_count": len(observations),
        "mean_token_length": sum(len(_words(item.output)) for item in observations)
        / len(observations),
        "mean_character_length": sum(len(item.output) for item in observations) / len(observations),
    }


def measure_baseline(
    observations: Iterable[BaselineObservation | Mapping[str, Any]],
) -> dict[str, Any]:
    """Measure within- and between-instance variation from completed probes.

    Within-instance pairs compare repeated observations of the same subject and
    probe.  Between-instance pairs compare different subjects at the same probe
    and repetition.  Administrative IDs, paths, and raw output content are not
    used in either comparison.
    """

    parsed = [_observation(item) for item in observations]
    seen: set[tuple[int | str, int, int]] = set()
    for item in parsed:
        if item.coordinate in seen:
            raise BaselineError(f"duplicate observation coordinate: {item.coordinate!r}")
        seen.add(item.coordinate)

    within_groups: dict[tuple[int | str, int], list[BaselineObservation]] = defaultdict(list)
    for item in parsed:
        within_groups[(item.subject_slot, item.probe_ordinal)].append(item)
    within_pairs = [
        _pair(left, right)
        for group in within_groups.values()
        for left, right in combinations(sorted(group, key=lambda item: item.repetition), 2)
    ]

    between_groups: dict[tuple[int, int], list[BaselineObservation]] = defaultdict(list)
    for item in parsed:
        between_groups[(item.probe_ordinal, item.repetition)].append(item)
    between_pairs = [
        _pair(left, right)
        for group in between_groups.values()
        for left, right in combinations(sorted(group, key=lambda item: str(item.subject_slot)), 2)
    ]

    return {
        "observation_count": len(parsed),
        "subject_count": len({item.subject_slot for item in parsed}),
        "probe_count": len({item.probe_ordinal for item in parsed}),
        "features": _feature_summary(parsed),
        "within_instance": _pair_summary(within_pairs),
        "between_instance": _pair_summary(between_pairs),
        "method": {
            "within_instance": "same subject and probe, different repetitions",
            "between_instance": "different subjects, same probe and repetition",
            "normalization": "Unicode NFC, line-ending and whitespace normalization, case-folding",
            "lexical_similarity": "Jaccard similarity over unique case-folded word tokens",
        },
    }


def _safe_value(value: Any, *, depth: int = 0) -> Any:
    """Copy JSON-like metadata while redacting likely credentials and raw content."""

    if depth > 5:
        return "[TRUNCATED]"
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            lowered = key_text.casefold()
            usage_key = lowered in {"prompt_tokens", "completion_tokens", "total_tokens"}
            if (any(part in lowered for part in _SECRET_PARTS) and not usage_key) or lowered in {
                "raw_metadata",
                "raw_output",
                "messages",
                "content",
            }:
                result[key_text] = "[REDACTED]"
            else:
                result[key_text] = _safe_value(child, depth=depth + 1)
        return result
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe_value(item, depth=depth + 1) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            raise BaselineError("report metadata contains a non-finite number")
        return value
    return str(value)


def _safe_bindings(bindings: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if not bindings:
        return []
    allowed = {
        "slot",
        "subject_slot",
        "lineage_id",
        "instance_id",
        "cohort",
        "condition",
        "start",
        "checkpoint_id",
        "revision",
        "manifest_id",
        "sha256",
        "snapshot_sha256",
    }
    result: list[dict[str, Any]] = []
    for item in bindings:
        if not isinstance(item, Mapping):
            raise BaselineError("subject bindings must be mappings")
        result.append(
            {str(key): _safe_value(value) for key, value in item.items() if key in allowed}
        )
    return result


@dataclass(frozen=True)
class BaselineReport:
    """Sanitized machine-readable baseline report with a concise text view."""

    data: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(canonical_json(self.data).decode("utf-8")))

    def to_json(self) -> str:
        return canonical_json(self.data).decode("utf-8") + "\n"

    def text(self) -> str:
        return render_baseline_report(self.data)

    def write(self, json_path: Path | str, text_path: Path | str | None = None) -> None:
        json_target = Path(json_path)
        json_target.parent.mkdir(parents=True, exist_ok=True)
        json_target.write_text(self.to_json(), encoding="utf-8")
        if text_path is not None:
            text_target = Path(text_path)
            text_target.parent.mkdir(parents=True, exist_ok=True)
            text_target.write_text(self.text(), encoding="utf-8")


def build_baseline_report(
    *,
    experiment_name: str,
    contract_revision: int,
    contract_sha256: str,
    software_revision: str,
    subject_bindings: Sequence[Mapping[str, Any]] | None,
    host: Mapping[str, Any],
    budgets: Mapping[str, Any],
    observations: Iterable[BaselineObservation | Mapping[str, Any]],
    actual_usage: Mapping[str, Any] | None = None,
    evaluation_isolation: Mapping[str, Any] | None = None,
    restart_resume: Mapping[str, Any] | None = None,
    deviations: Sequence[str] | None = None,
) -> BaselineReport:
    """Build the P0.4 report without storing model text or provider secrets."""

    if not isinstance(experiment_name, str) or not experiment_name:
        raise BaselineError("experiment_name must be non-empty")
    if (
        isinstance(contract_revision, bool)
        or not isinstance(contract_revision, int)
        or contract_revision < 1
    ):
        raise BaselineError("contract_revision must be a positive integer")
    if not isinstance(contract_sha256, str) or not contract_sha256:
        raise BaselineError("contract_sha256 must be non-empty")
    if not isinstance(software_revision, str) or not software_revision:
        raise BaselineError("software_revision must be non-empty")
    if not isinstance(host, Mapping) or not isinstance(budgets, Mapping):
        raise BaselineError("host and budgets must be mappings")
    report = {
        "schema_version": 1,
        "report_kind": "mneme-no-learning-baseline",
        "scientific_identity": {
            "name": experiment_name,
            "contract_revision": contract_revision,
            "label": f"{experiment_name} / revision {contract_revision}",
        },
        "contract_sha256": contract_sha256,
        "software_revision": software_revision,
        "subject_bindings": _safe_bindings(subject_bindings),
        "host": _safe_value(host),
        "budgets": _safe_value(budgets),
        "actual_usage": _safe_value(actual_usage or {}),
        "measurements": measure_baseline(observations),
        "evaluation_isolation": _safe_value(evaluation_isolation or {}),
        "restart_resume": _safe_value(restart_resume or {}),
        "developmental_influence": {
            "enabled": False,
            "history_injected_into_generation": False,
            "learning_or_association_updates": False,
            "statement": (
                "Stored developmental history remained behaviorally inert; observed differences "
                "are ordinary no-learning variation under the tested conditions."
            ),
        },
        "deviations": [str(item) for item in (deviations or ())],
        "limitations": [
            "This report is a Phase Zero noise-floor characterization, not an individuality claim.",
            "Lexical overlap and response agreement are transparent descriptive "
            "measurements, not personality metrics.",
            "Provider-managed sampling cannot establish causal developmental differentiation.",
        ],
    }
    return BaselineReport(report)


def render_baseline_report(report: Mapping[str, Any]) -> str:
    """Render a human-readable report without exposing model outputs."""

    if not isinstance(report, Mapping):
        raise BaselineError("report must be a mapping")
    identity = report.get("scientific_identity", {})
    measurements = report.get("measurements", {})
    within = measurements.get("within_instance", {}) if isinstance(measurements, Mapping) else {}
    between = measurements.get("between_instance", {}) if isinstance(measurements, Mapping) else {}

    def value(mapping: Any, key: str) -> str:
        if not isinstance(mapping, Mapping):
            return "unknown"
        item = mapping.get(key)
        return "unknown" if item is None else str(item)

    lines = [
        "MNEME P0.4 no-learning baseline",
        f"Scientific identity: {value(identity, 'label')}",
        f"Contract digest: {value(report, 'contract_sha256')}",
        f"Software revision: {value(report, 'software_revision')}",
        "",
        "Developmental influence: DISABLED",
        "History injected into generation: false",
        f"Observations: {value(measurements, 'observation_count')}",
        f"Subjects: {value(measurements, 'subject_count')}",
        f"Probes: {value(measurements, 'probe_count')}",
        "",
        "Within-instance variation (same subject/probe, repeated probes):",
        f"  exact agreement: {value(within, 'exact_match_rate')}",
        f"  normalized agreement: {value(within, 'normalized_match_rate')}",
        f"  lexical Jaccard: {value(within, 'mean_lexical_jaccard')}",
        "Between-instance variation (different subjects, matched probe/repetition):",
        f"  exact agreement: {value(between, 'exact_match_rate')}",
        f"  normalized agreement: {value(between, 'normalized_match_rate')}",
        f"  lexical Jaccard: {value(between, 'mean_lexical_jaccard')}",
        "",
        "The measurements describe ordinary no-learning output variation; they do not "
        "establish individuality or personality.",
    ]
    return "\n".join(lines) + "\n"


def build_report(*, run_id: str, lab: str | Path) -> dict[str, Any]:
    """Collect sanitized observations from one completed integrated run."""

    from .artifacts import ArtifactStore

    store = ArtifactStore(lab)
    run = store.locate_run(run_id)
    inspected = store.inspect_run(run_id, verify=True)
    if not inspected.get("verified"):
        raise BaselineError("run artifacts failed integrity verification")
    experiment = store._read_json(run / "experiment.json")
    preflight = store._read_json(run / "preflight.json")
    manifest = store._read_json(run / "run-manifest.json")
    bindings = store._read_json(run / "bindings.json")
    observations: list[BaselineObservation] = []
    usage: dict[str, Any] = {
        "evaluation_calls": 0,
        "development_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    for check in inspected.get("checks", []):
        if not isinstance(check, Mapping) or check.get("status") != "RESULT":
            continue
        if not isinstance(check.get("output"), str):
            continue
        observations.append(
            BaselineObservation(
                check.get("subject_slot", "unknown"),
                int(check.get("probe_ordinal", 0)),
                int(check.get("repetition", 0)),
                str(check["output"]),
            )
        )
        usage["evaluation_calls"] += 1
        token_usage = check.get("token_usage")
        if isinstance(token_usage, Mapping):
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = token_usage.get(key)
                if isinstance(value, int) and value >= 0:
                    usage[key] += value
    execution_state = store.root / "execution" / run_id / "state.json"
    execution = {}
    if execution_state.is_file():
        try:
            execution = json.loads(execution_state.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BaselineError(f"execution state is unreadable: {exc}") from exc
    journal = store.root / "execution" / run_id / "journal.jsonl"
    if journal.is_file():
        for line in journal.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BaselineError(f"execution journal is unreadable: {exc}") from exc
            if isinstance(event, Mapping) and event.get("kind") == "development":
                usage["development_calls"] += int(event.get("model_calls", 0))
    subjects_root = store.root / "execution" / run_id / "subjects"
    if subjects_root.is_dir():
        for subject_path in sorted(subjects_root.glob("*.sqlite3")):
            try:
                with sqlite3.connect(f"file:{subject_path}?mode=ro", uri=True) as connection:
                    rows = connection.execute(
                        "SELECT usage_json FROM generation_records WHERE usage_json IS NOT NULL"
                    ).fetchall()
            except sqlite3.Error as exc:
                raise BaselineError(f"subject usage is unreadable: {exc}") from exc
            for (usage_json,) in rows:
                try:
                    token_usage = json.loads(usage_json)
                except (TypeError, json.JSONDecodeError) as exc:
                    raise BaselineError(f"subject usage is invalid: {exc}") from exc
                if isinstance(token_usage, Mapping):
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                        value = token_usage.get(key)
                        if isinstance(value, int) and value >= 0:
                            usage[key] += value
    identity = experiment.get("name")
    revision = experiment.get("contract_revision")
    if not isinstance(identity, str) or not isinstance(revision, int):
        raise BaselineError("experiment identity is incomplete")
    host = preflight.get("host", experiment.get("host", {}))
    budgets = preflight.get("budget", {})
    software = "unknown"
    try:
        software = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).parents[2], text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        pass
    report = build_baseline_report(
        experiment_name=identity,
        contract_revision=revision,
        contract_sha256=str(manifest.get("contract_sha256", "")),
        software_revision=software,
        subject_bindings=bindings.get("subjects") if isinstance(bindings, Mapping) else None,
        host=host if isinstance(host, Mapping) else {},
        budgets=budgets if isinstance(budgets, Mapping) else {},
        observations=observations,
        actual_usage={**usage, "execution_status": execution.get("status", "UNKNOWN")},
        evaluation_isolation={"observations": len(observations), "developmental_writeback": False},
        restart_resume={"execution_status": execution.get("status", "UNKNOWN")},
    )
    return report.to_dict()
