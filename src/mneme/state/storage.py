"""Explicit SQLite storage for MNEME P0.2's durable accepted history."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import sqlite3
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from .contracts import (
    ArtifactKind,
    StoragePermissions,
    accepted_history_digest,
    canonical_digest,
    new_id,
    validate_id,
)

SCHEMA_VERSION = 11
APPLICATION_ID = 0x4D4E454D  # ASCII "MNEM"

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS store_info (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  schema_version INTEGER NOT NULL,
  record_version INTEGER NOT NULL,
  artifact_kind TEXT NOT NULL CHECK (artifact_kind IN ('working','checkpoint')),
  active_instance_id TEXT,
  created_by_version TEXT NOT NULL,
  revocation_ledger_path TEXT
);
CREATE TABLE IF NOT EXISTS lineages (
  instance_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  self_ref_id TEXT NOT NULL UNIQUE,
  parent_instance_id TEXT REFERENCES lineages(instance_id),
  fork_checkpoint_id TEXT,
  fork_manifest_id TEXT
);
CREATE TABLE IF NOT EXISTS policies (
  policy_id TEXT PRIMARY KEY,
  scope_id TEXT NOT NULL,
  storage_allowed INTEGER NOT NULL CHECK (storage_allowed IN (0,1)),
  export_allowed INTEGER NOT NULL CHECK (export_allowed IN (0,1)),
  interpretation_allowed INTEGER NOT NULL DEFAULT 0 CHECK (interpretation_allowed IN (0,1)),
  recall_allowed INTEGER NOT NULL DEFAULT 0 CHECK (recall_allowed IN (0,1)),
  provider_reuse_allowed INTEGER NOT NULL DEFAULT 0 CHECK (provider_reuse_allowed IN (0,1)),
  learning_allowed INTEGER NOT NULL DEFAULT 0 CHECK (learning_allowed IN (0,1)),
  policy_version INTEGER NOT NULL,
  bound_host_ref TEXT,
  bound_host_fingerprint_json TEXT
);
CREATE TABLE IF NOT EXISTS host_records (
  host_ref TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  model_id TEXT NOT NULL,
  model_revision TEXT,
  runtime TEXT NOT NULL,
  fingerprint_json TEXT NOT NULL,
  canonical_digest TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS manifests (
  manifest_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision >= 0),
  parent_manifest_id TEXT REFERENCES manifests(manifest_id),
  inherited_base_manifest_id TEXT REFERENCES manifests(manifest_id),
  policy_id TEXT NOT NULL REFERENCES policies(policy_id),
  self_ref_id TEXT NOT NULL,
  format_version INTEGER NOT NULL,
  controller_version TEXT NOT NULL,
  integrity_digest TEXT NOT NULL,
  accepted_history_digest TEXT NOT NULL,
  graph_snapshot_id TEXT,
  graph_revision INTEGER NOT NULL DEFAULT 0 CHECK (graph_revision >= 0),
  accepted_episode_count INTEGER NOT NULL DEFAULT 0 CHECK (accepted_episode_count >= 0),
  self_view_id TEXT,
  self_view_version INTEGER NOT NULL DEFAULT 0 CHECK (self_view_version >= 0),
  learner_snapshot_id TEXT,
  learner_configuration_digest TEXT,
  binding_version INTEGER,
  opportunity INTEGER CHECK (opportunity IS NULL OR opportunity >= 0),
  coverage_json TEXT,
  authority_revision INTEGER CHECK (authority_revision IS NULL OR authority_revision >= 0),
  UNIQUE(instance_id, revision),
  FOREIGN KEY(instance_id) REFERENCES lineages(instance_id)
);
CREATE TABLE IF NOT EXISTS run_manifests (
  run_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  pinned_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  host_ref TEXT NOT NULL REFERENCES host_records(host_ref),
  policy_id TEXT NOT NULL REFERENCES policies(policy_id),
  experiment_ref TEXT,
  controller_version TEXT NOT NULL,
  context_mode TEXT NOT NULL,
  seed INTEGER,
  rng_plan_version TEXT,
  request_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operations (
  operation_id TEXT PRIMARY KEY,
  episode_id TEXT NOT NULL UNIQUE,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  base_revision INTEGER NOT NULL CHECK (base_revision >= 0),
  run_id TEXT NOT NULL UNIQUE REFERENCES run_manifests(run_id),
  intent_digest TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PREPARED','STARTED','RESULT_READY','ACCEPTED','UNCERTAIN','ABANDONED')),
  generation_id TEXT,
  request_json TEXT,
  failure_code TEXT,
  supersedes_operation_id TEXT REFERENCES operations(operation_id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL REFERENCES operations(operation_id),
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  role TEXT NOT NULL,
  supplier TEXT NOT NULL,
  content TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  UNIQUE(operation_id, ordinal)
);
CREATE TABLE IF NOT EXISTS generation_records (
  generation_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL UNIQUE REFERENCES operations(operation_id),
  host_ref TEXT NOT NULL REFERENCES host_records(host_ref),
  output_source_id TEXT NOT NULL UNIQUE REFERENCES sources(source_id),
  returned_model TEXT NOT NULL,
  returned_provider TEXT NOT NULL,
  effective_parameters_json TEXT NOT NULL,
  usage_json TEXT,
  latency_ms REAL NOT NULL,
  finish_reason TEXT,
  provider_evidence_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS episodes (
  episode_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL UNIQUE REFERENCES operations(operation_id),
  origin_instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  accepted_revision INTEGER NOT NULL CHECK (accepted_revision > 0),
  generation_id TEXT UNIQUE REFERENCES generation_records(generation_id),
  occurred_at TEXT NOT NULL,
  accepted_at TEXT NOT NULL,
  UNIQUE(origin_instance_id, accepted_revision)
);
CREATE TABLE IF NOT EXISTS revisions (
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  revision INTEGER NOT NULL CHECK (revision >= 0),
  previous_revision INTEGER CHECK (previous_revision IS NULL OR previous_revision >= 0),
  event_id TEXT NOT NULL UNIQUE,
  event_kind TEXT NOT NULL,
  episode_id TEXT UNIQUE REFERENCES episodes(episode_id),
  manifest_id TEXT UNIQUE REFERENCES manifests(manifest_id),
  accepted_at TEXT NOT NULL,
  PRIMARY KEY(instance_id, revision)
);
CREATE TABLE IF NOT EXISTS current_state (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  active_instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  current_revision INTEGER NOT NULL CHECK (current_revision >= 0),
  current_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id)
);
CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  source_instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  source_revision INTEGER NOT NULL CHECK (source_revision >= 0),
  source_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  created_at TEXT NOT NULL,
  format_version INTEGER NOT NULL,
  integrity_digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interpretation_operations (
  operation_id TEXT PRIMARY KEY,
  episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  base_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  status TEXT NOT NULL CHECK (status IN ('PREPARED','STARTED','RESULT_READY','ACCEPTED','FAILED','UNCERTAIN','ABANDONED')),
  current_attempt INTEGER NOT NULL DEFAULT 0 CHECK (current_attempt >= 0),
  configuration_digest TEXT NOT NULL,
  failure_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interpretation_attempts (
  operation_id TEXT NOT NULL REFERENCES interpretation_operations(operation_id),
  attempt INTEGER NOT NULL CHECK (attempt >= 0),
  host_ref TEXT REFERENCES host_records(host_ref),
  request_json TEXT NOT NULL,
  result_json TEXT,
  status TEXT NOT NULL CHECK (status IN ('STARTED','RESULT_READY','VALID','INVALID','UNCERTAIN')),
  validation_errors_json TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (operation_id, attempt)
);
CREATE TABLE IF NOT EXISTS interpretations (
  interpretation_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL UNIQUE REFERENCES interpretation_operations(operation_id),
  episode_id TEXT NOT NULL UNIQUE REFERENCES episodes(episode_id),
  schema_version INTEGER NOT NULL,
  extractor_version TEXT NOT NULL,
  resolver_version TEXT NOT NULL,
  accepted_revision INTEGER NOT NULL CHECK (accepted_revision >= 0),
  accepted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidates (
  candidate_id TEXT PRIMARY KEY,
  interpretation_id TEXT NOT NULL REFERENCES interpretations(interpretation_id),
  local_key TEXT NOT NULL,
  label TEXT NOT NULL,
  normalized_label TEXT NOT NULL,
  kind TEXT NOT NULL,
  confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  salience REAL NOT NULL CHECK (salience >= 0 AND salience <= 1),
  context_json TEXT NOT NULL,
  UNIQUE(interpretation_id, local_key)
);
CREATE TABLE IF NOT EXISTS evidence_spans (
  candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  source_slot TEXT NOT NULL,
  start_offset INTEGER NOT NULL CHECK (start_offset >= 0),
  end_offset INTEGER NOT NULL CHECK (end_offset > start_offset),
  text_digest TEXT NOT NULL,
  PRIMARY KEY (candidate_id, ordinal)
);
CREATE TABLE IF NOT EXISTS resolution_decisions (
  decision_id TEXT PRIMARY KEY,
  interpretation_id TEXT NOT NULL REFERENCES interpretations(interpretation_id),
  local_key TEXT NOT NULL,
  canonical_label TEXT NOT NULL,
  normalized_label TEXT NOT NULL,
  decision_kind TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(interpretation_id, local_key)
);
CREATE TABLE IF NOT EXISTS graph_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  lineage_revision INTEGER NOT NULL CHECK (lineage_revision >= 0),
  graph_revision INTEGER NOT NULL CHECK (graph_revision >= 0),
  parent_snapshot_id TEXT REFERENCES graph_snapshots(snapshot_id),
  content_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(instance_id, graph_revision)
);
CREATE TABLE IF NOT EXISTS graph_concepts (
  snapshot_id TEXT NOT NULL REFERENCES graph_snapshots(snapshot_id),
  concept_key TEXT NOT NULL,
  label TEXT NOT NULL,
  normalized_label TEXT NOT NULL,
  kind TEXT NOT NULL,
  confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  salience REAL NOT NULL CHECK (salience >= 0 AND salience <= 1),
  candidate_id TEXT REFERENCES candidates(candidate_id),
  PRIMARY KEY (snapshot_id, concept_key)
);
CREATE TABLE IF NOT EXISTS graph_edges (
  snapshot_id TEXT NOT NULL REFERENCES graph_snapshots(snapshot_id),
  edge_key TEXT NOT NULL,
  source_key TEXT NOT NULL,
  target_key TEXT NOT NULL,
  relationship TEXT NOT NULL,
  polarity TEXT NOT NULL,
  context_json TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, edge_key)
);
CREATE TABLE IF NOT EXISTS graph_routes (
  snapshot_id TEXT NOT NULL REFERENCES graph_snapshots(snapshot_id),
  route_key TEXT NOT NULL,
  edge_keys_json TEXT NOT NULL,
  source_json TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, route_key)
);
CREATE TABLE IF NOT EXISTS source_bindings (
  source_id TEXT PRIMARY KEY REFERENCES sources(source_id),
  purpose TEXT NOT NULL CHECK (purpose IN ('external_evidence','model_output','controller_dependency','replayed_context','tool_result','feedback')),
  origin_source_id TEXT REFERENCES sources(source_id),
  permission_scope TEXT,
  independent_evidence INTEGER NOT NULL CHECK (independent_evidence IN (0,1)),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS identity_events (
  event_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  event_kind TEXT NOT NULL CHECK (event_kind IN ('adopt','alias','supersede')),
  name TEXT,
  alias TEXT,
  source_json TEXT NOT NULL,
  accepted_revision INTEGER NOT NULL CHECK (accepted_revision >= 0),
  self_view_version INTEGER NOT NULL CHECK (self_view_version >= 0),
  supersedes_event_id TEXT REFERENCES identity_events(event_id),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS identity_generation_records (
  generation_id TEXT PRIMARY KEY,
  identity_event_id TEXT NOT NULL UNIQUE REFERENCES identity_events(event_id),
  host_ref TEXT NOT NULL REFERENCES host_records(host_ref),
  request_json TEXT NOT NULL,
  result_json TEXT NOT NULL,
  returned_model TEXT NOT NULL,
  returned_provider TEXT NOT NULL,
  effective_parameters_json TEXT NOT NULL,
  usage_json TEXT,
  latency_ms REAL NOT NULL,
  finish_reason TEXT,
  provider_evidence_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS identity_generation_attempts (
  attempt_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  host_ref TEXT NOT NULL REFERENCES host_records(host_ref),
  request_json TEXT NOT NULL,
  result_json TEXT,
  returned_model TEXT,
  returned_provider TEXT,
  effective_parameters_json TEXT,
  usage_json TEXT,
  latency_ms REAL,
  finish_reason TEXT,
  provider_evidence_json TEXT,
  status TEXT NOT NULL CHECK (status IN ('STARTED','RESULT_READY','ACCEPTED','INVALID','UNCERTAIN')),
  validation_errors_json TEXT NOT NULL,
  identity_event_id TEXT UNIQUE REFERENCES identity_events(event_id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS self_views (
  self_view_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  version INTEGER NOT NULL CHECK (version >= 0),
  name TEXT,
  name_event_id TEXT REFERENCES identity_events(event_id),
  content_json TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(instance_id, version)
);
CREATE TABLE IF NOT EXISTS correction_directives (
  directive_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  target_route_id TEXT,
  expression_type TEXT,
  context_tag TEXT,
  scope TEXT NOT NULL CHECK (scope IN ('until_revoked')),
  status TEXT NOT NULL CHECK (status IN ('ACTIVE','REVOKED')),
  source_json TEXT NOT NULL,
  accepted_revision INTEGER NOT NULL CHECK (accepted_revision >= 0),
  superseded_by TEXT REFERENCES correction_directives(directive_id),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS declarations (
  declaration_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  declaration_json TEXT NOT NULL,
  source_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PROPOSED','ACCEPTED','REVOKED')),
  accepted_revision INTEGER NOT NULL CHECK (accepted_revision >= 0),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS turn_traces (
  trace_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  operation_id TEXT UNIQUE REFERENCES operations(operation_id),
  pinned_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  mode TEXT NOT NULL,
  treatment TEXT NOT NULL,
  query_json TEXT NOT NULL,
  considered_json TEXT NOT NULL,
  selected_json TEXT NOT NULL,
  suppressed_json TEXT NOT NULL,
  applied_json TEXT NOT NULL,
  request_json TEXT NOT NULL,
  context_truncated INTEGER NOT NULL CHECK (context_truncated IN (0,1)),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS development_operations (
  operation_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  episode_id TEXT NOT NULL UNIQUE REFERENCES episodes(episode_id),
  base_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  opportunity INTEGER NOT NULL CHECK (opportunity >= 1),
  stage TEXT NOT NULL,
  terminal_disposition TEXT,
  configuration_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS modeled_advance_operations (
  operation_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  base_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  context TEXT NOT NULL,
  steps INTEGER NOT NULL CHECK (steps > 0),
  target_json TEXT NOT NULL,
  opportunity INTEGER NOT NULL CHECK (opportunity >= 1),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS semantic_bindings (
  binding_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  interpretation_id TEXT NOT NULL REFERENCES interpretations(interpretation_id),
  candidate_id TEXT REFERENCES candidates(candidate_id),
  local_key TEXT NOT NULL,
  canonical_key TEXT NOT NULL,
  canonical_label TEXT NOT NULL,
  resolver_version TEXT NOT NULL,
  binding_version INTEGER NOT NULL CHECK (binding_version >= 1),
  source_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS development_observations (
  observation_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL REFERENCES development_operations(operation_id),
  binding_id TEXT REFERENCES semantic_bindings(binding_id),
  edge_key TEXT NOT NULL,
  context TEXT NOT NULL,
  source_role TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('present','absent','unknown')),
  dependence TEXT NOT NULL,
  dependence_group TEXT,
  covered INTEGER NOT NULL CHECK (covered IN (0,1)),
  actual_exposure INTEGER NOT NULL CHECK (actual_exposure IN (0,1)),
  evidence_json TEXT NOT NULL,
  credit_reason TEXT,
  arc_id TEXT REFERENCES conversation_arcs(arc_id),
  arc_reentry INTEGER NOT NULL DEFAULT 0 CHECK (arc_reentry IN (0,1)),
  reentry_initiator TEXT CHECK (reentry_initiator IS NULL OR reentry_initiator IN ('external','model','mneme','unknown')),
  reentry_origin_arc_id TEXT REFERENCES conversation_arcs(arc_id),
  refractory_active INTEGER NOT NULL DEFAULT 0 CHECK (refractory_active IN (0,1)),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learner_updates (
  update_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL REFERENCES development_operations(operation_id),
  application_key TEXT NOT NULL UNIQUE,
  opportunity INTEGER NOT NULL CHECK (opportunity >= 1),
  edge_key TEXT NOT NULL,
  context TEXT NOT NULL,
  delta INTEGER NOT NULL,
  reason TEXT NOT NULL,
  before_json TEXT NOT NULL,
  after_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learner_values (
  value_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  update_id TEXT NOT NULL REFERENCES learner_updates(update_id),
  edge_key TEXT NOT NULL,
  context TEXT NOT NULL,
  accessibility INTEGER NOT NULL CHECK (accessibility BETWEEN 0 AND 1000000),
  support INTEGER NOT NULL CHECK (support BETWEEN 0 AND 1000000),
  consequence INTEGER NOT NULL CHECK (consequence BETWEEN -250000 AND 250000),
  lifetime_credit INTEGER NOT NULL CHECK (lifetime_credit BETWEEN 0 AND 1000000),
  induced_credit INTEGER NOT NULL CHECK (induced_credit BETWEEN 0 AND 1000000),
  rolling_credit INTEGER NOT NULL CHECK (rolling_credit BETWEEN 0 AND 1000000),
  last_consolidation_opportunity INTEGER,
  inactivity_ticks INTEGER NOT NULL CHECK (inactivity_ticks >= 0),
  opportunity INTEGER NOT NULL CHECK (opportunity >= 1),
  content_digest TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learner_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  base_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  opportunity INTEGER NOT NULL CHECK (opportunity >= 0),
  learner_version TEXT NOT NULL,
  configuration_json TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS development_assessor_attempts (
  operation_id TEXT NOT NULL REFERENCES development_operations(operation_id),
  attempt INTEGER NOT NULL CHECK (attempt >= 0),
  request_json TEXT NOT NULL,
  result_json TEXT,
  usage_json TEXT,
  status TEXT NOT NULL CHECK (status IN ('STARTED','RESULT_READY','VALID','INVALID','UNCERTAIN')),
  validation_errors_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(operation_id, attempt)
);
CREATE TABLE IF NOT EXISTS outcome_assessments (
  assessment_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  operation_id TEXT REFERENCES development_operations(operation_id),
  target_route_id TEXT NOT NULL,
  context TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('known','unknown')),
  direction INTEGER NOT NULL CHECK (direction IN (-1,1)),
  exposure_id TEXT,
  relevant INTEGER NOT NULL CHECK (relevant IN (0,1)),
  evidence_json TEXT NOT NULL,
  source_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACCEPTED','REJECTED','RETRACTED','UNCERTAIN')),
  authority_revision INTEGER NOT NULL CHECK (authority_revision >= 0),
  supersedes_assessment_id TEXT REFERENCES outcome_assessments(assessment_id),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quarantine_events (
  event_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  target_kind TEXT NOT NULL CHECK (target_kind IN ('concept','edge','route','interpretation','source','checkpoint','cache','lineage')),
  target_id TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('ADD','RELEASE')),
  reason TEXT NOT NULL,
  source_json TEXT NOT NULL,
  authority_revision INTEGER NOT NULL CHECK (authority_revision >= 1),
  supersedes_event_id TEXT REFERENCES quarantine_events(event_id),
  created_at TEXT NOT NULL,
  UNIQUE(instance_id, authority_revision)
);
CREATE TABLE IF NOT EXISTS identity_review_operations (
  review_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  base_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  operation_key TEXT NOT NULL UNIQUE,
  proposal_json TEXT NOT NULL,
  stage TEXT NOT NULL CHECK (stage IN ('PREPARED','STARTED','RESULT_READY','ACCEPTED','REJECTED','UNCHANGED','UNCERTAIN')),
  decision_json TEXT,
  accepted_revision INTEGER,
  authority_revision INTEGER NOT NULL CHECK (authority_revision >= 0),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS identity_review_attempts (
  review_id TEXT NOT NULL REFERENCES identity_review_operations(review_id),
  attempt INTEGER NOT NULL CHECK (attempt >= 0),
  request_json TEXT NOT NULL,
  result_json TEXT,
  usage_json TEXT,
  host_ref TEXT,
  status TEXT NOT NULL CHECK (status IN ('STARTED','RESULT_READY','VALID','INVALID','UNCERTAIN')),
  validation_errors_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(review_id, attempt)
);
CREATE TABLE IF NOT EXISTS conversation_arcs (
  arc_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  conversation_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  start_turn INTEGER NOT NULL CHECK (start_turn >= 0),
  end_turn INTEGER NOT NULL CHECK (end_turn >= start_turn),
  start_episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
  initiation_role TEXT NOT NULL CHECK (initiation_role IN ('external','model','mneme','unknown')),
  topic_keys_json TEXT NOT NULL,
  source_roles_json TEXT NOT NULL,
  outcome_keys_json TEXT NOT NULL,
  boundary_version TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(instance_id, conversation_id, ordinal)
);
CREATE TABLE IF NOT EXISTS conversation_arc_members (
  arc_id TEXT NOT NULL REFERENCES conversation_arcs(arc_id),
  episode_id TEXT NOT NULL UNIQUE REFERENCES episodes(episode_id),
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  conversation_id TEXT NOT NULL,
  turn_index INTEGER NOT NULL CHECK (turn_index >= 0),
  topic_keys_json TEXT NOT NULL,
  topic_status TEXT NOT NULL CHECK (topic_status IN ('known','empty','unknown')),
  assignment_reason TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(instance_id, conversation_id, turn_index)
);
CREATE TABLE IF NOT EXISTS conversation_arc_events (
  event_id TEXT PRIMARY KEY,
  arc_id TEXT NOT NULL REFERENCES conversation_arcs(arc_id),
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  conversation_id TEXT NOT NULL,
  turn_index INTEGER NOT NULL CHECK (turn_index >= 0),
  event_kind TEXT NOT NULL CHECK (event_kind IN ('OPEN','CLOSE','REENTRY')),
  initiator_role TEXT CHECK (initiator_role IS NULL OR initiator_role IN ('external','model','mneme','unknown')),
  prior_arc_id TEXT REFERENCES conversation_arcs(arc_id),
  closure_reason TEXT,
  refractory_expires_after_turn INTEGER,
  details_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""

# Additive portion used by the explicit v1 -> v2 migration.  It is derived
# from the same schema declaration so new stores and migrated stores receive
# identical interpretation/graph tables.
_SCHEMA_V3_TABLES = _SCHEMA[
    _SCHEMA.index("CREATE TABLE IF NOT EXISTS identity_events") : _SCHEMA.index(
        "CREATE TABLE IF NOT EXISTS development_operations"
    )
]
_SCHEMA_V2_TABLES = _SCHEMA[
    _SCHEMA.index("CREATE TABLE IF NOT EXISTS interpretation_operations") : _SCHEMA.index(
        "CREATE TABLE IF NOT EXISTS identity_events"
    )
]
_SCHEMA_V6_TABLES = _SCHEMA[
    _SCHEMA.index("CREATE TABLE IF NOT EXISTS development_operations") : _SCHEMA.index(
        "CREATE TABLE IF NOT EXISTS outcome_assessments"
    )
]
_SCHEMA_V7_TABLES = _SCHEMA[
    _SCHEMA.index("CREATE TABLE IF NOT EXISTS outcome_assessments") : _SCHEMA.index(
        "CREATE TABLE IF NOT EXISTS conversation_arcs"
    )
]
_SCHEMA_V11_TABLES = _SCHEMA[_SCHEMA.index("CREATE TABLE IF NOT EXISTS conversation_arcs") :]

_IMMUTABLE = (
    "lineages",
    "policies",
    "host_records",
    "manifests",
    "run_manifests",
    "sources",
    "generation_records",
    "episodes",
    "revisions",
    "checkpoints",
    "interpretations",
    "candidates",
    "evidence_spans",
    "resolution_decisions",
    "graph_snapshots",
    "graph_concepts",
    "graph_edges",
    "graph_routes",
    "source_bindings",
    "identity_events",
    "identity_generation_records",
    "self_views",
    "correction_directives",
    "declarations",
    "turn_traces",
    "semantic_bindings",
    "development_observations",
    "modeled_advance_operations",
    "learner_updates",
    "learner_values",
    "learner_snapshots",
    "outcome_assessments",
    "quarantine_events",
    "conversation_arcs",
    "conversation_arc_members",
    "conversation_arc_events",
)


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class SchemaError(RuntimeError):
    """The database is not a supported MNEME store."""


class SQLiteStore:
    """One working lineage database, with explicit transaction boundaries."""

    def __init__(
        self,
        path: str | Path,
        *,
        read_only: bool = False,
        _allow_published_checkpoint_write: bool = False,
    ) -> None:
        self.path = Path(path)
        self.read_only = read_only
        if read_only:
            uri = f"file:{self.path.resolve()}?mode=ro"
            self.connection = sqlite3.connect(uri, uri=True, isolation_level=None)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            existed = self.path.exists() and self.path.stat().st_size > 0
            self.connection = sqlite3.connect(self.path, isolation_level=None)
            if not existed:
                self.connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
            # Reassert the approved durable working-store settings on every
            # writable open; SQLite PRAGMAs are connection-local.
            self.connection.execute("PRAGMA journal_mode = DELETE")
            self.connection.execute("PRAGMA synchronous = EXTRA")
            self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        if (
            not read_only
            and not self.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='store_info'"
            ).fetchone()
        ):
            self._initialize()
        self._check_schema()
        artifact = self.connection.execute("SELECT artifact_kind FROM store_info").fetchone()
        if (
            not read_only
            and artifact is not None
            and artifact[0] == ArtifactKind.CHECKPOINT
            and not _allow_published_checkpoint_write
        ):
            self.connection.close()
            raise SchemaError(
                "published checkpoint is read-only; fork it or open it through a checkpoint reader"
            )

    @classmethod
    def _open_checkpoint_for_fork(cls, path: str | Path) -> SQLiteStore:
        """Open a copied checkpoint during the private fork conversion step.

        Published checkpoints remain non-writable through the normal constructor.
        Forking first copies one, then atomically converts that private copy into a
        working store before inserting the child lineage.
        """

        return cls(path, _allow_published_checkpoint_write=True)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> SQLiteStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextlib.contextmanager
    def transaction(self, *, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        if self.read_only:
            raise sqlite3.OperationalError("read-only store")
        with self.writer_lock():
            self.connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            try:
                yield self.connection
            except BaseException:
                self.connection.rollback()
                raise
            else:
                self.connection.commit()

    @contextlib.contextmanager
    def writer_lock(self) -> Iterator[None]:
        if self.read_only:
            raise sqlite3.OperationalError("read-only store")
        lock_path = self.path.parent / "writer.lock"
        with lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _initialize(self) -> None:
        with self.transaction():
            self.connection.executescript(_SCHEMA)
            self.connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            for table in _IMMUTABLE:
                self.connection.executescript(
                    f"CREATE TRIGGER IF NOT EXISTS {table}_immutable_update "
                    f"BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable record'); END; "
                    f"CREATE TRIGGER IF NOT EXISTS {table}_immutable_delete "
                    f"BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable record'); END;"
                )

    def _check_schema(self) -> None:
        row = self.connection.execute("PRAGMA user_version").fetchone()
        version = int(row[0]) if row else 0
        if version > SCHEMA_VERSION:
            raise SchemaError(f"unsupported newer schema version {version}")
        if self.read_only and version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}:
            # Historical Phase Zero checkpoints remain inspectable without
            # mutation.  Forking a v1 checkpoint stages and explicitly
            # migrates a private copy before opening it writable.
            if info := self.connection.execute("SELECT schema_version FROM store_info").fetchone():
                if int(info[0]) == version:
                    return
        if version != SCHEMA_VERSION:
            if version < SCHEMA_VERSION:
                raise SchemaError(
                    f"schema version {version} requires explicit migration to {SCHEMA_VERSION}"
                )
            raise SchemaError(f"unsupported schema version {version}; expected {SCHEMA_VERSION}")
        info = self.connection.execute("SELECT schema_version FROM store_info").fetchone()
        if info is not None and int(info[0]) != SCHEMA_VERSION:
            raise SchemaError("store_info schema version disagrees with PRAGMA user_version")

    @staticmethod
    def migrate(
        path: str | Path,
        *,
        target_version: int = SCHEMA_VERSION,
        backup: str | Path | None = None,
    ) -> None:
        """Explicitly migrate a v1 store to the P1.1 schema.

        Opening an older store never mutates it.  The backup is made before the
        migration transaction and remains available if the process is
        interrupted or validation fails.
        """

        if target_version not in {2, 3, 4, 5, 6, 7, 8, 9, 10, SCHEMA_VERSION}:
            raise SchemaError(
                f"only migration to schema 2, 3, 4, 5, 6, 7, 8, 9, 10 or {SCHEMA_VERSION} is supported"
            )
        source = Path(path)
        if not source.is_file():
            raise SchemaError(f"store does not exist: {source}")
        backup_path = (
            Path(backup) if backup is not None else source.with_suffix(source.suffix + ".pre-v2")
        )
        if backup_path.exists():
            raise SchemaError(f"migration backup already exists: {backup_path}")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup_path)
        raw = sqlite3.connect(source, isolation_level=None)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA foreign_keys = ON")
        try:
            version_row = raw.execute("PRAGMA user_version").fetchone()
            version = int(version_row[0]) if version_row else 0
            if version == target_version:
                raise SchemaError("store is already at the requested schema version")
            if version not in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10} or version > target_version:
                raise SchemaError(f"cannot migrate unsupported schema version {version}")
            info = raw.execute("SELECT schema_version FROM store_info").fetchone()
            if info is None or int(info[0]) != version:
                raise SchemaError("store_info schema version is missing or inconsistent")
            # Foreign-key enforcement must be disabled before BEGIN; SQLite
            # ignores a toggle made while a transaction is active.  The
            # rebuilt tables retain the same references and are checked again
            # when the migrated store is reopened.
            raw.execute("PRAGMA foreign_keys = OFF")
            raw.execute("BEGIN IMMEDIATE")
            def has_column(table: str, column: str) -> bool:
                return any(
                    str(item[1]) == column
                    for item in raw.execute(f'PRAGMA table_info("{table}")').fetchall()
                )

            if version == 1 and target_version >= 2:
                raw.execute("ALTER TABLE manifests ADD COLUMN graph_snapshot_id TEXT")
                raw.execute(
                    "ALTER TABLE manifests ADD COLUMN graph_revision INTEGER NOT NULL DEFAULT 0"
                )
                policy_table = raw.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='policies'"
                ).fetchone()
                if policy_table is not None:
                    raw.execute(
                        "ALTER TABLE policies ADD COLUMN interpretation_allowed INTEGER NOT NULL DEFAULT 0"
                    )
                for statement in _SCHEMA_V2_TABLES.split(";"):
                    statement = statement.strip()
                    if statement:
                        raw.execute(statement)
                raw.execute(
                    "UPDATE store_info SET schema_version=2,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 2")
                version = 2
            if version == 2 and target_version >= 3:
                raw.execute(
                    "ALTER TABLE manifests ADD COLUMN accepted_episode_count INTEGER NOT NULL DEFAULT 0"
                )
                raw.execute("ALTER TABLE manifests ADD COLUMN self_view_id TEXT")
                raw.execute(
                    "ALTER TABLE manifests ADD COLUMN self_view_version INTEGER NOT NULL DEFAULT 0"
                )
                policy_table = raw.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='policies'"
                ).fetchone()
                if policy_table is not None:
                    raw.execute(
                        "ALTER TABLE policies ADD COLUMN recall_allowed INTEGER NOT NULL DEFAULT 0"
                    )
                    raw.execute(
                        "ALTER TABLE policies ADD COLUMN provider_reuse_allowed INTEGER NOT NULL DEFAULT 0"
                    )
                episodes_table = raw.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='episodes'"
                ).fetchone()
                if episodes_table is not None:
                    # The v3 counter is local to each lineage.  Existing v2
                    # manifests therefore derive it from accepted episodes
                    # owned by that lineage, while inherited history remains
                    # outside the child's local count.
                    raw.execute(
                        "UPDATE manifests AS m SET accepted_episode_count="
                        "(SELECT COUNT(*) FROM episodes e "
                        "WHERE e.origin_instance_id=m.instance_id "
                        "AND e.accepted_revision <= m.revision)"
                    )
                for statement in _SCHEMA_V3_TABLES.split(";"):
                    statement = statement.strip()
                    if statement:
                        raw.execute(statement)
                raw.execute(
                    "UPDATE store_info SET schema_version=3,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 3")
                version = 3
            if version == 3 and target_version >= 4:
                if not has_column("store_info", "revocation_ledger_path"):
                    raw.execute("ALTER TABLE store_info ADD COLUMN revocation_ledger_path TEXT")
                policy_table = raw.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='policies'"
                ).fetchone()
                if policy_table is not None:
                    if not has_column("policies", "bound_host_ref"):
                        raw.execute("ALTER TABLE policies ADD COLUMN bound_host_ref TEXT")
                    if not has_column("policies", "bound_host_fingerprint_json"):
                        raw.execute(
                            "ALTER TABLE policies ADD COLUMN bound_host_fingerprint_json TEXT"
                        )
                    # Legacy material never acquires Phase One reuse through
                    # migration.  An operator must issue an explicit grant
                    # against the newly established authority.
                    raw.execute("DROP TRIGGER IF EXISTS policies_immutable_update")
                    raw.execute(
                        "UPDATE policies SET interpretation_allowed=0,recall_allowed=0,"
                        "provider_reuse_allowed=0,policy_version=policy_version+1"
                    )
                legacy_ledger = str(
                    source.with_suffix(source.suffix + ".policy.jsonl").resolve()
                )
                raw.execute(
                    "UPDATE store_info SET revocation_ledger_path=?", (legacy_ledger,)
                )
                raw.execute(
                    "UPDATE store_info SET schema_version=4,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 4")
                version = 4
            if version == 4 and target_version >= 5:
                raw.execute(
                    "CREATE TABLE IF NOT EXISTS identity_generation_records ("
                    "generation_id TEXT PRIMARY KEY,"
                    "identity_event_id TEXT NOT NULL UNIQUE REFERENCES identity_events(event_id),"
                    "host_ref TEXT NOT NULL REFERENCES host_records(host_ref),"
                    "request_json TEXT NOT NULL,"
                    "result_json TEXT NOT NULL,"
                    "returned_model TEXT NOT NULL,"
                    "returned_provider TEXT NOT NULL,"
                    "effective_parameters_json TEXT NOT NULL,"
                    "usage_json TEXT,"
                    "latency_ms REAL NOT NULL,"
                    "finish_reason TEXT,"
                    "provider_evidence_json TEXT NOT NULL,"
                    "created_at TEXT NOT NULL"
                    ")"
                )
                raw.execute(
                    "UPDATE store_info SET schema_version=5,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 5")
                version = 5
            if version == 5 and target_version >= 6:
                policy_table = raw.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='policies'"
                ).fetchone()
                if policy_table is not None and not has_column("policies", "learning_allowed"):
                    raw.execute(
                        "ALTER TABLE policies ADD COLUMN learning_allowed INTEGER NOT NULL DEFAULT 0"
                    )
                for column, definition in (
                    ("learner_snapshot_id", "TEXT"),
                    ("learner_configuration_digest", "TEXT"),
                    ("binding_version", "INTEGER"),
                    ("opportunity", "INTEGER"),
                    ("coverage_json", "TEXT"),
                    ("authority_revision", "INTEGER"),
                ):
                    if not has_column("manifests", column):
                        raw.execute(f"ALTER TABLE manifests ADD COLUMN {column} {definition}")
                for statement in _SCHEMA_V6_TABLES.split(";"):
                    statement = statement.strip()
                    if statement:
                        raw.execute(statement)
                raw.execute(
                    "UPDATE store_info SET schema_version=6,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 6")
                version = 6
            if version == 6 and target_version >= 7:
                for statement in _SCHEMA_V7_TABLES.split(";"):
                    statement = statement.strip()
                    if statement:
                        raw.execute(statement)
                raw.execute(
                    "UPDATE store_info SET schema_version=7,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 7")
                version = 7
            if version == 7 and target_version >= 8:
                # v7 made one interpretation operation unique per episode.
                # A failed interpretation must remain immutable evidence while
                # an explicitly corrected extraction gets a new operation ID.
                # SQLite cannot drop that inline UNIQUE constraint, so rebuild
                # the small interpretation family in one explicit migration.
                # Keep foreign-key declarations in unrelated tables pointing
                # at the stable family names while the old tables are
                # temporarily renamed.  Without legacy ALTER semantics,
                # SQLite rewrites those declarations to the temporary names.
                raw.execute("PRAGMA legacy_alter_table = ON")
                family = (
                    "interpretation_operations",
                    "interpretation_attempts",
                    "interpretations",
                    "candidates",
                    "evidence_spans",
                    "resolution_decisions",
                    "semantic_bindings",
                )
                for table in family:
                    raw.execute(f'ALTER TABLE "{table}" RENAME TO "__v7_{table}"')
                for statement in (
                    """
                    CREATE TABLE interpretation_operations (
                      operation_id TEXT PRIMARY KEY,
                      episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
                      instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
                      base_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
                      status TEXT NOT NULL CHECK (status IN ('PREPARED','STARTED','RESULT_READY','ACCEPTED','FAILED','UNCERTAIN','ABANDONED')),
                      current_attempt INTEGER NOT NULL DEFAULT 0 CHECK (current_attempt >= 0),
                      configuration_digest TEXT NOT NULL,
                      failure_code TEXT,
                      created_at TEXT NOT NULL,
                      updated_at TEXT NOT NULL
                    );
                    CREATE TABLE interpretation_attempts (
                      operation_id TEXT NOT NULL REFERENCES interpretation_operations(operation_id),
                      attempt INTEGER NOT NULL CHECK (attempt >= 0),
                      host_ref TEXT REFERENCES host_records(host_ref),
                      request_json TEXT NOT NULL,
                      result_json TEXT,
                      status TEXT NOT NULL CHECK (status IN ('STARTED','RESULT_READY','VALID','INVALID','UNCERTAIN')),
                      validation_errors_json TEXT,
                      created_at TEXT NOT NULL,
                      PRIMARY KEY (operation_id, attempt)
                    );
                    CREATE TABLE interpretations (
                      interpretation_id TEXT PRIMARY KEY,
                      operation_id TEXT NOT NULL UNIQUE REFERENCES interpretation_operations(operation_id),
                      episode_id TEXT NOT NULL UNIQUE REFERENCES episodes(episode_id),
                      schema_version INTEGER NOT NULL,
                      extractor_version TEXT NOT NULL,
                      resolver_version TEXT NOT NULL,
                      accepted_revision INTEGER NOT NULL CHECK (accepted_revision >= 0),
                      accepted_at TEXT NOT NULL
                    );
                    CREATE TABLE candidates (
                      candidate_id TEXT PRIMARY KEY,
                      interpretation_id TEXT NOT NULL REFERENCES interpretations(interpretation_id),
                      local_key TEXT NOT NULL,
                      label TEXT NOT NULL,
                      normalized_label TEXT NOT NULL,
                      kind TEXT NOT NULL,
                      confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
                      salience REAL NOT NULL CHECK (salience >= 0 AND salience <= 1),
                      context_json TEXT NOT NULL,
                      UNIQUE(interpretation_id, local_key)
                    );
                    CREATE TABLE evidence_spans (
                      candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
                      ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
                      source_slot TEXT NOT NULL,
                      start_offset INTEGER NOT NULL CHECK (start_offset >= 0),
                      end_offset INTEGER NOT NULL CHECK (end_offset > start_offset),
                      text_digest TEXT NOT NULL,
                      PRIMARY KEY (candidate_id, ordinal)
                    );
                    CREATE TABLE resolution_decisions (
                      decision_id TEXT PRIMARY KEY,
                      interpretation_id TEXT NOT NULL REFERENCES interpretations(interpretation_id),
                      local_key TEXT NOT NULL,
                      canonical_label TEXT NOT NULL,
                      normalized_label TEXT NOT NULL,
                      decision_kind TEXT NOT NULL,
                      evidence_json TEXT NOT NULL,
                      created_at TEXT NOT NULL,
                      UNIQUE(interpretation_id, local_key)
                    );
                    CREATE TABLE semantic_bindings (
                      binding_id TEXT PRIMARY KEY,
                      instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
                      interpretation_id TEXT NOT NULL REFERENCES interpretations(interpretation_id),
                      candidate_id TEXT REFERENCES candidates(candidate_id),
                      local_key TEXT NOT NULL,
                      canonical_key TEXT NOT NULL,
                      canonical_label TEXT NOT NULL,
                      resolver_version TEXT NOT NULL,
                      binding_version INTEGER NOT NULL CHECK (binding_version >= 1),
                      source_json TEXT NOT NULL,
                      created_at TEXT NOT NULL
                    );
                    """.split(";")
                ):
                    statement = statement.strip()
                    if statement:
                        raw.execute(statement)
                columns = {
                    "interpretation_operations": "operation_id,episode_id,instance_id,base_manifest_id,status,current_attempt,configuration_digest,failure_code,created_at,updated_at",
                    "interpretation_attempts": "operation_id,attempt,host_ref,request_json,result_json,status,validation_errors_json,created_at",
                    "interpretations": "interpretation_id,operation_id,episode_id,schema_version,extractor_version,resolver_version,accepted_revision,accepted_at",
                    "candidates": "candidate_id,interpretation_id,local_key,label,normalized_label,kind,confidence,salience,context_json",
                    "evidence_spans": "candidate_id,ordinal,source_slot,start_offset,end_offset,text_digest",
                    "resolution_decisions": "decision_id,interpretation_id,local_key,canonical_label,normalized_label,decision_kind,evidence_json,created_at",
                    "semantic_bindings": "binding_id,instance_id,interpretation_id,candidate_id,local_key,canonical_key,canonical_label,resolver_version,binding_version,source_json,created_at",
                }
                for table, fields in columns.items():
                    raw.execute(
                        f'INSERT INTO "{table}" ({fields}) SELECT {fields} FROM "__v7_{table}"'
                    )
                for table in reversed(family):
                    raw.execute(f'DROP TABLE "__v7_{table}"')
                raw.execute(
                    "UPDATE store_info SET schema_version=8,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 8")
                version = 8
                raw.execute("PRAGMA legacy_alter_table = OFF")
            if version == 8 and target_version >= 9:
                raw.execute(
                    "CREATE TABLE IF NOT EXISTS identity_generation_attempts ("
                    "attempt_id TEXT PRIMARY KEY,"
                    "instance_id TEXT NOT NULL REFERENCES lineages(instance_id),"
                    "host_ref TEXT NOT NULL REFERENCES host_records(host_ref),"
                    "request_json TEXT NOT NULL,"
                    "result_json TEXT,"
                    "returned_model TEXT,"
                    "returned_provider TEXT,"
                    "effective_parameters_json TEXT,"
                    "usage_json TEXT,"
                    "latency_ms REAL,"
                    "finish_reason TEXT,"
                    "provider_evidence_json TEXT,"
                    "status TEXT NOT NULL CHECK (status IN ('STARTED','RESULT_READY','ACCEPTED','INVALID','UNCERTAIN')),"
                    "validation_errors_json TEXT NOT NULL,"
                    "identity_event_id TEXT UNIQUE REFERENCES identity_events(event_id),"
                    "created_at TEXT NOT NULL,"
                    "updated_at TEXT NOT NULL"
                    ")"
                )
                raw.execute(
                    "UPDATE store_info SET schema_version=9,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 9")
                version = 9
            if version == 9 and target_version >= 10:
                raw.execute(
                    "CREATE TABLE IF NOT EXISTS modeled_advance_operations ("
                    "operation_id TEXT PRIMARY KEY,"
                    "instance_id TEXT NOT NULL REFERENCES lineages(instance_id),"
                    "base_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),"
                    "context TEXT NOT NULL,"
                    "steps INTEGER NOT NULL CHECK (steps > 0),"
                    "target_json TEXT NOT NULL,"
                    "opportunity INTEGER NOT NULL CHECK (opportunity >= 1),"
                    "created_at TEXT NOT NULL"
                    ")"
                )
                raw.execute(
                    "CREATE TRIGGER IF NOT EXISTS modeled_advance_operations_immutable_update "
                    "BEFORE UPDATE ON modeled_advance_operations BEGIN "
                    "SELECT RAISE(ABORT, 'immutable record'); END;"
                )
                raw.execute(
                    "CREATE TRIGGER IF NOT EXISTS modeled_advance_operations_immutable_delete "
                    "BEFORE DELETE ON modeled_advance_operations BEGIN "
                    "SELECT RAISE(ABORT, 'immutable record'); END;"
                )
                raw.execute(
                    "UPDATE store_info SET schema_version=10,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 10")
                version = 10
            if version == 10 and target_version >= 11:
                for column, definition in (
                    ("arc_id", "TEXT"),
                    ("arc_reentry", "INTEGER NOT NULL DEFAULT 0"),
                    ("reentry_initiator", "TEXT"),
                    ("reentry_origin_arc_id", "TEXT"),
                    ("refractory_active", "INTEGER NOT NULL DEFAULT 0"),
                ):
                    if not has_column("development_observations", column):
                        raw.execute(
                            f"ALTER TABLE development_observations ADD COLUMN {column} {definition}"
                        )
                for statement in _SCHEMA_V11_TABLES.split(";"):
                    statement = statement.strip()
                    if statement:
                        raw.execute(statement)
                raw.execute(
                    "UPDATE store_info SET schema_version=11,record_version=record_version+1"
                )
                raw.execute("PRAGMA user_version = 11")
                version = 11
            for table in _IMMUTABLE:
                exists = raw.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
                if exists is None:
                    continue
                raw.execute(
                    f"CREATE TRIGGER IF NOT EXISTS {table}_immutable_update "
                    f"BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable record'); END"
                )
                raw.execute(
                    f"CREATE TRIGGER IF NOT EXISTS {table}_immutable_delete "
                    f"BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable record'); END"
                )
            raw.commit()
        except BaseException:
            raw.rollback()
            raise
        finally:
            raw.close()
        with source.open("rb") as handle:
            os.fsync(handle.fileno())

    migrate_to = migrate

    def create_root(
        self,
        *,
        scope_id: str = "local",
        self_ref_id: str | None = None,
        instance_id: str | None = None,
        permissions: StoragePermissions = StoragePermissions(),
        host_binding: Mapping[str, object] | None = None,
        controller_version: str = "mneme-p0.2",
    ) -> str:
        """Create the immutable root lineage and revision-zero manifest."""
        instance_id = validate_id(instance_id or new_id(), field="instance_id")
        self_ref_id = validate_id(self_ref_id or new_id(), field="self_ref_id")
        policy_id = new_id()
        manifest_id = new_id()
        now = _utc()
        history_digest = accepted_history_digest([])
        integrity = canonical_digest(
            {"instance_id": instance_id, "revision": 0, "self_ref_id": self_ref_id}
        )
        ledger_path = self.path.with_suffix(self.path.suffix + ".policy.jsonl").resolve()
        if self.connection.execute("SELECT 1 FROM store_info").fetchone() is not None:
            raise ValueError("store already has a lineage")
        if ledger_path.exists():
            raise SchemaError(f"permission authority already exists: {ledger_path}")
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.touch(mode=0o600)
        os.chmod(ledger_path, 0o600)
        bound_ref: str | None = None
        bound_json: str | None = None
        if host_binding is not None:
            bound_ref = canonical_digest(dict(host_binding))
            bound_json = json.dumps(dict(host_binding), sort_keys=True, separators=(",", ":"))
        with self.transaction() as db:
            db.execute(
                "INSERT INTO store_info VALUES (1,?,?,?,?,?,?)",
                (
                    SCHEMA_VERSION,
                    1,
                    ArtifactKind.WORKING,
                    instance_id,
                    controller_version,
                    str(ledger_path),
                ),
            )
            db.execute(
                "INSERT INTO lineages VALUES (?,?,?,?,?,?,?)",
                (instance_id, now, scope_id, self_ref_id, None, None, None),
            )
            db.execute(
                "INSERT INTO policies(policy_id,scope_id,storage_allowed,export_allowed,"
                "interpretation_allowed,recall_allowed,provider_reuse_allowed,learning_allowed,"
                "policy_version,bound_host_ref,bound_host_fingerprint_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    policy_id,
                    scope_id,
                    int(permissions.store),
                    int(permissions.export),
                    int(permissions.interpret),
                    int(permissions.recall),
                    int(permissions.provider_reuse),
                    int(permissions.learn),
                    3,
                    bound_ref,
                    bound_json,
                ),
            )
            db.execute(
                "INSERT INTO manifests("
                "manifest_id,instance_id,revision,parent_manifest_id,inherited_base_manifest_id,"
                "policy_id,self_ref_id,format_version,controller_version,integrity_digest,"
                "accepted_history_digest,graph_snapshot_id,graph_revision) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    manifest_id,
                    instance_id,
                    0,
                    None,
                    None,
                    policy_id,
                    self_ref_id,
                    1,
                    controller_version,
                    integrity,
                    history_digest,
                    None,
                    0,
                ),
            )
            db.execute(
                "INSERT INTO revisions VALUES (?,?,?,?,?,?,?,?)",
                (instance_id, 0, None, new_id(), "lineage_created", None, manifest_id, now),
            )
            db.execute("INSERT INTO current_state VALUES (1,?,?,?)", (instance_id, 0, manifest_id))
        return instance_id

    def current(self) -> sqlite3.Row:
        row = self.connection.execute("SELECT * FROM current_state").fetchone()
        if row is None:
            raise SchemaError("store has no active lineage")
        return cast(sqlite3.Row, row)

    def accepted_history(self, instance_id: str | None = None) -> list[sqlite3.Row]:
        instance_id = instance_id or str(self.current()["active_instance_id"])
        validate_id(instance_id, field="instance_id")
        return self._history_rows(instance_id)

    def _ancestry(self, instance_id: str) -> list[str]:
        """Return root-to-child lineage IDs for an active lineage."""
        result: list[str] = []
        seen: set[str] = set()
        current: str | None = instance_id
        while current is not None:
            if current in seen:
                raise SchemaError("lineage ancestry contains a cycle")
            seen.add(current)
            result.append(current)
            row = self.connection.execute(
                "SELECT parent_instance_id FROM lineages WHERE instance_id=?", (current,)
            ).fetchone()
            if row is None:
                raise SchemaError(f"lineage ancestry references missing instance: {current}")
            current = str(row[0]) if row[0] is not None else None
        result.reverse()
        return result

    def _history_rows(self, instance_id: str) -> list[sqlite3.Row]:
        rows: list[sqlite3.Row] = []
        for lineage_id in self._ancestry(instance_id):
            rows.extend(
                self.connection.execute(
                    """SELECT r.*, e.episode_id FROM revisions r
                    LEFT JOIN episodes e ON e.episode_id=r.episode_id
                    WHERE r.instance_id=? AND r.revision>0 ORDER BY r.revision""",
                    (lineage_id,),
                ).fetchall()
            )
        return rows

    def verify(self) -> list[str]:
        problems: list[str] = []
        fk = list(self.connection.execute("PRAGMA foreign_key_check"))
        problems.extend(f"foreign key: {tuple(row)}" for row in fk)
        head = self.current()
        active = self.connection.execute(
            "SELECT * FROM lineages WHERE instance_id=?", (head["active_instance_id"],)
        ).fetchone()
        if active is None:
            problems.append("current_state active lineage is missing")
        else:
            parent = active["parent_instance_id"]
            if (
                parent is not None
                and self.connection.execute(
                    "SELECT 1 FROM lineages WHERE instance_id=?", (parent,)
                ).fetchone()
                is None
            ):
                problems.append("lineage parent is missing")
            if (active["fork_checkpoint_id"] is None) != (active["fork_manifest_id"] is None):
                problems.append("fork ancestry is incomplete")
        manifest = self.connection.execute(
            "SELECT * FROM manifests WHERE manifest_id=?", (head["current_manifest_id"],)
        ).fetchone()
        if manifest is None or manifest["revision"] != head["current_revision"]:
            problems.append("current_state does not point to its revision manifest")
        elif int(self.connection.execute("PRAGMA user_version").fetchone()[0]) >= 2:
            for fork_manifest in self.connection.execute(
                "SELECT m.*,l.parent_instance_id FROM manifests m "
                "JOIN lineages l ON l.instance_id=m.instance_id "
                "WHERE l.parent_instance_id IS NOT NULL AND m.revision=0"
            ):
                expected_fork_integrity = canonical_digest(
                    {
                        "instance_id": fork_manifest["instance_id"],
                        "revision": 0,
                        "self_ref_id": fork_manifest["self_ref_id"],
                        "self_view_id": fork_manifest["self_view_id"],
                        "graph_snapshot_id": fork_manifest["graph_snapshot_id"],
                        "graph_revision": fork_manifest["graph_revision"],
                        "accepted_history_digest": fork_manifest["accepted_history_digest"],
                    }
                )
                if fork_manifest["integrity_digest"] != expected_fork_integrity:
                    problems.append(
                        f"fork manifest integrity disagrees with binding: "
                        f"{fork_manifest['manifest_id']}"
                    )
            graph_snapshot = manifest["graph_snapshot_id"]
            if graph_snapshot is not None:
                graph = self.connection.execute(
                    "SELECT instance_id,graph_revision FROM graph_snapshots WHERE snapshot_id=?",
                    (graph_snapshot,),
                ).fetchone()
                if graph is None:
                    problems.append("manifest graph snapshot is missing")
                elif int(graph[1]) != int(manifest["graph_revision"]):
                    problems.append("manifest graph revision disagrees with snapshot")
            try:
                if manifest["accepted_history_digest"] != self.accepted_history_digest(
                    str(head["active_instance_id"])
                ):
                    problems.append("manifest accepted-history digest disagrees with ledger")
            except SchemaError as exc:
                problems.append(str(exc))
        return problems

    def accepted_history_digest(
        self,
        instance_id: str | None = None,
        *,
        extra_records: list[Mapping[str, object]] | None = None,
    ) -> str:
        instance_id = instance_id or str(self.current()["active_instance_id"])
        records = self._history_content_records(instance_id)
        if extra_records:
            records.extend(extra_records)
        return accepted_history_digest(records)

    def _history_content_records(self, instance_id: str) -> list[Mapping[str, object]]:
        records: list[Mapping[str, object]] = []
        for row in self._history_rows(instance_id):
            if row["episode_id"] is None:
                continue
            episode = self.connection.execute(
                "SELECT operation_id,generation_id FROM episodes WHERE episode_id=?",
                (row["episode_id"],),
            ).fetchone()
            if episode is None:
                raise SchemaError(f"revision references missing episode: {row['episode_id']}")
            operation_id, generation_id = str(episode[0]), str(episode[1])
            output = self.connection.execute(
                "SELECT output_source_id FROM generation_records WHERE generation_id=?",
                (generation_id,),
            ).fetchone()
            if output is None:
                raise SchemaError(f"episode references missing generation: {generation_id}")
            sources = [
                {"role": str(source[0]), "supplier": str(source[1]), "content": str(source[2])}
                for source in self.connection.execute(
                    "SELECT role,supplier,content FROM sources WHERE operation_id=? ORDER BY ordinal",
                    (operation_id,),
                )
            ]
            generated = self.connection.execute(
                "SELECT content FROM sources WHERE source_id=?", (output[0],)
            ).fetchone()
            if generated is None:
                raise SchemaError(f"generation output source is missing: {output[0]}")
            records.append(
                {
                    "event_kind": str(row["event_kind"]),
                    "sources": sources,
                    "generation": {"content": str(generated[0])},
                }
            )
        return records
