"""Tests for the minimap ping system."""
from __future__ import annotations

from server.minimap_ping import (
    MAX_LIVE_PINGS_PER_PLAYER,
    MinimapPingSystem,
    PingIntent,
    PingScope,
)


def test_place_ping_succeeds():
    s = MinimapPingSystem()
    res = s.place_ping(
        placer_id="alice", zone_id="ronfaure",
        x=10, y=20,
        intent=PingIntent.ATTACK_HERE,
    )
    assert res.accepted
    assert res.ping.color == "red"


def test_cooldown_blocks_rapid_repeat():
    s = MinimapPingSystem(cooldown_seconds=2.0)
    s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0, now_seconds=0.0,
    )
    res = s.place_ping(
        placer_id="alice", zone_id="z",
        x=1, y=1, now_seconds=1.0,
    )
    assert not res.accepted
    assert "cooldown" in res.reason


def test_cooldown_clears_after_window():
    s = MinimapPingSystem(cooldown_seconds=1.0)
    s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0, now_seconds=0.0,
    )
    res = s.place_ping(
        placer_id="alice", zone_id="z",
        x=1, y=1, now_seconds=2.0,
    )
    assert res.accepted


def test_max_live_pings_per_player():
    s = MinimapPingSystem(
        cooldown_seconds=0.0,
        lifetime_seconds=100.0,
    )
    for i in range(MAX_LIVE_PINGS_PER_PLAYER):
        s.place_ping(
            placer_id="alice", zone_id="z",
            x=i, y=0, now_seconds=float(i),
        )
    res = s.place_ping(
        placer_id="alice", zone_id="z",
        x=99, y=0, now_seconds=10.0,
    )
    assert not res.accepted
    assert "too many" in res.reason


def test_party_visible_to_party_members():
    s = MinimapPingSystem()
    res = s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0,
        scope=PingScope.PARTY,
        party_member_ids=("bob", "carol"),
    )
    pings_for_bob = s.visible_to(
        viewer_id="bob", viewer_zone_id="z",
    )
    assert len(pings_for_bob) == 1
    pings_for_outsider = s.visible_to(
        viewer_id="dan", viewer_zone_id="z",
    )
    assert pings_for_outsider == ()


def test_self_scope_only_visible_to_placer():
    s = MinimapPingSystem()
    s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0,
        scope=PingScope.SELF,
        party_member_ids=("bob",),
    )
    assert len(
        s.visible_to(
            viewer_id="alice", viewer_zone_id="z",
        )
    ) == 1
    assert s.visible_to(
        viewer_id="bob", viewer_zone_id="z",
    ) == ()


def test_other_zone_invisible():
    s = MinimapPingSystem()
    s.place_ping(
        placer_id="alice", zone_id="z1",
        x=0, y=0,
        party_member_ids=("bob",),
    )
    assert s.visible_to(
        viewer_id="bob", viewer_zone_id="z2",
    ) == ()


def test_intent_color_mapping():
    s = MinimapPingSystem()
    for intent, expected in (
        (PingIntent.RETREAT, "yellow"),
        (PingIntent.DANGER, "magenta"),
        (PingIntent.LOOT, "gold"),
        (PingIntent.WAYPOINT, "cyan"),
    ):
        s2 = MinimapPingSystem()
        res = s2.place_ping(
            placer_id="alice", zone_id="z",
            x=0, y=0, intent=intent,
        )
        assert res.ping.color == expected


def test_tick_expires_old_pings():
    s = MinimapPingSystem(lifetime_seconds=1.0)
    s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0, now_seconds=0.0,
    )
    expired = s.tick(now_seconds=10.0)
    assert len(expired) == 1
    assert s.total_active() == 0


def test_tick_keeps_fresh_pings():
    s = MinimapPingSystem(lifetime_seconds=10.0)
    s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0, now_seconds=0.0,
    )
    expired = s.tick(now_seconds=1.0)
    assert expired == ()


def test_visible_sorted_recent_first():
    s = MinimapPingSystem(
        cooldown_seconds=0.0,
        lifetime_seconds=100.0,
    )
    s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0, now_seconds=0.0,
        party_member_ids=("bob",),
    )
    s.place_ping(
        placer_id="alice", zone_id="z",
        x=1, y=1, now_seconds=1.0,
        party_member_ids=("bob",),
    )
    pings = s.visible_to(
        viewer_id="bob", viewer_zone_id="z",
    )
    assert pings[0].placed_at_seconds == 1.0


def test_placer_sees_own_ping():
    s = MinimapPingSystem()
    s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0,
        scope=PingScope.PARTY,
        party_member_ids=(),
    )
    assert len(
        s.visible_to(
            viewer_id="alice", viewer_zone_id="z",
        )
    ) == 1


def test_get_ping_by_id():
    s = MinimapPingSystem()
    res = s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0,
    )
    p = s.get(res.ping.ping_id)
    assert p is not None
    assert p.placer_id == "alice"


def test_get_unknown_returns_none():
    s = MinimapPingSystem()
    assert s.get("ghost") is None


def test_total_active_count():
    s = MinimapPingSystem(cooldown_seconds=0.0)
    s.place_ping(
        placer_id="alice", zone_id="z",
        x=0, y=0,
    )
    s.place_ping(
        placer_id="bob", zone_id="z",
        x=0, y=0,
    )
    assert s.total_active() == 2
