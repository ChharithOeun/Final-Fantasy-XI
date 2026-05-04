"""Tests for cross-faction reputation."""
from __future__ import annotations

from server.cross_faction_reputation import (
    CrossFactionReputation,
    MAX_SCORE,
    MIN_SCORE,
    SideKind,
    StandingTier,
)


def test_declare_side():
    r = CrossFactionReputation()
    assert r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )


def test_declare_double_rejected():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    assert not r.declare_side(
        player_id="alice",
        own_side=SideKind.BEASTMAN,
    )


def test_modify_without_side_rejected():
    r = CrossFactionReputation()
    res = r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=50,
    )
    assert not res.accepted


def test_modify_empty_target_rejected():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    res = r.modify(
        player_id="alice",
        target_faction="",
        delta=50,
    )
    assert not res.accepted


def test_modify_zero_delta_returns_unchanged():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=100,
    )
    res = r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=0,
    )
    assert not res.accepted
    assert res.points == 100


def test_modify_positive():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    res = r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=200,
    )
    assert res.accepted
    assert res.points == 200


def test_modify_negative():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    res = r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=-500,
    )
    assert res.accepted
    assert res.points == -500


def test_modify_clamps_high():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=99999,
    )
    assert r.points(
        player_id="alice",
        target_faction="yagudo",
    ) == MAX_SCORE


def test_modify_clamps_low():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=-99999,
    )
    assert r.points(
        player_id="alice",
        target_faction="yagudo",
    ) == MIN_SCORE


def test_standing_hostile():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.modify(
        player_id="alice",
        target_faction="orc",
        delta=-500,
    )
    assert r.standing(
        player_id="alice",
        target_faction="orc",
    ) == StandingTier.HOSTILE


def test_standing_neutral_at_zero():
    r = CrossFactionReputation()
    assert r.standing(
        player_id="alice",
        target_faction="orc",
    ) == StandingTier.NEUTRAL


def test_standing_acquainted():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=100,
    )
    assert r.standing(
        player_id="alice",
        target_faction="yagudo",
    ) == StandingTier.ACQUAINTED


def test_standing_trusted():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=500,
    )
    assert r.standing(
        player_id="alice",
        target_faction="yagudo",
    ) == StandingTier.TRUSTED


def test_standing_exalted():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=999,
    )
    assert r.standing(
        player_id="alice",
        target_faction="yagudo",
    ) == StandingTier.EXALTED


def test_beastman_side_can_befriend_hume_nation():
    """Symmetry: beastman declared, can build standing
    with bastok via good deeds."""
    r = CrossFactionReputation()
    r.declare_side(
        player_id="brokenfang",
        own_side=SideKind.BEASTMAN,
    )
    r.modify(
        player_id="brokenfang",
        target_faction="bastok",
        delta=300,
    )
    assert r.standing(
        player_id="brokenfang",
        target_faction="bastok",
    ) == StandingTier.ACQUAINTED


def test_reset_clears():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=200,
    )
    assert r.reset(
        player_id="alice",
        target_faction="yagudo",
    )
    assert r.points(
        player_id="alice",
        target_faction="yagudo",
    ) == 0


def test_reset_unknown_returns_false():
    r = CrossFactionReputation()
    assert not r.reset(
        player_id="alice",
        target_faction="ghost",
    )


def test_per_player_isolation():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=200,
    )
    assert r.points(
        player_id="bob",
        target_faction="yagudo",
    ) == 0


def test_total_counts():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    r.declare_side(
        player_id="bob",
        own_side=SideKind.BEASTMAN,
    )
    r.modify(
        player_id="alice",
        target_faction="yagudo",
        delta=100,
    )
    assert r.total_players() == 2
    assert r.total_pairs() == 1


def test_own_side_lookup():
    r = CrossFactionReputation()
    r.declare_side(
        player_id="alice",
        own_side=SideKind.HUME_NATIONS,
    )
    assert r.own_side_for(
        "alice",
    ) == SideKind.HUME_NATIONS
    assert r.own_side_for("ghost") is None
