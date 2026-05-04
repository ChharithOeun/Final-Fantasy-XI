"""Tests for the shadowlands expansion."""
from __future__ import annotations

from server.shadowlands_expansion import (
    ExpansionStatus,
    ShadowlandsExpansion,
    ZoneKind,
)


def test_register_zone():
    e = ShadowlandsExpansion()
    z = e.register_zone(
        zone_id="yagudo_highlands",
        kind=ZoneKind.YAGUDO,
        label="Yagudo Highlands",
        level_gate=20,
        is_starter=True,
    )
    assert z is not None


def test_register_unknown_prereq_rejected():
    e = ShadowlandsExpansion()
    res = e.register_zone(
        zone_id="z", kind=ZoneKind.YAGUDO,
        label="x", level_gate=1,
        prereq_zone_ids=("ghost",),
    )
    assert res is None


def test_register_invalid_level_rejected():
    e = ShadowlandsExpansion()
    res = e.register_zone(
        zone_id="z", kind=ZoneKind.YAGUDO,
        label="x", level_gate=0,
    )
    assert res is None


def test_double_register_rejected():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="z", kind=ZoneKind.YAGUDO,
        label="x", level_gate=1,
    )
    second = e.register_zone(
        zone_id="z", kind=ZoneKind.QUADAV,
        label="y", level_gate=1,
    )
    assert second is None


def test_grant_and_check_ownership():
    e = ShadowlandsExpansion()
    assert e.grant_ownership(player_id="alice")
    assert e.has_ownership(player_id="alice")


def test_double_grant_rejected():
    e = ShadowlandsExpansion()
    e.grant_ownership(player_id="alice")
    assert not e.grant_ownership(player_id="alice")


def test_revoke_ownership():
    e = ShadowlandsExpansion()
    e.grant_ownership(player_id="alice")
    assert e.revoke_ownership(player_id="alice")
    assert not e.has_ownership(player_id="alice")


def test_revoke_unknown():
    e = ShadowlandsExpansion()
    assert not e.revoke_ownership(player_id="alice")


def test_can_enter_pre_release_blocks():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="z", kind=ZoneKind.YAGUDO,
        label="x", level_gate=1,
    )
    e.grant_ownership(player_id="alice")
    res = e.can_enter(
        player_id="alice", zone_id="z",
        player_level=99,
    )
    assert not res.accepted
    assert "not yet released" in res.reason


def test_can_enter_sunset_blocks():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="z", kind=ZoneKind.YAGUDO,
        label="x", level_gate=1,
    )
    e.grant_ownership(player_id="alice")
    e.mark_status(status=ExpansionStatus.SUNSET)
    res = e.can_enter(
        player_id="alice", zone_id="z",
        player_level=99,
    )
    assert not res.accepted


def test_can_enter_no_ownership():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="z", kind=ZoneKind.YAGUDO,
        label="x", level_gate=1,
    )
    e.mark_status(status=ExpansionStatus.OPEN)
    res = e.can_enter(
        player_id="alice", zone_id="z",
        player_level=99,
    )
    assert not res.accepted
    assert "not owned" in res.reason


def test_can_enter_below_level_gate():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="z", kind=ZoneKind.YAGUDO,
        label="x", level_gate=20,
    )
    e.mark_status(status=ExpansionStatus.OPEN)
    e.grant_ownership(player_id="alice")
    res = e.can_enter(
        player_id="alice", zone_id="z",
        player_level=10,
    )
    assert not res.accepted


def test_can_enter_missing_prereq():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="a", kind=ZoneKind.YAGUDO,
        label="A", level_gate=1,
    )
    e.register_zone(
        zone_id="b", kind=ZoneKind.YAGUDO,
        label="B", level_gate=1,
        prereq_zone_ids=("a",),
    )
    e.mark_status(status=ExpansionStatus.OPEN)
    e.grant_ownership(player_id="alice")
    res = e.can_enter(
        player_id="alice", zone_id="b",
        player_level=99,
    )
    assert not res.accepted
    assert "missing prereq" in res.reason


def test_can_enter_with_completed_prereqs():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="a", kind=ZoneKind.YAGUDO,
        label="A", level_gate=1,
    )
    e.register_zone(
        zone_id="b", kind=ZoneKind.YAGUDO,
        label="B", level_gate=1,
        prereq_zone_ids=("a",),
    )
    e.mark_status(status=ExpansionStatus.OPEN)
    e.grant_ownership(player_id="alice")
    res = e.can_enter(
        player_id="alice", zone_id="b",
        player_level=99,
        completed_zone_ids=("a",),
    )
    assert res.accepted


def test_can_enter_unknown_zone():
    e = ShadowlandsExpansion()
    e.mark_status(status=ExpansionStatus.OPEN)
    e.grant_ownership(player_id="alice")
    res = e.can_enter(
        player_id="alice", zone_id="ghost",
        player_level=99,
    )
    assert not res.accepted


def test_starter_zones_filter():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="y_start", kind=ZoneKind.YAGUDO,
        label="Y Start", level_gate=1,
        is_starter=True,
    )
    e.register_zone(
        zone_id="y_mid", kind=ZoneKind.YAGUDO,
        label="Y Mid", level_gate=20,
    )
    e.register_zone(
        zone_id="q_start", kind=ZoneKind.QUADAV,
        label="Q Start", level_gate=1,
        is_starter=True,
    )
    yagudo_starters = e.starter_zones(ZoneKind.YAGUDO)
    assert len(yagudo_starters) == 1
    assert yagudo_starters[0].zone_id == "y_start"


def test_total_zones_and_owners():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="a", kind=ZoneKind.YAGUDO,
        label="A", level_gate=1,
    )
    e.register_zone(
        zone_id="b", kind=ZoneKind.QUADAV,
        label="B", level_gate=1,
    )
    e.grant_ownership(player_id="alice")
    e.grant_ownership(player_id="bob")
    assert e.total_zones() == 2
    assert e.total_owners() == 2


def test_mark_status():
    e = ShadowlandsExpansion()
    e.mark_status(status=ExpansionStatus.OPEN)
    assert e.status == ExpansionStatus.OPEN


def test_event_limited_status_blocks_unowned():
    e = ShadowlandsExpansion()
    e.register_zone(
        zone_id="z", kind=ZoneKind.YAGUDO,
        label="x", level_gate=1,
    )
    e.mark_status(status=ExpansionStatus.EVENT_LIMITED)
    res = e.can_enter(
        player_id="alice", zone_id="z",
        player_level=99,
    )
    # Still requires ownership in event-limited mode
    assert not res.accepted
