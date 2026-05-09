"""Tests for npc_oath_chain."""
from __future__ import annotations

from server.npc_oath_chain import (
    NPCOathChainSystem, BondStrength,
    CascadeOutcome,
)


def _swear(s, **overrides):
    args = dict(
        liege_id="off_volker",
        sworn_id="off_squire",
        strength=BondStrength.BOUND,
        sworn_day=10,
    )
    args.update(overrides)
    return s.swear_oath(**args)


def test_swear_happy():
    s = NPCOathChainSystem()
    assert _swear(s) is not None


def test_swear_self_blocked():
    s = NPCOathChainSystem()
    assert _swear(
        s, liege_id="x", sworn_id="x",
    ) is None


def test_swear_blank():
    s = NPCOathChainSystem()
    assert _swear(s, liege_id="") is None


def test_swear_dup_active_blocked():
    s = NPCOathChainSystem()
    _swear(s)
    assert _swear(s) is None


def test_swear_after_break_ok():
    s = NPCOathChainSystem()
    bid = _swear(s)
    s.break_oath(bond_id=bid, now_day=20)
    assert _swear(s, sworn_day=30) is not None


def test_break_oath():
    s = NPCOathChainSystem()
    bid = _swear(s)
    assert s.break_oath(
        bond_id=bid, now_day=20,
    ) is True


def test_break_double_blocked():
    s = NPCOathChainSystem()
    bid = _swear(s)
    s.break_oath(bond_id=bid, now_day=20)
    assert s.break_oath(
        bond_id=bid, now_day=21,
    ) is False


def test_active_bonds_to_liege():
    s = NPCOathChainSystem()
    _swear(s, liege_id="L", sworn_id="a")
    _swear(s, liege_id="L", sworn_id="b")
    _swear(s, liege_id="L2", sworn_id="c")
    out = s.active_bonds_to_liege(liege_id="L")
    assert len(out) == 2


def test_resolve_blood_oath_follows():
    s = NPCOathChainSystem()
    bid = _swear(
        s, strength=BondStrength.BLOOD_OATH,
    )
    res = s.resolve_cascade(
        bond_id=bid,
        sworn_loyalty_to_current=20,
        sworn_grievance_score=10,
        seed=5, now_day=400,
    )
    # pull: 60 + 10 + 5 = 75
    # stay: 20 + 0 = 20
    # diff 55 > 15 -> FOLLOWED
    assert res == CascadeOutcome.FOLLOWED


def test_resolve_loose_high_loyalty_stays():
    s = NPCOathChainSystem()
    bid = _swear(
        s, strength=BondStrength.LOOSE,
    )
    res = s.resolve_cascade(
        bond_id=bid,
        sworn_loyalty_to_current=90,
        sworn_grievance_score=0,
        seed=0, now_day=400,
    )
    # pull: 10 + 0 + 0 = 10
    # stay: 90 + 0 = 90 -> 80 diff -> STAYED
    assert res == CascadeOutcome.STAYED


def test_resolve_middle_ambivalent():
    s = NPCOathChainSystem()
    bid = _swear(
        s, strength=BondStrength.BOUND,
    )
    res = s.resolve_cascade(
        bond_id=bid,
        sworn_loyalty_to_current=40,
        sworn_grievance_score=5,
        seed=2, now_day=400,
    )
    # pull: 30 + 5 + 2 = 37
    # stay: 40 + 0 = 40
    # diff 3 -> AMBIVALENT
    assert res == CascadeOutcome.AMBIVALENT


def test_resolve_invalid_loyalty():
    s = NPCOathChainSystem()
    bid = _swear(s)
    res = s.resolve_cascade(
        bond_id=bid,
        sworn_loyalty_to_current=200,
        sworn_grievance_score=0,
        seed=0, now_day=400,
    )
    assert res is None


def test_resolve_negative_grievance_blocked():
    s = NPCOathChainSystem()
    bid = _swear(s)
    res = s.resolve_cascade(
        bond_id=bid,
        sworn_loyalty_to_current=50,
        sworn_grievance_score=-1,
        seed=0, now_day=400,
    )
    assert res is None


def test_resolve_broken_oath_blocked():
    s = NPCOathChainSystem()
    bid = _swear(s)
    s.break_oath(bond_id=bid, now_day=20)
    res = s.resolve_cascade(
        bond_id=bid,
        sworn_loyalty_to_current=50,
        sworn_grievance_score=0,
        seed=0, now_day=400,
    )
    assert res is None


def test_resolve_unknown_bond():
    s = NPCOathChainSystem()
    res = s.resolve_cascade(
        bond_id="ghost",
        sworn_loyalty_to_current=50,
        sworn_grievance_score=0,
        seed=0, now_day=400,
    )
    assert res is None


def test_followers_of_liege():
    s = NPCOathChainSystem()
    bid_a = _swear(
        s, sworn_id="a",
        strength=BondStrength.BLOOD_OATH,
    )
    bid_b = _swear(
        s, sworn_id="b",
        strength=BondStrength.LOOSE,
    )
    s.resolve_cascade(
        bond_id=bid_a,
        sworn_loyalty_to_current=20,
        sworn_grievance_score=10, seed=5,
        now_day=400,
    )
    s.resolve_cascade(
        bond_id=bid_b,
        sworn_loyalty_to_current=90,
        sworn_grievance_score=0, seed=0,
        now_day=400,
    )
    followers = s.followers_of(
        liege_id="off_volker",
    )
    assert "a" in followers
    assert "b" not in followers


def test_cascade_records_per_liege():
    s = NPCOathChainSystem()
    bid = _swear(s)
    s.resolve_cascade(
        bond_id=bid,
        sworn_loyalty_to_current=50,
        sworn_grievance_score=0, seed=0,
        now_day=400,
    )
    out = s.cascade_for_liege(
        liege_id="off_volker",
    )
    assert len(out) == 1


def test_resolve_deterministic():
    s1 = NPCOathChainSystem()
    bid1 = _swear(s1)
    r1 = s1.resolve_cascade(
        bond_id=bid1,
        sworn_loyalty_to_current=50,
        sworn_grievance_score=5, seed=42,
        now_day=400,
    )
    s2 = NPCOathChainSystem()
    bid2 = _swear(s2)
    r2 = s2.resolve_cascade(
        bond_id=bid2,
        sworn_loyalty_to_current=50,
        sworn_grievance_score=5, seed=42,
        now_day=400,
    )
    assert r1 == r2


def test_bond_unknown():
    s = NPCOathChainSystem()
    assert s.bond(bond_id="ghost") is None


def test_break_unknown():
    s = NPCOathChainSystem()
    assert s.break_oath(
        bond_id="ghost", now_day=20,
    ) is False


def test_enum_counts():
    assert len(list(BondStrength)) == 3
    assert len(list(CascadeOutcome)) == 3
