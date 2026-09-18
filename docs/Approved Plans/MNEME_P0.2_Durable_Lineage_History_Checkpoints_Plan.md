# MNEME P0.2 — Durable lineage, history, and checkpoints

**Status:** Approved implementation plan; implemented and accepted on 2026-09-18.

**Approval:** 2026-09-18, with the three amendments incorporated below.

**Accepted baseline:** `3205c8a4afce12bf040252ad1381c07393113829`.

This is the complete approved plan. The approval removes future-mechanism Python
placeholder contracts and fixtures, limits permissions to storage and export/copy,
and names the content comparison an **accepted-history digest**. These explicit
P0.2 scope amendments take precedence over the roadmap's earlier placeholder-contract
proposal; the supplied specification and roadmap remain unchanged. All other
architecture, lifecycle, demonstration, and implementation-chunk decisions are retained.
Implementation was authorized by the active P0.2 execution task. The plan remains the
binding contract; implementation is complete for the approved P0.2 scope and later
phases remain deferred.

## 1. Basis and architecture

Plan against the clean, accepted baseline `3205c8a4afce12bf040252ad1381c07393113829`.
P0.1 remains accepted. Planning and approval do not constitute implementation.

The governing requirements are the [current specification](../specifications/MNEME_Model_Instance_Development_Spec.md),
[P0.2 roadmap](../specifications/MNEME_Development_Roadmap.md), and the
[research amendment](../research/MNEME_Research_Amendment_Individuality_Identity_2026-09-14.md)'s
separation of development from measurement, subject to the explicit approval amendments above.

**Use one SQLite database per working lineage and self-contained SQLite checkpoint copies.**
This follows the roadmap's explicit storage choice. A shared multi-lineage database
with pointer-only checkpoints could be simpler in isolation, but would change that
normative decision.

The minimal architecture is:

```text
CLI
 ├─ read-only inspection / checkpoint loading
 └─ continuity service
     ├─ prepare request and pin current manifest
     ├─ call existing Host outside database transactions
     ├─ persist returned generation
     └─ atomically accept episode, revision, manifest, and head

Branch SQLite database
 ├─ immutable lineage and accepted history
 ├─ immutable generation evidence and run manifests
 ├─ mutable pending-operation status
 └─ materialized current-state pointer

Checkpoint / fork publication
 └─ SQLite backup → validate staged database → publish complete file
```

Use Python's standard `sqlite3`, existing dataclass conventions, and explicit SQL.
Add no ORM, service, broker, or storage dependency.

P0.2 records experience without interpreting it. Stored history is not automatically
inserted into subsequent prompts.

## 2. Operational definitions

| Term | P0.2 definition |
|---|---|
| **Instance** | The specification's combination of a frozen host configuration, lineage identity, permissions, and accepted developmental state. A loaded instance is a runtime binding of those components, not a new identity. |
| **Lineage / branch** | One independently writable continuation, identified by immutable `instance_id`. “Branch” describes that role; it does not introduce another identifier. |
| **Episode** | One accepted interaction, containing ordered source references and, for a generated interaction, its actual generation record. Immutable after acceptance. |
| **Event** | A committed state-transition entry. In P0.2, the only revision-advancing event is `episode_accepted`; it accepts exactly one episode. No generic event-bus abstraction. |
| **Revision** | A nonnegative, monotonically increasing accepted-state version local to one lineage. The complete address is `(instance_id, revision)`. |
| **Manifest** | An immutable, versioned materialization describing the state at a revision: lineage binding, history boundary, permissions, structural self-reference, compatible versions, and host/run references. |
| **Run / RunManifest** | Provenance for one prepared generation in P0.2: pinned input manifest, host environment, request settings, explicit seed information, policies, and software versions. Runs reference episodes; they do not own history. |
| **Experiment** | An optional external identifier. No Python experiment contract, scheduler, cohorts, split enforcement, or experiment lifecycle yet. |
| **Pending operation** | Durable intent to generate and accept one episode, with a stable operation ID, pinned base revision, request, and execution status. It is not accepted experience. |
| **Checkpoint** | An immutable, self-contained database artifact identifying one lineage at one accepted revision. It can reconstruct that accepted state without the original working database. |
| **Fork** | A new lineage initialized from a published checkpoint. It retains inherited provenance and acquires an independent writable head. |

### Revision rules

- Root lineage creation produces revision `0`, with empty accepted history.
- A child starts at its own revision `0`, whose inherited base is the parent checkpoint.
- Each newly accepted episode advances that lineage by exactly one revision.
- Failed, uncertain, rejected, or abandoned operations do not advance revisions.
- Generation alone, inspection, checkpoint creation, backups, and evaluation do not advance revisions.
- Administrative labels never advance revisions. P0.2 need not expose label editing.
- Future accepted developmental transitions may advance revisions without creating a new episode; this requires an explicit later schema/policy extension.
- Graph and compiled-field revisions remain separate future concepts, as required by specification §13.1.

Thus `B@0` can inherit `A@100`; `B@1` adds one child-origin episode. Inspection reports
inherited and local counts separately.

**Confirmed restoration rule:** Loading an older checkpoint preserves its original
identity and revision in a read-only view. It does not rewind the live branch.
Further development from that older state requires a fork.

## 3. Storage and schema

Default local layout:

```text
$XDG_STATE_HOME/mneme/              # fallback ~/.local/state/mneme/
  instances/<instance-id>.sqlite3
  checkpoints/<checkpoint-id>.sqlite3
  staging/
  writer.lock
```

Allow an explicit `--store PATH`. No authoritative central catalog: list commands
discover validated published files. Staged files are never discoverable instances
or checkpoints.

Each branch database contains its active lineage plus the copied ancestor records
necessary to explain inherited history.

### Proposed schema

The following is SQL-like design, not implementation SQL. IDs are UUID strings;
timestamps are UTC evidence, never ordering authorities.

| Record | Important fields and constraints | Mutability |
|---|---|---|
| `store_info` | Singleton PK; `schema_version`, `record_version`, `artifact_kind`, `active_instance_id FK`, `created_by_version` | Structural changes only during unpublished creation/fork or explicit migration |
| `lineages` | `instance_id PK`, `created_at`, `scope_id`, `self_ref_id UNIQUE`, `parent_instance_id FK NULL`, `fork_checkpoint_id FK NULL`, `fork_manifest_id FK NULL` | Immutable |
| `host_records` | `host_ref PK`, model/provider/runtime/revision columns; canonical upstream model/revision/digest nullable; versioned fingerprint JSON; canonical digest UNIQUE | Immutable |
| `policies` | `policy_ref PK`, `scope_id`, explicit storage and export/copy permissions, policy version; no learning or recall permission fields | Immutable |
| `run_manifests` | `run_id PK`, originating instance FK, pinned manifest FK, host FK, policy FK, optional experiment reference, controller/package versions, context mode, explicit generation seed and RNG-plan version | Immutable |
| `operations` | `operation_id PK`, `episode_id UNIQUE`, instance FK, base revision, run FK UNIQUE, canonical intent digest, status, safe failure code, optional superseded-operation FK | Intent immutable; status mutable |
| `sources` | `source_id PK`, operation FK, ordinal, role, supplier, content text, permission FK, content digest; `UNIQUE(operation_id, ordinal)` | Immutable |
| `generation_records` | `generation_id PK`, operation FK UNIQUE, host FK, output source FK, returned model/provider, effective parameters, usage columns, latency, finish reason, allowlisted provider evidence | Immutable |
| `episodes` | `episode_id PK`, operation FK UNIQUE, origin instance FK, accepted revision, generation FK UNIQUE, occurred/accepted timestamps; `UNIQUE(origin_instance_id, accepted_revision)` | Immutable |
| `revisions` | Composite PK `(instance_id, revision)`; previous local revision, event ID UNIQUE, event kind, episode FK UNIQUE nullable at revision zero, manifest ID UNIQUE, accepted timestamp | Immutable |
| `manifests` | `manifest_id PK`, instance/revision UNIQUE FK, parent manifest FK, inherited-base manifest FK nullable, policy FK, self-reference binding, host/run references, format/controller version, integrity digest and accepted-history digest | Immutable |
| `current_state` | Singleton active lineage FK, current revision, current manifest FK | Updated only with accepted transition |
| `checkpoints` | `checkpoint_id PK`, source instance/revision FK, source manifest FK, creation timestamp, format version, accepted-state integrity digest | Immutable; authoritative artifact descriptor lives in the checkpoint copy |

Request settings belong in the run manifest; ordered request messages are reconstructed
from input `sources`. Output text is stored once as a model-origin source. Parameters
and fingerprint extensions may use validated JSON; IDs, relationships, revisions,
roles, permissions, statuses, usage, and output content remain explicit fields.

Composite foreign keys and application validation enforce same-lineage bindings.
Deferred constraints handle revision/manifest creation in one transaction. Use `CHECK`
constraints for revision ranges, allowed states, root-versus-fork ancestry, and artifact kinds.

Database triggers reject updates/deletes to accepted immutable records. Pending status
updates cannot alter an operation's request, base revision, or result. These protect
application invariants; they are not tamper-proof security against a database owner.

### Authoritative and derived state

The authoritative accepted history is:

- lineage creation and fork ancestry;
- ordered revision entries;
- accepted episodes and their immutable sources;
- referenced generation, host, policy, and run records.

Manifests and `current_state` materialize that history. A deterministic reducer can
reconstruct the P0.2 view without calling a model.

On disagreement, fail closed for development. `doctor` identifies the mismatch; do
not silently choose the head pointer or “repair” history. P0.2 tests reconstruction
in memory and recovery from validated backups. General salvage tooling is deferred.

Keep two separate digests:

- **Integrity digest:** includes provenance and administrative bindings.
- **Accepted-history digest:** compares ordered accepted history/content while excluding irrelevant administrative identifiers and timestamps.

Equality of the accepted-history digest does **not** establish behavioral equivalence
between instances. P0.2 has no learned influence. Do not call differing episode histories
“personality,” or use a history digest as a behavioral input. An actual behavioral or
developmental-state digest may be introduced when associations, self-model state,
and influence mechanisms exist.

## 4. Generation, transactions, and idempotency

Use explicit transaction control compatible with Python 3.11: `isolation_level=None`,
SQL `BEGIN IMMEDIATE`, `COMMIT`, and `ROLLBACK`.

Set and verify:

- `foreign_keys=ON`;
- `journal_mode=DELETE`;
- `synchronous=EXTRA`;
- a bounded busy timeout.

Use one store-wide OS writer lock for mutating commands. SQLite still enforces database
locking. Read-only commands do not acquire this application writer lock.

`EXTRA` adds directory synchronization after rollback-journal removal; guarantees still
depend on correct filesystem, locking, and hardware behavior. See
[SQLite synchronization](https://sqlite.org/pragma.html#pragma_synchronous) and
[atomic commit](https://www.sqlite.org/atomiccommit.html).

### Lifecycle

The preparation must precede the external call:

```text
prepare → generate → persist result → accept/revise → optional checkpoint
```

1. **Prepare — short transaction**
   - Validate scope and storage permission.
   - Pin the current manifest/revision.
   - Persist operation ID, reserved episode ID, request sources, run manifest, and selected host fingerprint.
   - Commit status `PREPARED`.
   - Permit only one unresolved development operation for the active lineage.

2. **Start generation — short transaction**
   - Verify operation and host binding.
   - Change status to `STARTED`; commit.

3. **Generate — no SQLite write transaction**
   - Call the existing `Host.generate`.
   - Send only explicit generation material.
   - Do not add lineage IDs, timestamps, ancestry, checkpoint IDs, or stored history.

4. **Persist result — short transaction**
   - Validate and store returned output and permitted provenance.
   - Change status to `RESULT_READY`; commit.
   - This result survives any later acceptance failure.

5. **Accept and revise — one transaction**
   - First check whether this operation already has an accepted episode.
   - Require active-lineage ownership, `RESULT_READY`, and the unchanged pinned head.
   - Insert episode, revision `N+1`, and immutable manifest.
   - Update `current_state` and operation status to `ACCEPTED`.
   - Commit everything together.

6. **Checkpoint**
   - Separate database-copy publication operation.
   - Does not advance the revision.

A stale-base result is retained but cannot be silently rebased or accepted against a
different state. Abandon it and prepare another operation explicitly.

### Stable IDs and retries

- Callers may supply an operation UUID; otherwise `prepare` generates and durably records it before generation.
- The CLI prints the ID after preparation. An uncertain prepare can be located through operation inspection.
- The same ID and identical canonical intent return the existing operation.
- The same ID with different intent is an idempotency conflict.
- `accept` retries return the original episode/revision receipt, even if the head has since advanced.
- An accepted event ID is the operation ID; the episode has its separately reserved immutable ID.
- Duplicate UUID collisions with different content are errors, never overwrites.

This guarantees **at-most-once accepted application**, not exactly-once remote generation.

### Uncertain generation

On restart, `STARTED` without a persisted result means `UNCERTAIN`.

Do not automatically call the provider again. The response might have existed and been
nondeterministic. The operator must abandon that operation and explicitly prepare a
replacement, linked through `supersedes_operation_id`.

A `RESULT_READY` operation resumes acceptance without another call. Provider failures
and malformed results remain operational evidence; they do not become accepted episodes.

## 5. Checkpoints, forks, restoration, and backup

### Checkpoint publication

Checkpoints physically copy the small database, following the roadmap. They are not
cheap ledger pointers.

1. Acquire the writer lock and capture the current revision.
2. Verify export/copy permission for the material to be copied, then use `Connection.backup` into a unique staging file.
3. In the staged copy, mark the artifact as a checkpoint and add its checkpoint descriptor.
4. Verify copied revision, manifest binding, integrity, foreign keys, and compatibility.
5. Close connections, synchronize the file, publish without overwriting an existing final filename, and synchronize the containing directory.
6. Release the lock and return the checkpoint receipt.

The source database does **not** receive a required catalog update. The published
checkpoint contains its own authority, eliminating a database/filesystem two-phase commit.

The backup API provides a consistent copy; holding the application writer lock prevents
the copied revision from moving during the operation. See the
[SQLite backup API](https://www.sqlite.org/backup.html).

Use stable caller-supplied checkpoint IDs for retryable automation. If the final artifact
already exists, verify its binding and return it; a conflicting binding is an error.
Never silently promote abandoned staging files.

A checkpoint may retain copied pending-operation evidence, but that evidence is outside
its accepted-state view and cannot be executed through the checkpoint API.

### Fork publication

- Accept only a validated, published checkpoint, with export/copy permission for its copied contents.
- Copy it into staging.
- Preserve ancestor lineages, source IDs, episode IDs, originating instance IDs, revisions, and checkpoint receipt.
- Add child lineage identity and a new structural self-reference.
- Create child revision `0`, referencing the parent checkpoint manifest.
- Replace only the staged active binding and head.
- Validate inherited-history equivalence, then publish the child database.

Child history is inspected as the ancestor prefix followed by local accepted episodes.
It is not relabeled as child-origin history.

Copied ancestor operations are never executable by the child: mutating APIs require
`operation.instance_id == active_instance_id`.

Each lineage has at most one parent. P0.2 supports a rooted ancestry forest, with no
merges. Copies cost storage but make B independent of A's database availability.

### Restoration and frozen access

Provide a separate `CheckpointReader` exposing immutable records and reconstructed
views. It has no prepare, accept, migration, or repair methods.

Open published checkpoints read-only and deny write statements. Do not treat `immutable=1`
as protection: SQLite documents it as an assumption that skips locking and change
detection. See [SQLite URI semantics](https://www.sqlite.org/uri.html).

- Loading `A@N` preserves A's identity.
- Restarting A loads its existing current head.
- An older checkpoint never replaces a newer writable A in place.
- Independent development from `A@N` creates B.

Later evaluation can consume this reader and write results into a separate artifact
directory. It cannot update episodes, revision counters, access timestamps, or pending
operations. P0.2 adds the boundary and tests, not the evaluation harness.

### Backup versus checkpoint

- **Checkpoint:** frozen accepted revision, usable as a fork origin.
- **Backup:** database-aware preservation of a working database, including pending work.
- **Database snapshot:** the technical consistent-copy mechanism.
- **Fork point:** the checkpoint manifest referenced by child ancestry.

Provide `store backup <instance-id> --output FILE`. Each branch database is self-contained
for its ancestry. Whole-store preservation backs up every working database and copies
published checkpoint files under the store lock. Backups and copied checkpoint files
must satisfy export/copy permission for all included material.

JSON output is for inspection; a JSONL import/export system is unnecessary in P0.2.

## 6. Host, permissions, schema versions, and privacy

### Host association

Reuse the P0.1 Host interface unchanged.

Record separately:

1. Canonical upstream model/checkpoint reference.
2. Actual execution fingerprint.
3. Returned provider/model and effective generation settings.

For DeepInfra, retain the pinned canonical Gemma reference while honestly recording
that hosted exact-weight equivalence is unknown. A matching model name is not proof
of identical weights.

A prepared request pins one execution host. Later operations may explicitly select
another host, producing new provenance. This does not imply host portability or
behavioral equivalence.

There are two existing documentation inconsistencies to correct during implementation:

- README/decision prose attributes fallback transcript rendering to the hosted path generally, although DeepInfra uses structured chat messages.
- One decision sentence understates DeepInfra's advertised capabilities; live code also reports token usage.

These are evidence-alignment edits, not reopening P0.1 acceptance.

### Permission scope

Implement one authorized local scope per lineage. Limit the policy record to two
permissions corresponding to P0.2 behavior:

- **Storage permission:** whether source material may be persisted.
- **Export/copy permission:** whether persisted material may be included in checkpoints, forks, backups, or explicit content export.

Check storage permission before persistence and export/copy permission before creating
a copy or exporting content. Because checkpoint and backup copies include the database's
contents, reject a disallowed copy rather than silently filtering it into an incomplete
snapshot. This includes pending-operation material retained in the database.

Do not introduce learning or recall permission fields, placeholder semantics, or a
general policy framework. Those permissions will be defined when their mechanisms exist.
Forks retain the same scope and permission policy; no cross-scope transfer API.

No destructive lineage/episode deletion command in P0.2. This is a temporary
supported-operation boundary, not a claim that personal data must remain undeletable.
Future authorized erasure must cover derived state and checkpoint copies, as required
by specification §13.3.

### Schema versioning

- Initial database schema version: `1`.
- Fixed SQLite `application_id` identifies MNEME stores.
- `PRAGMA user_version` must agree with `store_info.schema_version`.
- Version record serialization independently from database layout.
- Keep a small ordered migration registry; initially only store initialization exists.
- Migration requires an explicit writable command, prior backup, and transactional completion.
- Never migrate a published checkpoint in place.
- Newer unsupported schemas or manifest versions fail before writes or model calls.
- Future checkpoint migration produces a separately identified compatible artifact, retaining origin evidence.

### Privacy

- Private directories `0700`, database/artifact files `0600`, restrictive umask.
- Keep databases, journals, staging files, backups, and conversation artifacts out of Git.
- No conversation content in ordinary logs; CLI content display requires an explicit option.
- Persist allowlisted provider evidence, not arbitrary `raw_metadata` dictionaries.
- Never store authorization headers, environment dumps, provider tokens, or raw exception bodies.
- Preserve requested/effective generation parameters and safe provider request IDs where available.
- Sensitive content intentionally supplied as conversation text remains conversation data; no claim of universal secret detection.
- No encryption-at-rest or cryptographic identity.

## 7. Recovery behavior

| Interruption or error | Required behavior |
|---|---|
| Before preparation transaction | No durable operation or revision change. |
| During preparation | Entire preparation exists or none does. |
| Prepared, before generation starts | Safe to execute the saved request. |
| After `STARTED`, before result persistence | Mark uncertain on recovery; no automatic regeneration. |
| Result persisted, before acceptance | Resume acceptance using the saved output. |
| During acceptance transaction | SQLite recovery exposes prior state or the complete accepted transition. |
| After commit, before acknowledgment | Same operation retry returns original receipt. |
| Duplicate event/operation ID | Same intent returns existing result; different intent fails. |
| Head changed after preparation | Retain result and reject acceptance as stale. |
| Checkpoint interrupted during backup | Staging remains undiscoverable; source is unchanged. |
| Checkpoint published before acknowledgment | Retry validates and returns the existing artifact. |
| Checkpoint requested after interrupted acceptance | Recover the working DB first; snapshot whichever complete revision exists. |
| Fork from absent/incompatible checkpoint | Fail before publication; no visible child. |
| Corrupt DB or ledger/materialization mismatch | Fail closed; preserve evidence and restore from a validated backup. |
| Disk full or synchronization failure | Report failure or uncertain outcome; inspect stable IDs before retrying. |

Strict read-only inspection must not secretly perform hot-journal recovery. If recovery
is required, report it and direct the operator to `store recover`, which opens the
mutable branch appropriately. SQLite may require writes to recover a hot journal
before reading. See [rollback-journal recovery](https://www.sqlite.org/lockingv3.html).

Process-kill tests establish process-interruption behavior. They do not prove survival
of faulty storage, filesystem bugs, or actual power loss. File publication durability
likewise depends on supported local filesystem synchronization behavior.

## 8. CLI and public API

Preserve existing host commands. Add:

```text
mneme --store PATH instance create --host HOST [--id UUID]
mneme --store PATH instance list --json
mneme --store PATH instance inspect ID --json

mneme --store PATH episode prepare ID --request FILE --host HOST \
    [--operation-id UUID]
mneme --store PATH operation generate OPERATION_ID
mneme --store PATH operation inspect OPERATION_ID --json
mneme --store PATH operation list INSTANCE_ID --json
mneme --store PATH operation abandon OPERATION_ID
mneme --store PATH episode accept OPERATION_ID
mneme --store PATH episode list INSTANCE_ID [--include-content] --json

mneme --store PATH checkpoint create INSTANCE_ID [--id UUID]
mneme --store PATH checkpoint list INSTANCE_ID --json
mneme --store PATH checkpoint inspect CHECKPOINT_ID --json
mneme --store PATH instance fork --checkpoint CHECKPOINT_ID [--id UUID]

mneme --store PATH store recover INSTANCE_ID
mneme --store PATH store backup INSTANCE_ID --output FILE
mneme --store PATH doctor --json
```

Request files contain validated P0.1 generation material and source-policy references.
The new persistence path rejects unsupported or silently ignored request fields before
calling the host.

Machine output includes schema version, stable IDs, revision, manifest reference, and
an explicit status/error code. Keep the existing `host qualify --json PATH` behavior
unchanged.

Public Python boundaries:

- `prepare_episode`, `generate_operation`, `accept_episode`;
- `load_instance`, `load_checkpoint`;
- `create_checkpoint`, `fork_instance`, `backup_instance`;
- read-only history iteration and deterministic reconstruction.

No full conversational controller or automatic transcript accumulation.

## 9. Proposed files

Group implementation into a small package:

- `src/mneme/state/contracts.py`: durable contracts, validation, canonical serialization.
- `src/mneme/state/storage.py`: schema initialization, explicit transactions, queries, immutable-record protections.
- `src/mneme/state/service.py`: operation lifecycle, acceptance, manifest construction, history reconstruction.
- `src/mneme/state/snapshots.py`: checkpoint, fork, backup, and publication.
- `src/mneme/state/reader.py`: frozen read-only interface.

Future concepts remain documented in the specification and roadmap. Introduce their
Python contracts and fixtures only when their implementing phase needs them.

Extend `src/mneme/cli.py`; extract command handling into a small CLI module if needed.
Preserve `host.py` and existing provider behavior.

Add focused storage/continuity tests and non-sensitive fixtures. Update README,
documentation index, `.gitignore`, and a P0.2 decision document. Append `bible.md`
in every implementation commit.

After explicit implementation authorization, use the work-queue skill to add the
implementation packages and validation receipts. Do not alter the completed P0.1 package.
The queue has no planning/approval state; approval is recorded in this document and
`bible.md`, leaving the P0.1 queue unchanged until implementation is authorized.

## 10. Test plan

Ordinary CI remains network-free.

| Group | Concrete tests |
|---|---|
| Contracts | Round trips; invalid UUIDs/revisions/roles; canonical serialization; unknown versions; lineage versus self-reference distinction. No future-mechanism placeholder contracts or fixtures. |
| Storage | Foreign keys; immutable-row rejection; verified PRAGMAs; acceptance rollback at intermediate statements; disk/write failure; unsupported schema rejection. |
| Permissions | Storage denial prevents persistence; export/copy denial prevents checkpoint, fork, backup, and explicit content export; no learning/recall permission fields or semantics. |
| Lineage | Root creation; child revision zero; ancestry chains; preserved source ownership; independent writes; child remains readable without parent database. |
| Episodes | Contiguous local revisions; ordered sources; model output never becomes user testimony; rejected work absent from accepted history. |
| Manifests | Rebuild accepted view from ledger; detect incorrect head/digest/binding; no provider call during reconstruction; accepted-history digest ignores irrelevant administrative IDs/timestamps but changes with accepted content/order, without claiming behavioral equivalence. |
| Checkpoints | Backup consistency; exact revision binding; read-only load; no future-state leakage; incompatible artifact rejection; repeated publication ID. |
| Idempotency | Duplicate prepare, generate after saved result, accept after later head movement, conflicting ID reuse, post-commit acknowledgment loss. |
| Recovery | Child-process termination before result persistence, before acceptance commit, after commit, during checkpoint construction, and during fork publication. |
| Isolation | Frozen reader rejects writes; no access-counter changes; evaluation-style generation leaves source bytes and accepted state unchanged. |
| Host boundary | FakeHost receives identical generation material across different lineage/run/checkpoint IDs; seeds independent of IDs; changed visible input still changes output. |
| Privacy | Tokens and synthetic sensitive headers absent from DB/logs/errors; unknown provider metadata excluded; restrictive file permissions. |
| Migration | Initialization, repeated opening, version disagreement, newer schema, transactional migration rollback using a test migration. |
| Integration | Opt-in DeepInfra generation, persisted result, acceptance, restart, and fingerprint inspection. |

Use subprocess synchronization barriers for crash tests. Kill a writer after partial
SQL work but before commit, then reopen from a fresh process. Avoid relying only on
caught exceptions.

Run existing pytest, Ruff, and strict mypy checks alongside the new suite.

## 11. Acceptance demonstration

Use a temporary clean store and explicit IDs retained in the demonstration receipt.
Use non-sensitive material with storage and export/copy permission for this demonstration.

1. Initialize the store and create A.
2. Prepare one small, non-sensitive request for `gemma-deepinfra`.
3. Generate once, persist its result, and accept it as `A@1`.
4. Inspect the actual output, canonical model reference, execution fingerprint, and hosted-equivalence uncertainty.
5. Add two FakeHost episodes, obtaining `A@3`; their host provenance must remain explicit.
6. Create checkpoint C for `A@3`.
7. Fork B from C, producing `B@0`.
8. Compare A's checkpoint history with B's inherited history: same episode/source IDs, contents, order, and original authorship.
9. Give A and B distinct FakeHost interactions. Verify `A@4` and `B@1` with independent tails.
10. Terminate the processes and reopen the store.
11. Verify identities, heads, ancestry, checkpoint C, and accepted history.
12. Reconstruct accepted views from the ledger and compare them with manifests.
13. Retry an accepted operation; verify no new episode or revision.
14. Run the pre-commit process-kill case and recover the prior head.
15. Run the post-commit/pre-acknowledgment case and recover the single committed acceptance.
16. Load C through the frozen reader; prove mutation rejection and unchanged checkpoint bytes.
17. Run matched FakeHost requests with different administrative IDs; compare generation material and output.
18. Back up B, load the backup independently, and demonstrate that A's working database is unnecessary.
19. Ask `instance inspect B --json` to produce the auditable ancestry answer: B originated from A at revision 3 through checkpoint C, with its fork manifest and inherited episode origins.

Default live budget: **one real Gemma generation**, bounded output length, no automatic
retries. FakeHost covers the rest. A failed real call leaves the live acceptance step
open without affecting offline results.

## 12. Implementation chunks

| Chunk | Goal and likely files | Acceptance | Dependencies |
|---|---|---|---|
| **1. State contracts and schema** | State contracts/storage, versioning, P0.2 fixtures, P0.2 decision document | Root creation, schema validation, storage and export/copy permissions only, immutable records, round trips, structural self-reference with no name; no future-mechanism contracts | Approved plan and explicit implementation authorization |
| **2. Durable episode acceptance** | Service layer, host-boundary adapter, operation tests | Prepared/result/accepted lifecycle, exact retry behavior, contiguous revisions, atomic manifest/head publication, no metadata leakage | 1 |
| **3. Checkpoints and independent forks** | Snapshots, reader, lineage/recovery tests | Complete artifact publication, child inheritance, read-only restoration, backup, interrupted publication behavior | 1–2 |
| **4. CLI and acceptance closure** | CLI, docs, demonstration fixtures, CI and queue receipts | Human-readable and JSON inspection; subprocess crash suite; existing checks pass; bounded real-Gemma receipt | 1–3 |

Each chunk returns a reviewable candidate and declared validation receipts before
completion. Canonical integration remains serialized.

## 13. Decisions, risks, and scope boundary

**Blocking decisions:** None remain for the plan. Human approval is recorded, including
the three amendments. Implementation awaits separate explicit authorization. Historical
restoration remains read-only; future-mechanism Python contracts and fixtures are deferred.

**Implementation defaults settled here:**

- Per-branch SQLite databases and copied checkpoints.
- Child-local revision numbering from zero.
- Self-contained copied ancestry.
- One active writer.
- No automatic regeneration after uncertain provider execution.
- No destructive deletion or writable historical rewind.
- No authoritative cross-file checkpoint registry.

**Principal risks:**

- Database copies increase storage use; acceptable for the small pilot.
- Strict uncertainty handling sometimes requires explicit abandonment and replacement.
- Provider metadata is incomplete; provenance cannot establish unknown hosted weights.
- Copying checkpoints retains conversation content and complicates future erasure.
- Hardware power-loss guarantees remain conditional, beyond process-kill testing.

**Intentionally deferred:** host portability research, developmental identity, naming,
graph state, learning rules, extraction, outcomes, influence, behavioral individuality,
privacy-erasure machinery, and experimental methodology.

Future concepts stay in the specification and roadmap until their implementing phase
needs software contracts. The structural self-reference is unset and never supplied
to the model. There are no graph tables, learned updates, or identity transitions.
Storage and export/copy are the only P0.2 permission semantics. The accepted-history
digest compares content and does not establish behavioral equivalence.

P0.3 retains experiment specifications, split rules, budgets, and random-stream
scheduling. P0.4 retains the integrated baseline runner and reproducibility study.
Phase 1 retains extraction, association retrieval, naming behavior, and the conversation loop.

P0.2 finishes when lineage, accepted history, revisions, ancestry, and checkpoints
survive restart and interrupted writes with auditable provenance—not when MNEME
exhibits personality.
