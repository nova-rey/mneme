from mneme.contracts import GenerationRequest
from mneme.development import (
    ConversationTurn,
    EpisodeTracker,
    declared_conversation_arcs,
    model_reentry_refractory,
    persist_conversation_arc_progress,
    persist_conversation_episode,
)
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.storage import SQLiteStore


def _turn(
    ordinal: int, topic: str, role: str = "external", *, pivot: bool = False
) -> ConversationTurn:
    return ConversationTurn(
        turn_id=f"t{ordinal}",
        ordinal=ordinal,
        topic_keys=(topic,),
        source_role=role,
        explicit_pivot=pivot,
    )


def test_consecutive_subject_turns_form_one_episode() -> None:
    tracker = EpisodeTracker()
    for ordinal in range(5):
        assert (
            tracker.add(_turn(ordinal, "basil", "external" if ordinal % 2 == 0 else "model")) == ()
        )
    episodes = tracker.finish()
    assert len(episodes) == 1
    assert episodes[0].start_ordinal == 0
    assert episodes[0].end_ordinal == 4
    assert episodes[0].turn_ids == tuple(f"t{i}" for i in range(5))


def test_one_turn_tangent_does_not_close_episode_but_persistent_pivot_does() -> None:
    tracker = EpisodeTracker()
    tracker.add(_turn(0, "basil"))
    tracker.add(_turn(1, "travel"))
    closed = tracker.add(_turn(2, "cooking"))
    tracker.add(_turn(3, "cooking"))
    assert len(closed) == 1
    assert closed[0].topic_keys == ("basil",)
    episodes = tracker.finish()
    assert len(episodes) == 2
    assert set(episodes[1].topic_keys) == {"travel", "cooking"}


def test_external_reentry_is_not_refractory() -> None:
    tracker = EpisodeTracker()
    tracker.add(_turn(0, "basil", "external"))
    tracker.add(_turn(1, "travel", "external"))
    tracker.add(_turn(2, "travel", "external"))
    tracker.add(_turn(3, "basil", "external"))
    tracker.add(_turn(4, "basil", "external"))
    episodes = tracker.finish()
    assert len(episodes) == 3
    reentry = episodes[-1]
    assert reentry.reentry_initiator == "external"
    assert not reentry.refractory_active


def test_model_reentry_uses_bounded_two_round_refractory() -> None:
    assert model_reentry_refractory(reentry_initiator="model", rounds_since_prior=0)
    assert model_reentry_refractory(reentry_initiator="model", rounds_since_prior=2)
    assert not model_reentry_refractory(reentry_initiator="model", rounds_since_prior=3)
    assert not model_reentry_refractory(reentry_initiator="external", rounds_since_prior=1)


def test_reentry_rounds_are_measured_from_latest_related_arc() -> None:
    tracker = EpisodeTracker()
    tracker.add(_turn(0, "basil", "external"))
    tracker.add(_turn(1, "travel", "external"))
    tracker.add(_turn(2, "travel", "external"))
    tracker.add(_turn(3, "basil", "model"))
    tracker.add(_turn(4, "basil", "model"))
    episodes = tracker.finish()
    reentry = episodes[-1]
    assert reentry.reentry_initiator == "model"
    assert reentry.prior_related_episode_ids == (episodes[0].episode_id,)
    assert reentry.rounds_since_prior == 2
    assert reentry.refractory_active


def test_episode_replay_is_deterministic_and_accepts_unknown_role() -> None:
    turns = (
        _turn(0, "basil", "unknown"),
        _turn(1, "basil", "external"),
        _turn(2, "travel", "model"),
        _turn(3, "travel", "model"),
    )
    first = EpisodeTracker()
    second = EpisodeTracker()
    for turn in turns:
        first.add(turn)
        second.add(turn)
    assert tuple(item.to_dict() for item in first.finish()) == tuple(
        item.to_dict() for item in second.finish()
    )


def test_arc_persistence_is_atomic_and_inspectable(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "arcs.sqlite3")
    instance = store.create_root(permissions=StoragePermissions(store=True))
    host = FakeHost()
    continuity = ContinuityService(store, instance, host)
    operation = continuity.prepare_episode(
        GenerationRequest(({"role": "user", "content": "The basil needs water."},)),
        operation_id="arc-generation",
    )
    continuity.generate_operation(operation.operation_id)
    accepted = continuity.accept_episode(operation.operation_id)
    tracker = EpisodeTracker()
    tracker.add(
        ConversationTurn(
            turn_id="t0",
            ordinal=0,
            topic_keys=("basil",),
            source_role="external",
            outcome_keys=("basil-survived",),
        )
    )
    arc = tracker.finish()[0]
    with store:
        persist_conversation_episode(
            store,
            instance_id=instance,
            conversation_id="conversation-1",
            ordinal=0,
            episode=arc,
            turn_episode_ids=((0, accepted.episode_id),),
        )
        assert store.connection.execute("SELECT COUNT(*) FROM conversation_arcs").fetchone()[0] == 1
        assert (
            store.connection.execute("SELECT COUNT(*) FROM conversation_arc_members").fetchone()[0]
            == 1
        )
        assert (
            store.connection.execute("SELECT COUNT(*) FROM conversation_arc_events").fetchone()[0]
            == 2
        )
        row = store.connection.execute(
            "SELECT start_turn,end_turn,source_roles_json,outcome_keys_json FROM conversation_arcs"
        ).fetchone()
        assert row[0] == 0
        assert row[1] == 0
        assert row[2] == '["external"]'
        assert row[3] == '["basil-survived"]'
    store.close()


def test_declared_conversation_arcs_group_windows_and_record_pivots() -> None:
    arcs = declared_conversation_arcs(
        ((0, "basil"), (1, "basil"), (2, "travel"), (3, "travel"), (4, "basil")),
        conversation_id="thread-a",
    )
    assert arcs[0].episode_id == arcs[1].episode_id
    assert arcs[0].start_ordinal == 0
    assert arcs[0].end_ordinal == 1
    assert arcs[2].closure_reason == "topic_pivot"
    assert arcs[4].prior_related_episode_ids == (arcs[0].episode_id,)
    assert arcs[4].reentry_initiator == "external"
    assert arcs[4].rounds_since_prior == 2


def test_arc_progress_is_idempotent_across_turn_retries(tmp_path) -> None:
    with SQLiteStore(tmp_path / "progress.sqlite3") as store:
        instance = store.create_root(permissions=StoragePermissions(store=True))
        service = ContinuityService(store, instance, FakeHost())
        accepted_ids: list[str] = []
        for ordinal in range(2):
            operation = service.prepare_episode(
                GenerationRequest(({"role": "user", "content": f"basil {ordinal}"},)),
                operation_id=f"progress-{ordinal}",
            )
            service.generate_operation(operation.operation_id)
            accepted_ids.append(service.accept_episode(operation.operation_id).episode_id)
        arcs = declared_conversation_arcs(
            ((0, "basil"), (1, "basil")), conversation_id="thread-b"
        )
        arc = arcs[0]
        for turn, accepted_id in enumerate(accepted_ids):
            persist_conversation_arc_progress(
                store,
                instance_id=instance,
                conversation_id="thread-b",
                ordinal=0,
                episode=arc,
                turn_index=turn,
                accepted_episode_id=accepted_id,
                close=turn == 1,
            )
            # A retry after an uncertain caller outcome must be a no-op.
            persist_conversation_arc_progress(
                store,
                instance_id=instance,
                conversation_id="thread-b",
                ordinal=0,
                episode=arc,
                turn_index=turn,
                accepted_episode_id=accepted_id,
                close=turn == 1,
            )
        assert store.connection.execute(
            "SELECT COUNT(*) FROM conversation_arcs WHERE arc_id=?", (arc.episode_id,)
        ).fetchone()[0] == 1
        assert store.connection.execute(
            "SELECT COUNT(*) FROM conversation_arc_members WHERE arc_id=?", (arc.episode_id,)
        ).fetchone()[0] == 2
        assert store.connection.execute(
            "SELECT COUNT(*) FROM conversation_arc_events WHERE arc_id=?", (arc.episode_id,)
        ).fetchone()[0] == 2
