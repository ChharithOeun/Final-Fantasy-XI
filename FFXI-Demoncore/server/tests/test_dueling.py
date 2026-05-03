"""Tests for the dueling registry."""
from __future__ import annotations

from server.dueling import (
    CHALLENGE_TIMEOUT_SECONDS,
    DUEL_MAX_DURATION_SECONDS,
    DuelOutcome,
    DuelRegistry,
    DuelStakesKind,
    DuelState,
)


def test_challenge_self_rejected():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="alice",
    )
    assert not res.accepted


def test_challenge_creates_duel():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    assert res.accepted
    d = reg.get(res.duel_id)
    assert d is not None
    assert d.state == DuelState.PROPOSED


def test_challenge_blocks_party_in_open_duel():
    reg = DuelRegistry()
    reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    # Alice can't challenge another while open
    res = reg.challenge(
        challenger_id="alice", defender_id="charlie",
    )
    assert not res.accepted
    # Bob can't be challenged again either
    res2 = reg.challenge(
        challenger_id="dave", defender_id="bob",
    )
    assert not res2.accepted


def test_gil_stake_must_be_positive():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
        stakes_kind=DuelStakesKind.GIL,
        stakes_amount=0,
    )
    assert not res.accepted


def test_accept_moves_to_accepted():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
        now_seconds=0.0,
    )
    assert reg.accept(
        duel_id=res.duel_id, defender_id="bob",
        now_seconds=10.0,
    )
    assert reg.get(res.duel_id).state == DuelState.ACCEPTED


def test_accept_wrong_defender_rejected():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    assert not reg.accept(
        duel_id=res.duel_id, defender_id="charlie",
        now_seconds=10.0,
    )


def test_accept_after_timeout_expires():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
        now_seconds=0.0,
    )
    assert not reg.accept(
        duel_id=res.duel_id, defender_id="bob",
        now_seconds=CHALLENGE_TIMEOUT_SECONDS + 1,
    )
    assert reg.get(res.duel_id).state == DuelState.EXPIRED


def test_decline_moves_to_declined():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    assert reg.decline(
        duel_id=res.duel_id, defender_id="bob",
    )
    assert reg.get(res.duel_id).state == DuelState.DECLINED


def test_start_fight_after_accept():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
        now_seconds=0.0,
    )
    reg.accept(
        duel_id=res.duel_id, defender_id="bob",
        now_seconds=10.0,
    )
    assert reg.start_fight(
        duel_id=res.duel_id, now_seconds=20.0,
    )
    assert reg.get(res.duel_id).state == DuelState.LIVE


def test_start_fight_without_accept_rejected():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    assert not reg.start_fight(
        duel_id=res.duel_id, now_seconds=20.0,
    )


def test_resolve_records_winner():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    reg.accept(
        duel_id=res.duel_id, defender_id="bob",
        now_seconds=10.0,
    )
    reg.start_fight(duel_id=res.duel_id, now_seconds=20.0)
    assert reg.resolve(
        duel_id=res.duel_id, winner_id="alice",
        outcome=DuelOutcome.WIN, now_seconds=200.0,
    )
    d = reg.get(res.duel_id)
    assert d.state == DuelState.FINISHED
    assert d.winner_id == "alice"
    assert d.outcome == DuelOutcome.WIN


def test_resolve_unknown_winner_rejected():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    reg.accept(
        duel_id=res.duel_id, defender_id="bob",
        now_seconds=10.0,
    )
    reg.start_fight(duel_id=res.duel_id, now_seconds=20.0)
    assert not reg.resolve(
        duel_id=res.duel_id, winner_id="charlie",
        outcome=DuelOutcome.WIN, now_seconds=100.0,
    )


def test_forfeit_makes_other_winner():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    reg.accept(
        duel_id=res.duel_id, defender_id="bob",
        now_seconds=10.0,
    )
    reg.start_fight(duel_id=res.duel_id, now_seconds=20.0)
    assert reg.forfeit(
        duel_id=res.duel_id, forfeiting_id="alice",
        now_seconds=100.0,
    )
    d = reg.get(res.duel_id)
    assert d.winner_id == "bob"
    assert d.outcome == DuelOutcome.FORFEIT


def test_double_ko_outcome():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    reg.accept(
        duel_id=res.duel_id, defender_id="bob",
        now_seconds=10.0,
    )
    reg.start_fight(duel_id=res.duel_id, now_seconds=20.0)
    reg.resolve(
        duel_id=res.duel_id, winner_id=None,
        outcome=DuelOutcome.DOUBLE_KO, now_seconds=200.0,
    )
    d = reg.get(res.duel_id)
    assert d.outcome == DuelOutcome.DOUBLE_KO
    assert d.winner_id is None


def test_expire_old_proposes_to_expired():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
        now_seconds=0.0,
    )
    expired = reg.expire_old(
        now_seconds=CHALLENGE_TIMEOUT_SECONDS + 100,
    )
    assert expired == 1
    assert reg.get(res.duel_id).state == DuelState.EXPIRED


def test_expire_old_timeout_long_fight():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    reg.accept(
        duel_id=res.duel_id, defender_id="bob",
        now_seconds=10.0,
    )
    reg.start_fight(duel_id=res.duel_id, now_seconds=20.0)
    expired = reg.expire_old(
        now_seconds=20.0 + DUEL_MAX_DURATION_SECONDS + 1,
    )
    assert expired == 1
    d = reg.get(res.duel_id)
    assert d.state == DuelState.FINISHED
    assert d.outcome == DuelOutcome.TIMEOUT


def test_open_duels_for_lists_active():
    reg = DuelRegistry()
    res1 = reg.challenge(
        challenger_id="alice", defender_id="bob",
    )
    open_for_alice = reg.open_duels_for("alice")
    assert len(open_for_alice) == 1
    # Decline -> closed
    reg.decline(
        duel_id=res1.duel_id, defender_id="bob",
    )
    open_for_alice_after = reg.open_duels_for("alice")
    assert len(open_for_alice_after) == 0


def test_full_lifecycle_honor_duel():
    """Alice challenges Bob; Bob accepts; fight; Alice wins."""
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
        stakes_kind=DuelStakesKind.HONOR,
        now_seconds=0.0,
    )
    assert reg.accept(
        duel_id=res.duel_id, defender_id="bob",
        now_seconds=10.0,
    )
    assert reg.start_fight(
        duel_id=res.duel_id, now_seconds=20.0,
    )
    assert reg.resolve(
        duel_id=res.duel_id, winner_id="alice",
        outcome=DuelOutcome.WIN, now_seconds=180.0,
    )
    d = reg.get(res.duel_id)
    assert d.state == DuelState.FINISHED
    assert d.winner_id == "alice"


def test_full_lifecycle_gil_wager():
    reg = DuelRegistry()
    res = reg.challenge(
        challenger_id="alice", defender_id="bob",
        stakes_kind=DuelStakesKind.GIL,
        stakes_amount=10000,
        now_seconds=0.0,
    )
    assert res.accepted
    d = reg.get(res.duel_id)
    assert d.stakes_amount == 10000
    assert d.stakes_kind == DuelStakesKind.GIL
