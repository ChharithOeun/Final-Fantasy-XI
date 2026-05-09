"""Tests for entity_hobby_buddies."""
from __future__ import annotations

from server.entity_hobby_buddies import (
    EntityHobbyBuddiesSystem, BuddyTier,
)
from server.entity_hobbies import HobbyKind


def _decl(s: EntityHobbyBuddiesSystem) -> str:
    return s.declare_pair(
        entity_a="volker", entity_b="naji",
        hobby=HobbyKind.FISHING,
    )


def test_declare_happy():
    s = EntityHobbyBuddiesSystem()
    pid = _decl(s)
    assert pid is not None


def test_declare_self_pair_blocked():
    s = EntityHobbyBuddiesSystem()
    assert s.declare_pair(
        entity_a="x", entity_b="x",
        hobby=HobbyKind.FISHING,
    ) is None


def test_declare_dup_blocked():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    # Same pair, either order
    assert s.declare_pair(
        entity_a="naji", entity_b="volker",
        hobby=HobbyKind.FISHING,
    ) is None


def test_different_hobby_same_pair_ok():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    pid2 = s.declare_pair(
        entity_a="volker", entity_b="naji",
        hobby=HobbyKind.DRINKING,
    )
    assert pid2 is not None


def test_starting_tier_acquaintance():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    assert s.tier(
        entity_a="volker", entity_b="naji",
        hobby=HobbyKind.FISHING,
    ) == BuddyTier.ACQUAINTANCE


def test_record_session_increments():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    assert s.record_joint_session(
        entity_a="naji", entity_b="volker",
        hobby=HobbyKind.FISHING,
    ) is True
    assert s.joint_sessions(
        entity_a="naji", entity_b="volker",
        hobby=HobbyKind.FISHING,
    ) == 1


def test_record_self_blocked():
    s = EntityHobbyBuddiesSystem()
    assert s.record_joint_session(
        entity_a="x", entity_b="x",
        hobby=HobbyKind.FISHING,
    ) is False


def test_record_undeclared_blocked():
    s = EntityHobbyBuddiesSystem()
    assert s.record_joint_session(
        entity_a="a", entity_b="b",
        hobby=HobbyKind.FISHING,
    ) is False


def test_friend_at_5():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    for _ in range(5):
        s.record_joint_session(
            entity_a="naji", entity_b="volker",
            hobby=HobbyKind.FISHING,
        )
    assert s.tier(
        entity_a="volker", entity_b="naji",
        hobby=HobbyKind.FISHING,
    ) == BuddyTier.FRIEND


def test_close_friend_at_15():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    for _ in range(15):
        s.record_joint_session(
            entity_a="naji", entity_b="volker",
            hobby=HobbyKind.FISHING,
        )
    assert s.tier(
        entity_a="volker", entity_b="naji",
        hobby=HobbyKind.FISHING,
    ) == BuddyTier.CLOSE_FRIEND


def test_best_friend_at_40():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    for _ in range(40):
        s.record_joint_session(
            entity_a="naji", entity_b="volker",
            hobby=HobbyKind.FISHING,
        )
    assert s.is_best_friends(
        entity_a="volker", entity_b="naji",
        hobby=HobbyKind.FISHING,
    ) is True


def test_below_best_not_best_friends():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    for _ in range(20):
        s.record_joint_session(
            entity_a="naji", entity_b="volker",
            hobby=HobbyKind.FISHING,
        )
    assert s.is_best_friends(
        entity_a="volker", entity_b="naji",
        hobby=HobbyKind.FISHING,
    ) is False


def test_buddies_of_lookup():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    s.declare_pair(
        entity_a="volker", entity_b="bob",
        hobby=HobbyKind.DRINKING,
    )
    pairs = s.buddies_of(entity_id="volker")
    assert len(pairs) == 2


def test_buddies_of_unknown():
    s = EntityHobbyBuddiesSystem()
    assert s.buddies_of(entity_id="ghost") == []


def test_tier_undeclared_pair_none():
    s = EntityHobbyBuddiesSystem()
    assert s.tier(
        entity_a="a", entity_b="b",
        hobby=HobbyKind.FISHING,
    ) is None


def test_unknown_pair_lookup():
    s = EntityHobbyBuddiesSystem()
    assert s.pair(pair_id="ghost") is None


def test_canonical_ordering():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    p = s.pair(pair_id="pair_1")
    # Canonical: alphabetical
    assert p.entity_a == "naji"
    assert p.entity_b == "volker"


def test_joint_sessions_undeclared_zero():
    s = EntityHobbyBuddiesSystem()
    assert s.joint_sessions(
        entity_a="a", entity_b="b",
        hobby=HobbyKind.FISHING,
    ) == 0


def test_per_hobby_isolation():
    s = EntityHobbyBuddiesSystem()
    _decl(s)
    s.declare_pair(
        entity_a="volker", entity_b="naji",
        hobby=HobbyKind.DRINKING,
    )
    for _ in range(5):
        s.record_joint_session(
            entity_a="naji", entity_b="volker",
            hobby=HobbyKind.FISHING,
        )
    # Drinking pair untouched
    assert s.joint_sessions(
        entity_a="naji", entity_b="volker",
        hobby=HobbyKind.DRINKING,
    ) == 0


def test_enum_count():
    assert len(list(BuddyTier)) == 4
