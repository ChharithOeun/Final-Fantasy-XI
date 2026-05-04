"""Tests for shadowlands endgame quests."""
from __future__ import annotations

from server.shadowlands_endgame_quests import (
    QuestId,
    QuestStatus,
    ShadowlandsEndgameQuests,
    StepKind,
)


def _accept_first(s: ShadowlandsEndgameQuests):
    return s.accept(
        player_id="alice", account_id="acct_alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )


def test_accept_first_proof():
    s = ShadowlandsEndgameQuests()
    res = _accept_first(s)
    assert res.accepted


def test_accept_double_rejected():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    res = _accept_first(s)
    assert not res.accepted


def test_accept_second_before_first_rejected():
    s = ShadowlandsEndgameQuests()
    res = s.accept(
        player_id="alice", account_id="acct_alice",
        quest_id=QuestId.THE_SECOND_PROOF,
    )
    assert not res.accepted


def test_accept_third_before_second_rejected():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    s.advance_step(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
        step=StepKind.ACCEPT_TARGET,
    )
    s.advance_step(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
        step=StepKind.LOCATE_TARGET,
    )
    s.advance_step(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
        step=StepKind.SPARE_TARGET,
    )
    s.complete(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    # First done — but try jumping to third without second
    res = s.accept(
        player_id="alice", account_id="acct_alice",
        quest_id=QuestId.THE_THIRD_PROOF,
    )
    assert not res.accepted


def test_advance_step_in_order():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    res = s.advance_step(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
        step=StepKind.ACCEPT_TARGET,
    )
    assert res.accepted


def test_advance_step_out_of_order_rejected():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    res = s.advance_step(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
        step=StepKind.SPARE_TARGET,
    )
    assert not res.accepted
    assert "out of order" in res.reason


def test_advance_step_wrong_quest_rejected():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    res = s.advance_step(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
        step=StepKind.REFUSE_REWARD,    # belongs to second proof
    )
    assert not res.accepted


def test_advance_step_unaccepted_rejected():
    s = ShadowlandsEndgameQuests()
    res = s.advance_step(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
        step=StepKind.ACCEPT_TARGET,
    )
    assert not res.accepted
    assert "not accepted" in res.reason


def test_advance_already_complete_rejected():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    for step in (
        StepKind.ACCEPT_TARGET,
        StepKind.LOCATE_TARGET,
        StepKind.SPARE_TARGET,
    ):
        s.advance_step(
            player_id="alice",
            quest_id=QuestId.THE_FIRST_PROOF,
            step=step,
        )
    s.complete(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    res = s.advance_step(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
        step=StepKind.ACCEPT_TARGET,
    )
    assert not res.accepted


def test_complete_with_all_steps():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    for step in (
        StepKind.ACCEPT_TARGET,
        StepKind.LOCATE_TARGET,
        StepKind.SPARE_TARGET,
    ):
        s.advance_step(
            player_id="alice",
            quest_id=QuestId.THE_FIRST_PROOF,
            step=step,
        )
    res = s.complete(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    assert res.accepted


def test_complete_without_steps_rejected():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    res = s.complete(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    assert not res.accepted


def test_complete_unaccepted_rejected():
    s = ShadowlandsEndgameQuests()
    res = s.complete(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    assert not res.accepted


def test_can_complete_flag():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    assert not s.can_complete(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    for step in (
        StepKind.ACCEPT_TARGET,
        StepKind.LOCATE_TARGET,
        StepKind.SPARE_TARGET,
    ):
        s.advance_step(
            player_id="alice",
            quest_id=QuestId.THE_FIRST_PROOF,
            step=step,
        )
    assert s.can_complete(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )


def test_gate_callback_invoked():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    for step in (
        StepKind.ACCEPT_TARGET,
        StepKind.LOCATE_TARGET,
        StepKind.SPARE_TARGET,
    ):
        s.advance_step(
            player_id="alice",
            quest_id=QuestId.THE_FIRST_PROOF,
            step=step,
        )
    captured: list[tuple[str, str]] = []

    def cb(account_id, quest_id):
        captured.append((account_id, quest_id))
        return True

    s.complete(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
        gate_callback=cb,
    )
    assert captured == [
        ("acct_alice", "shadowlands_proof_1"),
    ]


def test_progress_for_unknown_returns_none():
    s = ShadowlandsEndgameQuests()
    assert s.progress_for(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    ) is None


def test_progress_recorded_after_accept():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    prog = s.progress_for(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    assert prog is not None
    assert prog.status == QuestStatus.IN_PROGRESS


def test_full_chain_progression():
    s = ShadowlandsEndgameQuests()
    # First proof
    s.accept(
        player_id="alice", account_id="acct",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    for step in (
        StepKind.ACCEPT_TARGET,
        StepKind.LOCATE_TARGET,
        StepKind.SPARE_TARGET,
    ):
        s.advance_step(
            player_id="alice",
            quest_id=QuestId.THE_FIRST_PROOF,
            step=step,
        )
    s.complete(
        player_id="alice",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    # Second proof
    s.accept(
        player_id="alice", account_id="acct",
        quest_id=QuestId.THE_SECOND_PROOF,
    )
    for step in (
        StepKind.REFUSE_REWARD,
        StepKind.WALK_AWAY,
    ):
        s.advance_step(
            player_id="alice",
            quest_id=QuestId.THE_SECOND_PROOF,
            step=step,
        )
    s.complete(
        player_id="alice",
        quest_id=QuestId.THE_SECOND_PROOF,
    )
    # Third proof now allowed
    res = s.accept(
        player_id="alice", account_id="acct",
        quest_id=QuestId.THE_THIRD_PROOF,
    )
    assert res.accepted


def test_per_player_isolation():
    s = ShadowlandsEndgameQuests()
    s.accept(
        player_id="alice", account_id="a",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    s.accept(
        player_id="bob", account_id="b",
        quest_id=QuestId.THE_FIRST_PROOF,
    )
    assert s.total_progress() == 2


def test_total_progress():
    s = ShadowlandsEndgameQuests()
    _accept_first(s)
    assert s.total_progress() == 1
