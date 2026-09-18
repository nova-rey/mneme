"""P0.3 experiment contracts and fixture validation."""

from .artifacts import ArtifactError, ArtifactStore, PublishedRun
from .baseline import (
    BaselineError,
    BaselineObservation,
    BaselineReport,
    build_baseline_report,
    measure_baseline,
    render_baseline_report,
)
from .contracts import (
    EXPERIMENT_SCHEMA_VERSION,
    ContractError,
    ExperimentIdentity,
    ExperimentSpec,
    canonical_json,
    load_spec,
)
from .datasets import (
    DatasetBoundaryError,
    DatasetRecord,
    FixturePack,
    load_fixture_pack,
    load_jsonl,
    validate_split_boundaries,
)
from .evaluation import EvaluationError, FrozenEvaluationView, run_isolation_check

__all__ = [
    "EXPERIMENT_SCHEMA_VERSION",
    "ContractError",
    "DatasetBoundaryError",
    "DatasetRecord",
    "ExperimentIdentity",
    "ExperimentSpec",
    "EvaluationError",
    "FixturePack",
    "FrozenEvaluationView",
    "canonical_json",
    "load_fixture_pack",
    "load_jsonl",
    "load_spec",
    "run_isolation_check",
    "BaselineError",
    "BaselineObservation",
    "BaselineReport",
    "build_baseline_report",
    "measure_baseline",
    "render_baseline_report",
    "validate_split_boundaries",
    "ArtifactError",
    "ArtifactStore",
    "PublishedRun",
]
