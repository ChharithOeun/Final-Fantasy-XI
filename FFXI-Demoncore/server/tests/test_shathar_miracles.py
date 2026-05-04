"""Tests for Shathar miracles."""
from __future__ import annotations

from server.shathar_miracles import (
    MAX_FAITH_POINTS,
    MiracleKind,
    MiracleTier,
    ShatharMiracles,
)


def _seed(s: ShatharMiracles):
    s.register_miracle(
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        tier=MiracleTier.LESSER,
        faith_cost=50,
        cooldown_seconds=300,
    )
    s.register_miracle(
        kind=MiracleKind.OUTCASTS_HYMN,
        tier=MiracleTier.GREATER,
        faith_cost=200,
        cooldown_seconds=900,
    )
    s.register_miracle(
        kind=MiracleKind.THE_NAMING,
        tier=MiracleTier.OUTCAST_VOICE,
        faith_cost=800,
        cooldown_seconds=86400,
    )


def test_register_miracle():
    s = ShatharMiracles()
    _seed(s)
    assert s.total_miracles() == 3


def test_register_double_kind_rejected():
    s = ShatharMiracles()
    s.register_miracle(
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        tier=MiracleTier.LESSER,
        faith_cost=50, cooldown_seconds=300,
    )
    res = s.register_miracle(
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        tier=MiracleTier.LESSER,
        faith_cost=10, cooldown_seconds=10,
    )
    assert res is None


def test_register_negative_cost_rejected():
    s = ShatharMiracles()
    res = s.register_miracle(
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        tier=MiracleTier.LESSER,
        faith_cost=-1, cooldown_seconds=10,
    )
    assert res is None


def test_register_negative_cooldown_rejected():
    s = ShatharMiracles()
    res = s.register_miracle(
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        tier=MiracleTier.LESSER,
        faith_cost=10, cooldown_seconds=-5,
    )
    assert res is None


def test_grant_faith():
    s = ShatharMiracles()
    res = s.grant_faith(
        player_id="alice", points=100,
    )
    assert res == 100


def test_grant_negative_rejected():
    s = ShatharMiracles()
    assert s.grant_faith(
        player_id="alice", points=0,
    ) is None
    assert s.grant_faith(
        player_id="alice", points=-10,
    ) is None


def test_grant_faith_clamped_to_max():
    s = ShatharMiracles()
    s.grant_faith(
        player_id="alice", points=99999,
    )
    assert s.faith_points(
        player_id="alice",
    ) == MAX_FAITH_POINTS


def test_invoke_success():
    s = ShatharMiracles()
    _seed(s)
    s.grant_faith(player_id="alice", points=100)
    res = s.invoke(
        player_id="alice",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        now_seconds=10.0,
    )
    assert res.accepted
    assert res.faith_remaining == 50


def test_invoke_unregistered_rejected():
    s = ShatharMiracles()
    s.grant_faith(player_id="alice", points=999)
    res = s.invoke(
        player_id="alice",
        kind=MiracleKind.OUTCASTS_HYMN,
        now_seconds=10.0,
    )
    assert not res.accepted
    assert "not registered" in res.reason


def test_invoke_insufficient_faith():
    s = ShatharMiracles()
    _seed(s)
    s.grant_faith(player_id="alice", points=10)
    res = s.invoke(
        player_id="alice",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        now_seconds=10.0,
    )
    assert not res.accepted
    assert "insufficient" in res.reason


def test_invoke_on_cooldown():
    s = ShatharMiracles()
    _seed(s)
    s.grant_faith(player_id="alice", points=200)
    s.invoke(
        player_id="alice",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        now_seconds=10.0,
    )
    s.grant_faith(player_id="alice", points=200)
    res = s.invoke(
        player_id="alice",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        now_seconds=20.0,
    )
    assert not res.accepted
    assert "cooldown" in res.reason


def test_invoke_after_cooldown_expires():
    s = ShatharMiracles()
    _seed(s)
    s.grant_faith(player_id="alice", points=200)
    s.invoke(
        player_id="alice",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        now_seconds=10.0,
    )
    s.grant_faith(player_id="alice", points=200)
    res = s.invoke(
        player_id="alice",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        now_seconds=10000.0,
    )
    assert res.accepted


def test_next_available_at():
    s = ShatharMiracles()
    _seed(s)
    s.grant_faith(player_id="alice", points=100)
    s.invoke(
        player_id="alice",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        now_seconds=10.0,
    )
    nxt = s.next_available_at(
        player_id="alice",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
    )
    assert nxt == 310.0


def test_next_available_no_player():
    s = ShatharMiracles()
    nxt = s.next_available_at(
        player_id="ghost",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
    )
    assert nxt is None


def test_invocation_count():
    s = ShatharMiracles()
    _seed(s)
    s.grant_faith(player_id="alice", points=900)
    for _ in range(3):
        s.invoke(
            player_id="alice",
            kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
            now_seconds=10000.0 * 1,
        )
        # Same now_seconds -> only first succeeds
    assert s.total_invocations(
        player_id="alice",
    ) == 1


def test_high_tier_miracle_high_cost():
    s = ShatharMiracles()
    _seed(s)
    s.grant_faith(
        player_id="alice", points=MAX_FAITH_POINTS,
    )
    res = s.invoke(
        player_id="alice",
        kind=MiracleKind.THE_NAMING,
        now_seconds=0.0,
    )
    assert res.accepted
    assert res.faith_remaining == 200


def test_per_player_isolation():
    s = ShatharMiracles()
    _seed(s)
    s.grant_faith(player_id="alice", points=100)
    s.grant_faith(player_id="bob", points=10)
    res_b = s.invoke(
        player_id="bob",
        kind=MiracleKind.SHIELD_OF_THE_FORGOTTEN,
        now_seconds=0.0,
    )
    assert not res_b.accepted


def test_total_miracles():
    s = ShatharMiracles()
    _seed(s)
    assert s.total_miracles() == 3


def test_faith_points_default_zero():
    s = ShatharMiracles()
    assert s.faith_points(player_id="alice") == 0
