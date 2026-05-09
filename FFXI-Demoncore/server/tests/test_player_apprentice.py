"""Tests for player_apprentice."""
from __future__ import annotations

from server.player_apprentice import (
    PlayerApprenticeSystem, BondState, EndReason,
)


def test_propose_happy():
    s = PlayerApprenticeSystem()
    assert s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    ) is not None


def test_propose_self_blocked():
    s = PlayerApprenticeSystem()
    assert s.propose(
        mentor_id="x", apprentice_id="x",
        proposed_day=10,
    ) is None


def test_propose_blank():
    s = PlayerApprenticeSystem()
    assert s.propose(
        mentor_id="", apprentice_id="cara",
        proposed_day=10,
    ) is None


def test_propose_dup_apprentice_blocked():
    s = PlayerApprenticeSystem()
    s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    assert s.propose(
        mentor_id="dave", apprentice_id="cara",
        proposed_day=11,
    ) is None


def test_accept_happy():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    assert s.accept(bond_id=bid, now_day=11) is True


def test_accept_double_blocked():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.accept(bond_id=bid, now_day=11)
    assert s.accept(
        bond_id=bid, now_day=12,
    ) is False


def test_accept_before_proposed_blocked():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    assert s.accept(bond_id=bid, now_day=5) is False


def test_graduate():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.accept(bond_id=bid, now_day=11)
    assert s.graduate(
        bond_id=bid, now_day=200,
    ) is True
    b = s.bond(bond_id=bid)
    assert b.state == BondState.GRADUATED
    assert b.mentor_rep_delta == 200


def test_graduate_unaccepted_blocked():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    assert s.graduate(
        bond_id=bid, now_day=200,
    ) is False


def test_dissolve_mutual():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.accept(bond_id=bid, now_day=11)
    assert s.dissolve(
        bond_id=bid, now_day=50,
        reason=EndReason.MUTUAL_AGREEMENT,
    ) is True
    assert s.bond(
        bond_id=bid,
    ).mentor_rep_delta == 50


def test_dissolve_invalid_reason():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.accept(bond_id=bid, now_day=11)
    assert s.dissolve(
        bond_id=bid, now_day=50,
        reason=EndReason.LEVEL_THRESHOLD,
    ) is False


def test_dissolve_proposed_no_rep():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.dissolve(
        bond_id=bid, now_day=15,
        reason=EndReason.MENTOR_RELEASED,
    )
    assert s.bond(
        bond_id=bid,
    ).mentor_rep_delta == 0


def test_abandon():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.accept(bond_id=bid, now_day=11)
    assert s.abandon(
        bond_id=bid, now_day=200,
    ) is True
    assert s.bond(
        bond_id=bid,
    ).mentor_rep_delta == -25


def test_abandon_proposed_blocked():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    assert s.abandon(
        bond_id=bid, now_day=200,
    ) is False


def test_active_bond_for_apprentice():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.accept(bond_id=bid, now_day=11)
    b = s.active_bond_for_apprentice(
        apprentice_id="cara",
    )
    assert b is not None
    assert b.bond_id == bid


def test_active_bond_after_graduate_none():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.accept(bond_id=bid, now_day=11)
    s.graduate(bond_id=bid, now_day=200)
    assert s.active_bond_for_apprentice(
        apprentice_id="cara",
    ) is None


def test_propose_after_dissolve_ok():
    s = PlayerApprenticeSystem()
    bid = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.accept(bond_id=bid, now_day=11)
    s.dissolve(
        bond_id=bid, now_day=50,
        reason=EndReason.MUTUAL_AGREEMENT,
    )
    new_bid = s.propose(
        mentor_id="dave", apprentice_id="cara",
        proposed_day=60,
    )
    assert new_bid is not None


def test_total_mentor_rep_aggregates():
    s = PlayerApprenticeSystem()
    bid_a = s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.accept(bond_id=bid_a, now_day=11)
    s.graduate(bond_id=bid_a, now_day=100)
    bid_b = s.propose(
        mentor_id="bob", apprentice_id="dave",
        proposed_day=110,
    )
    s.accept(bond_id=bid_b, now_day=111)
    s.abandon(bond_id=bid_b, now_day=300)
    # 200 graduation - 25 abandon = 175
    assert s.total_mentor_rep(
        mentor_id="bob",
    ) == 175


def test_bonds_for_mentor():
    s = PlayerApprenticeSystem()
    s.propose(
        mentor_id="bob", apprentice_id="cara",
        proposed_day=10,
    )
    s.propose(
        mentor_id="bob", apprentice_id="dave",
        proposed_day=11,
    )
    s.propose(
        mentor_id="other", apprentice_id="ed",
        proposed_day=12,
    )
    out = s.bonds_for_mentor(mentor_id="bob")
    assert len(out) == 2


def test_bond_unknown():
    s = PlayerApprenticeSystem()
    assert s.bond(bond_id="ghost") is None


def test_enum_counts():
    assert len(list(BondState)) == 5
    assert len(list(EndReason)) == 5
