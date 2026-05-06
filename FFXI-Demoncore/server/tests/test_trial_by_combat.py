"""Tests for trial_by_combat."""
from __future__ import annotations

from server.trial_by_combat import (
    DuelStatus,
    StakeKind,
    TrialByCombatRegistry,
)


def test_issue_happy():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.GIL, stake_payload="50000",
        issued_at=10, expires_at=100,
    )
    assert cid == "duel_1"


def test_self_challenge_blocked():
    r = TrialByCombatRegistry()
    out = r.issue_challenge(
        challenger_id="alice", defender_id="alice",
        stake_kind=StakeKind.GIL, stake_payload="100",
        issued_at=10, expires_at=100,
    )
    assert out == ""


def test_blank_party_blocked():
    r = TrialByCombatRegistry()
    out = r.issue_challenge(
        challenger_id="", defender_id="bob",
        stake_kind=StakeKind.GIL, stake_payload="100",
        issued_at=10, expires_at=100,
    )
    assert out == ""


def test_expires_before_issued_blocked():
    r = TrialByCombatRegistry()
    out = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.GIL, stake_payload="100",
        issued_at=100, expires_at=50,
    )
    assert out == ""


def test_blank_payload_blocked_for_non_honor():
    r = TrialByCombatRegistry()
    out = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.GIL, stake_payload="",
        issued_at=10, expires_at=100,
    )
    assert out == ""


def test_honor_stake_allows_blank_payload():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    assert cid != ""


def test_accept_happy():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    assert r.accept(challenge_id=cid, accepted_at=20) is True
    d = r.get(challenge_id=cid)
    assert d is not None
    assert d.status == DuelStatus.SCHEDULED


def test_accept_after_expiry_cancels():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    out = r.accept(challenge_id=cid, accepted_at=200)
    assert out is False
    d = r.get(challenge_id=cid)
    assert d is not None
    assert d.status == DuelStatus.CANCELLED


def test_decline_happy():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    assert r.decline(challenge_id=cid, declined_at=20) is True
    d = r.get(challenge_id=cid)
    assert d is not None
    assert d.status == DuelStatus.CANCELLED


def test_decline_after_accept_blocked():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    r.accept(challenge_id=cid, accepted_at=20)
    out = r.decline(challenge_id=cid, declined_at=30)
    assert out is False


def test_record_outcome_winner():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.GIL, stake_payload="100",
        issued_at=10, expires_at=100,
    )
    r.accept(challenge_id=cid, accepted_at=20)
    ok = r.record_outcome(
        challenge_id=cid, winner_id="alice", loser_id="bob",
        recorded_at=50,
    )
    assert ok is True
    d = r.get(challenge_id=cid)
    assert d is not None
    assert d.status == DuelStatus.RESOLVED
    assert d.winner_id == "alice"


def test_record_outcome_draw():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    r.accept(challenge_id=cid, accepted_at=20)
    ok = r.record_outcome(
        challenge_id=cid, winner_id=None, loser_id=None,
        recorded_at=50, draw=True,
    )
    assert ok is True
    d = r.get(challenge_id=cid)
    assert d is not None
    assert d.is_draw is True
    assert d.status == DuelStatus.RESOLVED


def test_record_outcome_outsider_blocked():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    r.accept(challenge_id=cid, accepted_at=20)
    out = r.record_outcome(
        challenge_id=cid, winner_id="carol", loser_id="alice",
        recorded_at=50,
    )
    assert out is False


def test_record_outcome_before_accept_blocked():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    out = r.record_outcome(
        challenge_id=cid, winner_id="alice", loser_id="bob",
        recorded_at=50,
    )
    assert out is False


def test_forfeit_pending():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    ok = r.forfeit(
        challenge_id=cid, forfeit_by="alice", forfeit_at=30,
    )
    assert ok is True
    d = r.get(challenge_id=cid)
    assert d is not None
    assert d.status == DuelStatus.FORFEITED
    assert d.loser_id == "alice"
    assert d.winner_id == "bob"


def test_forfeit_outsider_blocked():
    r = TrialByCombatRegistry()
    cid = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    out = r.forfeit(
        challenge_id=cid, forfeit_by="carol", forfeit_at=30,
    )
    assert out is False


def test_pending_for_filters_only_pending():
    r = TrialByCombatRegistry()
    a = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    b = r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=11, expires_at=100,
    )
    r.accept(challenge_id=a, accepted_at=20)  # a now scheduled
    pending = r.pending_for(player_id="alice")
    assert len(pending) == 1
    assert pending[0].challenge_id == b


def test_duels_for_player_finds_both_sides():
    r = TrialByCombatRegistry()
    r.issue_challenge(
        challenger_id="alice", defender_id="bob",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=10, expires_at=100,
    )
    r.issue_challenge(
        challenger_id="bob", defender_id="alice",
        stake_kind=StakeKind.HONOR, stake_payload="",
        issued_at=20, expires_at=200,
    )
    alice = r.duels_for_player(player_id="alice")
    assert len(alice) == 2
