#!/usr/bin/env python3
# ruff: noqa: E501
"""Freeze the Phase Two SAA ten-thread experiment contract.

This module is an intentionally isolated harness boundary.  It owns the
prospective schedule, seeds, readout coordinates, and evidence shape for
``F0-SAA-v1``; it does not alter the existing F0 field implementation or the
controller.  ``--emit-plan`` only writes a deterministic plan and performs no
provider or local-model calls.  A later execution adapter can consume the
frozen contract and use the existing PilotRuntime/shared-Interloper services.

The contract is kept here so a live runner cannot quietly change Thread 10,
field seeds, repetition counts, or the removal/restoration coordinates after
Threads 1--9 have been observed.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mneme.experiments.shared_interloper import ThreadSpec

EXPERIMENT = "p2.3-saa-ten-thread-ab"
CONTRACT_REVISION = 1
SAA_VERSION = "f0-saa-v1"
FIELD_RNG_ALGORITHM = "python-random.Random-mt19937"

# These values are part of the prospective contract.  They are intentionally
# independent of run IDs, branch names, filenames, and database order.
FIELD_SEEDS = (71001, 71002, 71003, 71004, 71005, 71006)
GEMMA_READOUT_SEEDS = (81001, 81002, 81003)
QWEN_DEVELOPMENT_SEEDS = (91001, 91002, 91003, 91004, 91005, 91006, 91007, 91008, 91009)
DEVELOPMENT_TURNS_MIN = 6
DEVELOPMENT_TURNS_TARGET = 8
DEVELOPMENT_TURNS_MAX = 10
READOUT_REPETITIONS = 3

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class SAAThread:
    """A frozen public setup plus private participant circumstances."""

    thread_id: str
    domain: str
    opening: str
    concerns: tuple[str, ...]
    target_turns: int = DEVELOPMENT_TURNS_TARGET

    def __post_init__(self) -> None:
        if not _SAFE_ID.fullmatch(self.thread_id):
            raise ValueError(f"invalid thread id: {self.thread_id!r}")
        if not DEVELOPMENT_TURNS_MIN <= self.target_turns <= DEVELOPMENT_TURNS_MAX:
            raise ValueError("target_turns must remain within the declared runway")
        if not self.opening.strip() or not self.concerns:
            raise ValueError("each thread requires an opening and private concerns")

    def to_dict(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "domain": self.domain,
            "opening": self.opening,
            "concerns": list(self.concerns),
            "target_turns": self.target_turns,
            "runway": {
                "minimum": DEVELOPMENT_TURNS_MIN,
                "target": DEVELOPMENT_TURNS_TARGET,
                "maximum": DEVELOPMENT_TURNS_MAX,
            },
        }

    def shared_interloper_spec(self) -> ThreadSpec:
        """Adapt the frozen schedule to the existing Qwen contract."""

        return ThreadSpec(self.thread_id, self.opening, self.concerns)


THREAD_SCHEDULE: tuple[SAAThread, ...] = (
    SAAThread(
        "T01",
        "gardening-biological-cultivation",
        "I am trying to keep a few balcony plants healthy through hot weather and a short absence. What would you think through first?",
        ("afternoon heat is uneven", "someone may be unable to check every pot", "ordinary materials and modest effort are preferred"),
    ),
    SAAThread(
        "T02",
        "travel-packing-uncertainty",
        "I am packing for a short trip with uncertain weather and a return time that may slip. How would you keep the plan workable?",
        ("space is limited", "one delay could affect the next step", "a backup should not add much bulk"),
    ),
    SAAThread(
        "T03",
        "cooking-improvisation-taste",
        "I have a few ingredients, mixed preferences, and no reliable recipe for tonight. How would you improvise a meal?",
        ("one ingredient may be unavailable", "the meal should remain adjustable", "different people want different textures"),
    ),
    SAAThread(
        "T04",
        "music-rhythm-arrangement",
        "I am arranging a small piece for unevenly skilled players. How could it stay coherent while leaving room to adapt?",
        ("parts have different confidence levels", "timing may drift", "the arrangement should remain expressive"),
    ),
    SAAThread(
        "T05",
        "household-repair-troubleshooting",
        "A household device works intermittently and replacement parts are not immediately available. How would you investigate it?",
        ("the symptom is not always reproducible", "a temporary fix may be useful", "damage from a rushed repair is costly"),
    ),
    SAAThread(
        "T06",
        "games-probability-strategy",
        "I am designing a small game where luck matters but choices should still feel meaningful. What would you balance?",
        ("players need understandable risks", "a bad early result should not end the game", "different strategies should remain viable"),
    ),
    SAAThread(
        "T07",
        "art-visual-composition",
        "I am making a visual piece from a limited set of colors and repeated shapes. How might I keep it from becoming monotonous?",
        ("repetition can create structure", "contrast must remain intentional", "the materials cannot be expanded"),
    ),
    SAAThread(
        "T08",
        "social-coordination-shared-resources",
        "Several neighbors need to share a scarce resource while their schedules keep changing. How would you organize the arrangement?",
        ("availability is uneven", "people need to trust the process", "the resource cannot be reserved forever"),
    ),
    SAAThread(
        "T09",
        "astronomy-navigation-observation",
        "I am planning an evening observation session with uncertain visibility and limited equipment. What would you prepare for?",
        ("conditions may change quickly", "the best target may not be visible", "the session should still be worthwhile"),
    ),
    # Thread 10 is frozen before any Thread 1--9 execution and contains no
    # explicit reference to the domains or answers above.  Its constraints
    # permit multiple bridges without targeting one learned nexus.
    SAAThread(
        "T10",
        "isolated-seasonal-community-project",
        "A small coastal community is opening a temporary night market in a converted ferry terminal. Power, weather, volunteers, delicate displays, and closing procedures are all uncertain. How would you design the project so it remains workable?",
        ("conditions can change during the event", "people have different roles and energy", "the setup must be safe to close and reopen"),
    ),
)


READOUT_PROBES: tuple[str, ...] = (
    "A remote team must build a temporary public service with limited equipment and unpredictable interruptions. What would you make explicit first?",
    "You are explaining a new process to people who will use it at different speeds and under changing conditions. How would you structure the explanation?",
    "A small project has several plausible designs, none obviously best, and one failure could make recovery expensive. How would you compare them?",
    "A group is preparing an unfamiliar shared space with practical constraints and a need for some visual or social character. What would you attend to?",
)


@dataclass(frozen=True)
class SAAConfig:
    """Frozen, inspectable SAA parameters for the first approximation."""

    version: str = SAA_VERSION
    exploration: str = "on"
    max_landing_candidates: int = 8
    max_propagation_depth: int = 2
    propagation_attenuation: int = 600_000
    pressure_budget: int = 1_000_000
    max_active_contributors: int = 4
    pressure_floor: int = 20_000
    background_floor: int = 30_000
    exploration_budget: int = 100_000
    activation_decay: int = 800_000
    renderer_max_chars: int = 900
    renderer_max_tendencies: int = 3
    familiar_context_relevance_weight: int = 700_000
    novel_context_relevance_weight: int = 250_000
    novelty_flatness_threshold: int = 250_000
    consequence_step: int = 50_000
    consequence_floor: int = 50_000
    field_rng_algorithm: str = FIELD_RNG_ALGORITHM

    def __post_init__(self) -> None:
        bounded = (
            self.propagation_attenuation,
            self.pressure_budget,
            self.pressure_floor,
            self.background_floor,
            self.exploration_budget,
            self.activation_decay,
            self.familiar_context_relevance_weight,
            self.novel_context_relevance_weight,
            self.novelty_flatness_threshold,
            self.consequence_floor,
        )
        if any(value < 0 or value > 1_000_000 for value in bounded):
            raise ValueError("SAA fixed-point parameters must be in [0, 1_000_000]")
        if self.exploration not in {"off", "on"}:
            raise ValueError("exploration must be off or on")
        if self.max_landing_candidates < 1 or self.max_active_contributors < 1:
            raise ValueError("SAA candidate/contributor caps must be positive")
        if self.max_propagation_depth < 0 or self.renderer_max_tendencies < 1:
            raise ValueError("SAA depth and renderer caps must be positive")
        if self.renderer_max_chars < 1 or self.exploration_budget > self.pressure_budget:
            raise ValueError("invalid SAA renderer or exploration budget")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "exploration": self.exploration,
            "max_landing_candidates": self.max_landing_candidates,
            "max_propagation_depth": self.max_propagation_depth,
            "propagation_attenuation": self.propagation_attenuation,
            "pressure_budget": self.pressure_budget,
            "max_active_contributors": self.max_active_contributors,
            "pressure_floor": self.pressure_floor,
            "background_floor": self.background_floor,
            "exploration_budget": self.exploration_budget,
            "activation_decay": self.activation_decay,
            "renderer_max_chars": self.renderer_max_chars,
            "renderer_max_tendencies": self.renderer_max_tendencies,
            "familiar_context_relevance_weight": self.familiar_context_relevance_weight,
            "novel_context_relevance_weight": self.novel_context_relevance_weight,
            "novelty_flatness_threshold": self.novelty_flatness_threshold,
            "consequence_step": self.consequence_step,
            "consequence_floor": self.consequence_floor,
            "field_rng_algorithm": self.field_rng_algorithm,
        }


@dataclass(frozen=True)
class SAAFieldTrace:
    """Machine-readable evidence for one SAA accessibility coordinate."""

    coordinate: str
    subject: str
    thread: str
    turn: int
    current_input: str
    active_context: tuple[dict[str, Any], ...]
    eligible_candidates: tuple[dict[str, Any], ...]
    normalized_distribution: tuple[dict[str, Any], ...]
    flatness: dict[str, Any]
    field_seed: int
    random_draw: int
    selected_landing: str | None
    propagated_neighborhood: tuple[dict[str, Any], ...]
    rendered_payload: str
    gemma_seed: int
    gemma_output: str
    vanilla_output: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinate": self.coordinate,
            "subject": self.subject,
            "thread": self.thread,
            "turn": self.turn,
            "current_input": self.current_input,
            "active_context": list(self.active_context),
            "eligible_candidates": list(self.eligible_candidates),
            "normalized_distribution": list(self.normalized_distribution),
            "flatness": dict(self.flatness),
            "field_seed": self.field_seed,
            "random_draw": self.random_draw,
            "selected_landing": self.selected_landing,
            "propagated_neighborhood": list(self.propagated_neighborhood),
            "rendered_payload": self.rendered_payload,
            "gemma_seed": self.gemma_seed,
            "gemma_output": self.gemma_output,
            "vanilla_output": self.vanilla_output,
        }


def saa_contract(config: SAAConfig | None = None) -> dict[str, Any]:
    """Return the canonical prospective contract without touching providers."""

    chosen = config or SAAConfig()
    return {
        "name": EXPERIMENT,
        "contract_revision": CONTRACT_REVISION,
        "mode": SAA_VERSION,
        "historical_evidence_unchanged": True,
        "architecture": {
            "C": "vanilla/no MNEME influence",
            "SAA": "stochastic associative accessibility over earned graph pressure",
            "prior_F0": "preserved deterministic comparison only",
        },
        "model_stack": {
            "developing_host": "google/gemma-4-E4B-it (local MSI, pinned existing runtime)",
            "extractor": "GLiNER2.5 (local MSI, pinned existing runtime)",
            "semantic_assessor": "cross-encoder/nli-deberta-v3-xsmall",
            "interloper": "Qwen/Qwen3-30B-A3B",
            "no_provider_assessor_fallback": True,
        },
        "saa_config": chosen.to_dict(),
        "field_rng": {
            "algorithm": FIELD_RNG_ALGORITHM,
            "seed_schedule": list(FIELD_SEEDS),
            "independent_from": [
                "Gemma generation seed",
                "Qwen generation",
                "run ID",
                "timestamp",
                "branch name",
                "filename",
                "database ordering",
            ],
        },
        "development": {
            "thread_count": len(THREAD_SCHEDULE),
            "threads_1_to_9": [item.to_dict() for item in THREAD_SCHEDULE[:9]],
            "thread_10": THREAD_SCHEDULE[9].to_dict(),
            "target_turns_per_thread": DEVELOPMENT_TURNS_TARGET,
            "runway_bounds": {
                "minimum": DEVELOPMENT_TURNS_MIN,
                "maximum": DEVELOPMENT_TURNS_MAX,
            },
            "fresh_context_at_boundaries": True,
            "shared_interloper": True,
            "target_associations": [],
        },
        "measurement": {
            "readout_probes": list(READOUT_PROBES),
            "readout_repetitions": READOUT_REPETITIONS,
            "gemma_seeds": list(GEMMA_READOUT_SEEDS),
            "thread_10_initial_readout_only": True,
            "learn_from_thread_10_after_primary_measurement": True,
            "removal_restoration": ["SAA_ON", "SAA_OFF", "SAA_RESTORED"],
            "consequence_subtest": {
                "enabled": True,
                "feedback_types": ["positive_external", "negative_external"],
                "global_concept_mutation": False,
            },
            "sibling_different_history": "deferred_unless_bounded_without_scope_explosion",
        },
        "evidence": {
            "field_trace_schema": "saa-field-trace-v1",
            "complete_transcripts": True,
            "machine_readable": True,
            "raw_graph_provenance_hidden_from_host": True,
            "null_output": "hard_stop_invalid_instrumentation",
        },
    }


def validate_saa_contract(contract: dict[str, Any]) -> None:
    """Validate invariants that must hold before any live execution."""

    if contract.get("name") != EXPERIMENT or contract.get("mode") != SAA_VERSION:
        raise ValueError("unexpected SAA contract identity")
    development = contract.get("development")
    if not isinstance(development, dict) or development.get("thread_count") != 10:
        raise ValueError("SAA requires exactly ten frozen threads")
    threads = development.get("threads_1_to_9")
    thread_10 = development.get("thread_10")
    if not isinstance(threads, list) or len(threads) != 9 or not isinstance(thread_10, dict):
        raise ValueError("SAA thread schedule is incomplete")
    all_ids = [str(item.get("thread_id")) for item in threads] + [str(thread_10.get("thread_id"))]
    if len(set(all_ids)) != 10 or all_ids[-1] != "T10":
        raise ValueError("thread IDs must be unique with T10 last")
    if any(int(item.get("target_turns", 0)) < DEVELOPMENT_TURNS_MIN for item in threads):
        raise ValueError("developmental runway is below the minimum")
    seeds = contract.get("field_rng", {}).get("seed_schedule")
    if seeds != list(FIELD_SEEDS):
        raise ValueError("field seed schedule drifted")
    measurement = contract.get("measurement", {})
    if measurement.get("readout_repetitions") != READOUT_REPETITIONS:
        raise ValueError("readout repetition count drifted")


def validate_field_trace(trace: SAAFieldTrace) -> None:
    """Reject incomplete or host-leaking SAA evidence records."""

    if not trace.current_input.strip() or not trace.gemma_output.strip():
        raise ValueError("field traces require nonempty input and Gemma output")
    if trace.field_seed < 0 or trace.gemma_seed < 0:
        raise ValueError("seeds must be nonnegative")
    forbidden = ("provenance", "graph_id", "treatment", "learner score")
    payload = trace.rendered_payload.casefold()
    if any(item in payload for item in forbidden):
        raise ValueError("SAA host payload contains audit metadata")


def emit_plan(path: Path) -> dict[str, Any]:
    """Write a canonical offline plan; this function performs no live calls."""

    contract = saa_contract()
    validate_saa_contract(contract)
    payload = {
        "contract": contract,
        "contract_sha256": _canonical_digest(contract),
        "status": "FROZEN_OFFLINE_PLAN",
        "provider_calls_made": 0,
        "local_model_calls_made": 0,
        "historical_evidence_unchanged": True,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _canonical_digest(value: Any) -> str:
    import hashlib

    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-plan", type=Path, help="write the offline frozen SAA contract")
    args = parser.parse_args(argv)
    if args.emit_plan is None:
        parser.error("this contract scaffold performs no live calls; pass --emit-plan PATH")
    payload = emit_plan(args.emit_plan)
    print(json.dumps({"status": payload["status"], "path": str(args.emit_plan), "provider_calls": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
