"""Deterministic conversational episode grouping and re-entry metadata.

The learner receives accepted turn-level observations, but developmental
credit must be attributable to conversational arcs rather than every message.
This module deliberately uses caller-supplied semantic topic keys and source
roles.  It does not attempt open-ended discourse understanding.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class EpisodeError(ValueError):
    """A turn or episode declaration is malformed."""


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConversationTurn:
    """One accepted conversational turn supplied to the bounded grouper."""

    turn_id: str
    ordinal: int
    topic_keys: tuple[str, ...]
    source_role: str
    relationship_keys: tuple[str, ...] = ()
    outcome_keys: tuple[str, ...] = ()
    explicit_pivot: bool = False

    def __post_init__(self) -> None:
        if not self.turn_id or self.ordinal < 0:
            raise EpisodeError("turn identity must be non-empty and ordinal non-negative")
        if not self.topic_keys:
            raise EpisodeError("turn must provide at least one topic key")
        if any(not item for item in self.topic_keys):
            raise EpisodeError("turn topic keys must be non-empty")
        if self.source_role not in {"external", "model", "mneme", "unknown"}:
            raise EpisodeError("unsupported turn source role")


@dataclass(frozen=True)
class ConversationEpisode:
    """Immutable bounded arc record used by provenance and learner traces."""

    episode_id: str
    start_ordinal: int
    end_ordinal: int
    turn_ids: tuple[str, ...]
    topic_keys: tuple[str, ...]
    initiation_role: str
    turn_source_roles: tuple[str, ...] = ()
    relationship_keys: tuple[str, ...] = ()
    outcome_keys: tuple[str, ...] = ()
    prior_related_episode_ids: tuple[str, ...] = ()
    closure_reason: str | None = None
    reentry_initiator: str | None = None
    rounds_since_prior: int | None = None

    def __post_init__(self) -> None:
        if not self.episode_id or self.start_ordinal < 0 or self.end_ordinal < self.start_ordinal:
            raise EpisodeError("invalid episode bounds")
        if not self.turn_ids or self.start_ordinal > self.end_ordinal:
            raise EpisodeError("episode must contain turns")
        if self.turn_source_roles and len(self.turn_source_roles) != len(self.turn_ids):
            raise EpisodeError("turn_source_roles must align with turn_ids")
        if any(
            role not in {"external", "model", "mneme", "unknown"}
            for role in self.turn_source_roles
        ):
            raise EpisodeError("unsupported turn source role")
        if self.initiation_role not in {"external", "model", "mneme", "unknown"}:
            raise EpisodeError("unsupported episode initiation role")
        if self.reentry_initiator is not None and self.reentry_initiator not in {
            "external",
            "model",
            "mneme",
            "unknown",
        }:
            raise EpisodeError("unsupported reentry initiator")
        if self.rounds_since_prior is not None and self.rounds_since_prior < 0:
            raise EpisodeError("rounds_since_prior cannot be negative")

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def refractory_active(self) -> bool:
        """Whether model-origin re-entry is inside the two-round window.

        The pure tracker does not invent a global turn clock for callers that
        provide only an immutable arc.  Harnesses that have a close coordinate
        should pass the derived boolean explicitly when constructing an
        Observation.  This conservative default never suppresses evidence.
        """

        return model_reentry_refractory(
            reentry_initiator=self.reentry_initiator,
            rounds_since_prior=self.rounds_since_prior,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "start_ordinal": self.start_ordinal,
            "end_ordinal": self.end_ordinal,
            "turn_ids": list(self.turn_ids),
            "topic_keys": list(self.topic_keys),
            "initiation_role": self.initiation_role,
            "turn_source_roles": list(self.turn_source_roles),
            "relationship_keys": list(self.relationship_keys),
            "outcome_keys": list(self.outcome_keys),
            "prior_related_episode_ids": list(self.prior_related_episode_ids),
            "closure_reason": self.closure_reason,
            "reentry_initiator": self.reentry_initiator,
            "rounds_since_prior": self.rounds_since_prior,
        }


@dataclass
class EpisodeTracker:
    """Group turns with one-turn tangent tolerance and explicit pivots.

    A disjoint topic is held as a pending tangent.  If the next turn returns
    to the current topic, the tangent remains inside the current episode.  If
    the disjoint topic persists, the current arc closes and a new one opens.
    """

    tangent_tolerance: int = 1
    _current: list[ConversationTurn] = field(default_factory=list, init=False)
    _pending: list[ConversationTurn] = field(default_factory=list, init=False)
    _episodes: list[ConversationEpisode] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.tangent_tolerance < 0:
            raise EpisodeError("tangent_tolerance must be non-negative")

    @staticmethod
    def _overlap(left: set[str], right: set[str]) -> bool:
        return bool(left.intersection(right))

    def _current_topics(self) -> set[str]:
        return {topic for turn in self._current for topic in turn.topic_keys}

    def _new_episode(self, turns: list[ConversationTurn], *, closure_reason: str | None) -> None:
        topics = tuple(sorted({topic for turn in turns for topic in turn.topic_keys}))
        relationships = tuple(sorted({item for turn in turns for item in turn.relationship_keys}))
        outcomes = tuple(sorted({item for turn in turns for item in turn.outcome_keys}))
        related = [
            episode
            for episode in self._episodes
            if set(episode.topic_keys).intersection(topics)
        ]
        prior = tuple(episode.episode_id for episode in related)
        reentry = None
        rounds_since_prior = None
        if prior:
            reentry = turns[0].source_role
            # Re-entry timing is relative to the latest related arc, not an
            # intervening unrelated topic.  This keeps the refractory window
            # tied to the association that actually returned.
            previous = related[-1]
            rounds_since_prior = max(0, turns[0].ordinal - previous.end_ordinal - 1)
        episode_id = (
            "conversation:"
            + _digest({"start": turns[0].ordinal, "turns": [turn.turn_id for turn in turns]})[:24]
        )
        self._episodes.append(
            ConversationEpisode(
                episode_id=episode_id,
                start_ordinal=turns[0].ordinal,
                end_ordinal=turns[-1].ordinal,
                turn_ids=tuple(turn.turn_id for turn in turns),
                topic_keys=topics,
                initiation_role=turns[0].source_role,
                turn_source_roles=tuple(turn.source_role for turn in turns),
                relationship_keys=relationships,
                outcome_keys=outcomes,
                prior_related_episode_ids=prior,
                closure_reason=closure_reason,
                reentry_initiator=reentry,
                rounds_since_prior=rounds_since_prior,
            )
        )

    def add(self, turn: ConversationTurn) -> tuple[ConversationEpisode, ...]:
        """Add one turn and return any episode closed by that turn."""

        if self._current and turn.ordinal <= self._current[-1].ordinal:
            raise EpisodeError("turn ordinals must increase")
        topics = set(turn.topic_keys)
        if not self._current:
            self._current.append(turn)
            return ()
        if turn.explicit_pivot:
            self._new_episode(self._current, closure_reason="explicit_pivot")
            self._current = [*self._pending, turn]
            self._pending = []
            return (self._episodes[-1],)
        if self._overlap(self._current_topics(), topics):
            self._current.extend(self._pending)
            self._pending = []
            self._current.append(turn)
            return ()
        self._pending.append(turn)
        if len(self._pending) <= self.tangent_tolerance:
            return ()
        self._new_episode(self._current, closure_reason="topic_pivot")
        closed = self._episodes[-1]
        self._current = list(self._pending)
        self._pending = []
        return (closed,)

    def finish(self) -> tuple[ConversationEpisode, ...]:
        """Close the final arc and return all episode records in order."""

        if self._current:
            self._current.extend(self._pending)
            self._pending = []
            self._new_episode(self._current, closure_reason="end_of_conversation")
            self._current = []
        return tuple(self._episodes)

    @property
    def episodes(self) -> tuple[ConversationEpisode, ...]:
        return tuple(self._episodes)


def model_reentry_refractory(
    *, reentry_initiator: str | None, rounds_since_prior: int | None
) -> bool:
    """Return whether the bounded two-round model-origin debounce is active."""

    return (
        reentry_initiator == "model"
        and rounds_since_prior is not None
        and 0 <= rounds_since_prior <= 2
    )


def persist_conversation_episode(
    store: Any,
    *,
    instance_id: str,
    conversation_id: str,
    ordinal: int,
    episode: ConversationEpisode,
    turn_episode_ids: tuple[tuple[int, str], ...],
    boundary_version: str = "conversation-arc-v1",
) -> None:
    """Publish one immutable arc and its accepted-turn membership.

    Callers persist accepted turn episodes first.  This function owns only the
    small arc ledger and uses one transaction so a partial membership cannot
    be mistaken for a complete arc.
    """

    if not turn_episode_ids:
        raise EpisodeError("an arc must have at least one accepted turn episode")
    if len(turn_episode_ids) != len(episode.turn_ids):
        raise EpisodeError("turn episode membership must align with the arc turns")
    ordinals = tuple(item[0] for item in turn_episode_ids)
    if ordinals != tuple(sorted(ordinals)) or len(set(ordinals)) != len(ordinals):
        raise EpisodeError("turn episode membership ordinals must be sorted and unique")
    connection = store.connection
    payload = json.dumps(
        episode.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    now = datetime.now(UTC).isoformat(timespec="microseconds")
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO conversation_arcs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                episode.episode_id,
                instance_id,
                conversation_id,
                ordinal,
                episode.start_ordinal,
                episode.end_ordinal,
                turn_episode_ids[0][1],
                episode.initiation_role,
                json.dumps(list(episode.topic_keys), ensure_ascii=False),
                json.dumps(list(episode.turn_source_roles), ensure_ascii=False),
                json.dumps(list(episode.outcome_keys), ensure_ascii=False),
                boundary_version,
                episode.digest,
                now,
            ),
        )
        for turn_index, accepted_episode_id in turn_episode_ids:
            connection.execute(
                "INSERT INTO conversation_arc_members VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    episode.episode_id,
                    accepted_episode_id,
                    instance_id,
                    conversation_id,
                    turn_index,
                    json.dumps(list(episode.topic_keys), ensure_ascii=False),
                    "known" if episode.topic_keys else "empty",
                    "arc_tracker_v1",
                    now,
                ),
            )
        connection.execute(
            "INSERT INTO conversation_arc_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f"{episode.episode_id}:open",
                episode.episode_id,
                instance_id,
                conversation_id,
                episode.start_ordinal,
                "OPEN",
                episode.initiation_role,
                episode.prior_related_episode_ids[-1]
                if episode.prior_related_episode_ids
                else None,
                None,
                episode.start_ordinal + 2 if episode.refractory_active else None,
                payload,
                now,
            ),
        )
        if episode.reentry_initiator is not None:
            connection.execute(
                "INSERT INTO conversation_arc_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f"{episode.episode_id}:reentry",
                    episode.episode_id,
                    instance_id,
                    conversation_id,
                    episode.start_ordinal,
                    "REENTRY",
                    episode.reentry_initiator,
                    episode.prior_related_episode_ids[-1]
                    if episode.prior_related_episode_ids
                    else None,
                    None,
                    episode.start_ordinal + 2
                    if episode.refractory_active
                    else None,
                    payload,
                    now,
                ),
            )
        if episode.closure_reason is not None:
            connection.execute(
                "INSERT INTO conversation_arc_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f"{episode.episode_id}:close",
                    episode.episode_id,
                    instance_id,
                    conversation_id,
                    episode.end_ordinal,
                    "CLOSE",
                    None,
                    None,
                    episode.closure_reason,
                    episode.end_ordinal + 2 if episode.reentry_initiator == "model" else None,
                    payload,
                    now,
                ),
            )
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def declared_conversation_arcs(
    turns: Sequence[tuple[int, str]],
    *,
    conversation_id: str,
    source_role: str = "external",
) -> dict[int, ConversationEpisode]:
    """Declare deterministic topic-window arcs for a bounded runner.

    ``turns`` contains immutable ordinal/topic pairs supplied by the
    experiment contract.  The function only groups adjacent equal topics; it
    does not infer open-ended discourse semantics.  Returned values are shared
    by the runner and adapter so the same arc identity is used for persistence
    and learner observations.
    """

    if not conversation_id:
        raise EpisodeError("conversation_id must be non-empty")
    if source_role not in {"external", "model", "mneme", "unknown"}:
        raise EpisodeError("unsupported arc source role")
    if not turns:
        raise EpisodeError("at least one turn is required")
    ordered = tuple(turns)
    if any(ordinal < 0 or not topic for ordinal, topic in ordered):
        raise EpisodeError("arc turn ordinals/topics must be valid")
    if (
        tuple(sorted(ordered)) != ordered
        or len({ordinal for ordinal, _ in ordered}) != len(ordered)
    ):
        raise EpisodeError("arc turns must be ordered and unique")

    groups: list[list[tuple[int, str]]] = []
    for item in ordered:
        if not groups or groups[-1][-1][1] != item[1]:
            groups.append([item])
        else:
            groups[-1].append(item)
    result: dict[int, ConversationEpisode] = {}
    completed: list[ConversationEpisode] = []
    for ordinal, group in enumerate(groups):
        topic = group[0][1]
        related = tuple(
            previous.episode_id
            for previous in completed
            if topic in previous.topic_keys
        )
        previous = next(
            (candidate for candidate in reversed(completed) if candidate.episode_id in related),
            None,
        )
        episode = ConversationEpisode(
            episode_id=f"conversation:{conversation_id}:{ordinal}",
            start_ordinal=group[0][0],
            end_ordinal=group[-1][0],
            turn_ids=tuple(f"{conversation_id}:turn:{turn}" for turn, _ in group),
            topic_keys=(topic,),
            initiation_role=source_role,
            turn_source_roles=tuple(source_role for _ in group),
            prior_related_episode_ids=related,
            closure_reason=("topic_pivot" if ordinal < len(groups) - 1 else "end_of_conversation"),
            reentry_initiator=source_role if related else None,
            rounds_since_prior=(
                max(0, group[0][0] - previous.end_ordinal - 1)
                if previous is not None
                else None
            ),
        )
        completed.append(episode)
        for turn, _ in group:
            result[turn] = episode
    return result


def persist_conversation_arc_progress(
    store: Any,
    *,
    instance_id: str,
    conversation_id: str,
    ordinal: int,
    episode: ConversationEpisode,
    turn_index: int,
    accepted_episode_id: str,
    close: bool = False,
) -> None:
    """Idempotently publish one accepted turn into a predeclared arc.

    Conversation runners know bounded topic-window boundaries before all
    turn-level episode IDs exist.  The arc row is therefore opened on the
    first accepted turn, members are appended as later turns commit, and the
    close event is emitted only at the declared final turn.  Arc rows and
    members remain immutable; retries verify and reuse identical records.
    """

    if turn_index < episode.start_ordinal or turn_index > episode.end_ordinal:
        raise EpisodeError("turn index is outside the declared arc")
    if not accepted_episode_id:
        raise EpisodeError("accepted episode identity must be non-empty")
    connection = store.connection
    payload = json.dumps(
        episode.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    now = datetime.now(UTC).isoformat(timespec="microseconds")
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT instance_id,conversation_id,ordinal,start_turn,end_turn,"
            "start_episode_id,content_digest FROM conversation_arcs WHERE arc_id=?",
            (episode.episode_id,),
        ).fetchone()
        if existing is None:
            connection.execute(
                "INSERT INTO conversation_arcs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    episode.episode_id,
                    instance_id,
                    conversation_id,
                    ordinal,
                    episode.start_ordinal,
                    episode.end_ordinal,
                    accepted_episode_id,
                    episode.initiation_role,
                    json.dumps(list(episode.topic_keys), ensure_ascii=False),
                    json.dumps(list(episode.turn_source_roles), ensure_ascii=False),
                    json.dumps(list(episode.outcome_keys), ensure_ascii=False),
                    "conversation-arc-v1",
                    episode.digest,
                    now,
                ),
            )
            connection.execute(
                "INSERT INTO conversation_arc_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f"{episode.episode_id}:open",
                    episode.episode_id,
                    instance_id,
                    conversation_id,
                    episode.start_ordinal,
                    "OPEN",
                    episode.initiation_role,
                    episode.prior_related_episode_ids[-1]
                    if episode.prior_related_episode_ids
                    else None,
                    None,
                    episode.end_ordinal + 2 if episode.refractory_active else None,
                    payload,
                    now,
                ),
            )
        elif (
            tuple(existing[:5])
            != (
                instance_id,
                conversation_id,
                ordinal,
                episode.start_ordinal,
                episode.end_ordinal,
            )
            or existing[6] != episode.digest
        ):
            raise EpisodeError("existing conversation arc does not match declaration")

        member = connection.execute(
            "SELECT arc_id,episode_id FROM conversation_arc_members "
            "WHERE instance_id=? AND conversation_id=? AND turn_index=?",
            (instance_id, conversation_id, turn_index),
        ).fetchone()
        if member is None:
            connection.execute(
                "INSERT INTO conversation_arc_members VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    episode.episode_id,
                    accepted_episode_id,
                    instance_id,
                    conversation_id,
                    turn_index,
                    json.dumps(list(episode.topic_keys), ensure_ascii=False),
                    "known",
                    "arc_tracker_v1",
                    now,
                ),
            )
        elif tuple(member) != (episode.episode_id, accepted_episode_id):
            raise EpisodeError("conversation turn is bound to a different arc member")

        if close:
            close_event = connection.execute(
                "SELECT 1 FROM conversation_arc_events WHERE event_id=?",
                (f"{episode.episode_id}:close",),
            ).fetchone()
            if close_event is None:
                connection.execute(
                    "INSERT INTO conversation_arc_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        f"{episode.episode_id}:close",
                        episode.episode_id,
                        instance_id,
                        conversation_id,
                        episode.end_ordinal,
                        "CLOSE",
                        None,
                        None,
                        episode.closure_reason or "declared_window_end",
                        episode.end_ordinal + 2
                        if episode.reentry_initiator == "model"
                        else None,
                        payload,
                        now,
                    ),
                )
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


__all__ = [
    "ConversationEpisode",
    "ConversationTurn",
    "EpisodeError",
    "EpisodeTracker",
    "declared_conversation_arcs",
    "model_reentry_refractory",
    "persist_conversation_episode",
    "persist_conversation_arc_progress",
]
