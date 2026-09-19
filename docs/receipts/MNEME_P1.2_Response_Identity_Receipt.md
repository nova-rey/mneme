# MNEME P1.2 Response and Basic Identity Receipt

Date: 2026-09-19  
Base: `8a0d758f68d68cadfaa842200c151776d8636a1a`  
Tested code: `8e9ed7a4349409f7d9edae942410856f95da6e66`  
Package: `P1.2`

P1.2 adds the shared response boundary over the accepted P1.1 graph. Route
selection is bounded and fixed: contextual query coverage, route directness,
support, and canonical content tie-breaking determine eligible order. Candidate
confidence and salience remain evidence annotations and do not become
developmental ranking weights. Typed memory rendering is controller-owned,
bounded, and recorded in private turn traces; administrative IDs are excluded
from model-visible generation material.

The package adds deliberate identity adoption and cold-start self-view loading,
including a single prompted host naming call with strict local JSON validation.
Malformed naming results fail without regeneration or adoption. Checkpoint forks
clone inherited self-view content into child-local ownership while preserving
ancestry and content provenance. Explicit correction directives are append-only,
scoped, reversible records; declarations remain separate proposals.

Chat uses a process-local bounded session over the shared controller. The
existing integrated runner can opt into the controller through an explicit
experiment controller block while preserving the declared message context;
the default Phase Zero path remains available. Controller retries reuse the
same accepted operation and trace without duplicate provider calls, episodes,
or revisions. Schema 2→3 migration backfills local accepted-episode counts.

Validation performed at this stop gate:

- `.venv2/bin/pytest -q`: **148 passed**
- Focused P1.2, runner, and storage tests: **21 passed**
- `.venv2/bin/ruff check .`: **passed**
- `.venv2/bin/mypy --strict src`: **passed** (35 source files)
- `git diff --check`: **passed**
- CLI smoke: documented file-path instance creation, explicit name adoption,
  and JSON self-view inspection passed.
- Offline FakeHost acceptance: exact-once controller retry, one-call host
  naming, malformed naming rejection, reversible correction, checkpoint/fork
  self-view rebinding, restart, and fresh chat-session recovery passed.

No network or paid model call was required for P1.2. The bounded live budget
remains reserved for the approved Phase One acceptance demonstration. No P1.3
or Phase Two implementation was started.

