"""Tests for friendship_system."""
from __future__ import annotations

from server.friendship_system import (
    EventKind, FriendshipSystem, FriendshipTier,
)


def test_record_event():
    f = FriendshipSystem()
    assert f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.PARTY_HOUR,
    ) is True


def test_record_event_blank_blocked():
    f = FriendshipSystem()
    assert f.record_event(
        player_a="", player_b="cara",
        kind=EventKind.TELL_EXCHANGED,
    ) is False


def test_record_event_self_blocked():
    f = FriendshipSystem()
    assert f.record_event(
        player_a="bob", player_b="bob",
        kind=EventKind.TELL_EXCHANGED,
    ) is False


def test_record_event_zero_count_blocked():
    f = FriendshipSystem()
    assert f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.PARTY_HOUR, count=0,
    ) is False


def test_bond_starts_at_acquaintance():
    f = FriendshipSystem()
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.PARTY_HOUR,
    )
    bond = f.bond(player_a="bob", player_b="cara")
    assert bond is not None
    assert bond.points == 2
    assert bond.tier == FriendshipTier.ACQUAINTANCE


def test_bond_symmetric():
    f = FriendshipSystem()
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.GIFT_EXCHANGED,
    )
    a_view = f.bond(player_a="bob", player_b="cara")
    b_view = f.bond(player_a="cara", player_b="bob")
    assert a_view.points == b_view.points


def test_bond_unknown_returns_none():
    f = FriendshipSystem()
    assert f.bond(
        player_a="bob", player_b="cara",
    ) is None


def test_companion_tier():
    f = FriendshipSystem()
    # 30 party hours = 60 points -> COMPANION (51..200)
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.PARTY_HOUR, count=30,
    )
    bond = f.bond(player_a="bob", player_b="cara")
    assert bond.tier == FriendshipTier.COMPANION


def test_confidant_tier():
    f = FriendshipSystem()
    # 25 dungeons = 300 points -> CONFIDANT
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.DUNGEON_CLEARED, count=25,
    )
    bond = f.bond(player_a="bob", player_b="cara")
    assert bond.tier == FriendshipTier.CONFIDANT


def test_blood_bond_tier():
    f = FriendshipSystem()
    # 50 dungeons = 600 points -> BLOOD_BOND (501+)
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.DUNGEON_CLEARED, count=50,
    )
    bond = f.bond(player_a="bob", player_b="cara")
    assert bond.tier == FriendshipTier.BLOOD_BOND


def test_decay_first_call_no_op():
    f = FriendshipSystem()
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.GIFT_EXCHANGED, count=10,
    )
    assert f.decay(now_day=100) == 0


def test_decay_subsequent_loses_points():
    f = FriendshipSystem()
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.GIFT_EXCHANGED, count=10,
    )
    f.decay(now_day=100)  # initialize
    f.decay(now_day=110)  # 10 days
    bond = f.bond(player_a="bob", player_b="cara")
    # 50 - 10 = 40 points
    assert bond.points == 40


def test_decay_clamps_at_zero():
    f = FriendshipSystem()
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.TELL_EXCHANGED, count=3,
    )
    f.decay(now_day=100)
    f.decay(now_day=200)
    bond = f.bond(player_a="bob", player_b="cara")
    # Bond decayed all the way to 0 -> deleted
    assert bond is None


def test_friends_at_tier():
    f = FriendshipSystem()
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.DUNGEON_CLEARED, count=50,
    )  # BLOOD_BOND
    f.record_event(
        player_a="bob", player_b="dave",
        kind=EventKind.PARTY_HOUR, count=30,
    )  # COMPANION
    blood = f.friends_at_tier(
        player_id="bob", tier=FriendshipTier.BLOOD_BOND,
    )
    assert blood == ["cara"]
    comp = f.friends_at_tier(
        player_id="bob", tier=FriendshipTier.COMPANION,
    )
    assert comp == ["dave"]


def test_top_friends_sorted():
    f = FriendshipSystem()
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.PARTY_HOUR, count=10,
    )
    f.record_event(
        player_a="bob", player_b="dave",
        kind=EventKind.DUNGEON_CLEARED, count=5,
    )
    f.record_event(
        player_a="bob", player_b="evan",
        kind=EventKind.TELL_EXCHANGED, count=3,
    )
    top = f.top_friends(player_id="bob", n=2)
    # dave 60 pts, cara 20 pts, evan 3 pts
    assert top[0][0] == "dave"
    assert top[1][0] == "cara"


def test_top_friends_no_partners():
    f = FriendshipSystem()
    assert f.top_friends(player_id="bob") == []


def test_event_weights_differ():
    f = FriendshipSystem()
    f.record_event(
        player_a="bob", player_b="cara",
        kind=EventKind.TELL_EXCHANGED,
    )
    f.record_event(
        player_a="bob", player_b="dave",
        kind=EventKind.DEATH_SAVED,
    )
    cara_pts = f.bond(
        player_a="bob", player_b="cara",
    ).points
    dave_pts = f.bond(
        player_a="bob", player_b="dave",
    ).points
    assert dave_pts > cara_pts


def test_self_bond_returns_none():
    f = FriendshipSystem()
    assert f.bond(
        player_a="bob", player_b="bob",
    ) is None


def test_six_event_kinds():
    assert len(list(EventKind)) == 6


def test_four_tiers():
    assert len(list(FriendshipTier)) == 4
