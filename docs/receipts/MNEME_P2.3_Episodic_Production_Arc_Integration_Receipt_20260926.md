# P2.3 episodic production-arc integration receipt

Implementation commit: `7faaf96b9def04ef3bb5cfcde148a290fa66b232`  
Provider calls: 0  
Historical v6 records: unchanged

## Correction

The bounded conversation-arc contract is now carried through the production
contingent and separated-support runners.  Each accepted developmental turn
is published to a deterministic arc before interpretation.  The first turn
opens the immutable arc, later accepted turns add idempotent membership, and
the declared final turn publishes the close event.  A retry of the same
coordinate verifies the existing arc/member/event records instead of adding a
second developmental observation.

The production assessment adapter receives the same `(subject, turn)` arc
binding used by the runner.  Published observations therefore retain the arc
ID, prior related arc, re-entry initiator, and the explicit two-round
model-origin refractory state.  The runner uses its declared chapter windows
as the bounded topic signal; it does not infer a new arc from every noun or
invent semantic edges.  The existing `EpisodeTracker` remains available for
callers with richer turn-level topic/source declarations.

Source-role handling also now treats a runtime `feedback` binding as external
outcome evidence.  Controller, model, replay, and tool bindings remain
non-external for deterministic provenance resolution.  This keeps an outcome
report in the same conversational arc without turning it into a fresh
independent root unless the existing learner/provenance rules permit that.

## Validation

* `.venv2/bin/pytest -q`: **460 passed**;
* `.venv2/bin/ruff check src tests`: passed;
* `.venv2/bin/mypy --strict src/mneme`: passed;
* wheel build in an isolated Hatchling builder and fresh-target import smoke:
  passed;
* `work-queue --queue .codex/work-queue.json validate`: passed;
* `git diff --check`: passed;
* remote CI for this implementation commit: `36209632261` passed;
* no DeepInfra, local-model, or other provider calls were made.

Focused regressions cover adjacent topic-window grouping, genuine pivot and
external re-entry timing, idempotent arc retry, and feedback-role preservation.

## Historical boundary

The preserved v6 transcript and its six admitted observations predate this
runner integration and contain no persisted arc metadata.  The previously
published derived v6 audit therefore remains conservative and inconclusive on
external-versus-model re-entry; it still awards no retroactive credit and does
not alter the ten zero-state edge records or the historical
`COMPLETED_INADEQUATE` disposition.  This correction makes the evidence
available to new/resumed executions under the versioned arc contract; it does
not rewrite old receipts or replay old conversations.

P2.3 remains waiting on its existing adequacy/accounting review dependency.
No Phase Two release or Phase Three work is claimed.
