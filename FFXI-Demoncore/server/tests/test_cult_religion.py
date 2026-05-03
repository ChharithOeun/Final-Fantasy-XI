"""Tests for cult & religion."""
from __future__ import annotations

from server.cult_religion import (
    APOSTATE_CEILING_CUT,
    APOSTATE_THRESHOLD,
    CultReligionRegistry,
    DEVOTED_TIER_FAITH,
    DevotionTier,
    FAITHFUL_TIER_FAITH,
    GodKind,
    HERETIC_MALUS,
    MAX_FAITH,
    PrayerKind,
    SAINT_TIER_FAITH,
    ZEALOT_TIER_FAITH,
)


def test_pledge_creates_devotion():
    cult = CultReligionRegistry()
    assert cult.pledge(player_id="alice", god=GodKind.ALTANA)
    assert cult.devotion("alice").god == GodKind.ALTANA


def test_pledge_starts_at_no_tier():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    assert cult.tier_for("alice") == DevotionTier.NONE


def test_pledge_same_god_is_noop():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    cult.offer(player_id="alice", value=10000)
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    assert cult.devotion("alice").faith == 100


def test_pledge_switch_applies_heretic_malus():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    cult.offer(player_id="alice", value=20000)
    # 200 faith
    cult.pledge(player_id="alice", god=GodKind.PROMATHIA)
    # Faith reset to 0 (max of 0, -malus)
    assert cult.devotion("alice").faith == 0


def test_offer_increments_faith():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    new_faith = cult.offer(player_id="alice", value=10000)
    # 10000 / 100 = 100 faith
    assert new_faith == 100


def test_offer_caps_at_ceiling():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    cult.offer(player_id="alice", value=10_000_000)
    assert cult.devotion("alice").faith == MAX_FAITH


def test_offer_negative_rejected():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    assert cult.offer(player_id="alice", value=0) is None


def test_offer_no_pledge_returns_none():
    cult = CultReligionRegistry()
    assert cult.offer(
        player_id="alice", value=1000,
    ) is None


def test_sin_lowers_faith():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    cult.offer(player_id="alice", value=20000)
    cult.sin(player_id="alice", magnitude=50)
    assert cult.devotion("alice").faith == 150


def test_sin_floor_at_zero():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    cult.offer(player_id="alice", value=10000)
    cult.sin(player_id="alice", magnitude=10000)
    assert cult.devotion("alice").faith == 0


def test_pray_below_tier_rejected():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    out = cult.pray(
        player_id="alice", prayer_kind=PrayerKind.BLESSING,
    )
    assert not out.accepted
    assert "tier" in out.reason


def test_pray_succeeds_at_devoted():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    cult.offer(
        player_id="alice", value=DEVOTED_TIER_FAITH * 100,
    )
    out = cult.pray(
        player_id="alice", prayer_kind=PrayerKind.BLESSING,
    )
    assert out.accepted
    assert out.faith_after == DEVOTED_TIER_FAITH - 10


def test_pray_miracle_requires_saint():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    # Faithful tier — miracle not allowed
    cult.offer(
        player_id="alice", value=FAITHFUL_TIER_FAITH * 100,
    )
    out = cult.pray(
        player_id="alice",
        prayer_kind=PrayerKind.MIRACLE_RESURRECTION,
    )
    assert not out.accepted


def test_pray_miracle_at_saint():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    cult.offer(
        player_id="alice",
        value=SAINT_TIER_FAITH * 100,
    )
    out = cult.pray(
        player_id="alice",
        prayer_kind=PrayerKind.MIRACLE_RESURRECTION,
    )
    assert out.accepted


def test_pray_no_pledge_rejected():
    cult = CultReligionRegistry()
    out = cult.pray(
        player_id="x", prayer_kind=PrayerKind.BLESSING,
    )
    assert not out.accepted


def test_apostate_resets_faith():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    cult.offer(player_id="alice", value=20000)
    cult.declare_apostate(player_id="alice")
    assert cult.devotion("alice").faith == 0
    assert cult.devotion("alice").apostate_count == 1


def test_apostate_threshold_cuts_ceiling():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    for _ in range(APOSTATE_THRESHOLD):
        cult.declare_apostate(player_id="alice")
    assert (
        cult.devotion("alice").faith_ceiling
        == MAX_FAITH - APOSTATE_CEILING_CUT
    )


def test_apostate_unknown_player():
    cult = CultReligionRegistry()
    assert not cult.declare_apostate(player_id="ghost")


def test_total_devotions():
    cult = CultReligionRegistry()
    cult.pledge(player_id="a", god=GodKind.ALTANA)
    cult.pledge(player_id="b", god=GodKind.PROMATHIA)
    assert cult.total_devotions() == 2


def test_tier_progression_through_offerings():
    cult = CultReligionRegistry()
    cult.pledge(player_id="alice", god=GodKind.ALTANA)
    cult.offer(
        player_id="alice", value=ZEALOT_TIER_FAITH * 100,
    )
    assert cult.tier_for("alice") == DevotionTier.ZEALOT
