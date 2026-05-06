"""Tests for typhoon portal."""
from __future__ import annotations

from server.typhoon_portal import (
    MAX_RAID_TRANSIT,
    PORTAL_OPEN_SECONDS,
    PortalState,
    ROYAL_FIGHT_SECONDS,
    TyphoonPortal,
)


def test_open_happy():
    p = TyphoonPortal()
    assert p.open(raid_id="r1", now_seconds=0) is True


def test_open_blank():
    p = TyphoonPortal()
    assert p.open(raid_id="", now_seconds=0) is False


def test_open_double_blocked():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    assert p.open(raid_id="r1", now_seconds=10) is False


def test_state_after_open():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    assert p.state_of(raid_id="r1") == PortalState.OPEN


def test_transit_happy():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    assert p.transit(
        raid_id="r1", player_id="p1", now_seconds=10,
    ) is True


def test_transit_dup_blocked():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    p.transit(raid_id="r1", player_id="p1", now_seconds=10)
    assert p.transit(
        raid_id="r1", player_id="p1", now_seconds=20,
    ) is False


def test_transit_after_window_auto_closes():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    ok = p.transit(
        raid_id="r1", player_id="p1",
        now_seconds=PORTAL_OPEN_SECONDS + 10,
    )
    assert ok is False
    assert p.state_of(raid_id="r1") == PortalState.CLOSED


def test_transit_cap_at_64():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    for i in range(MAX_RAID_TRANSIT):
        p.transit(
            raid_id="r1", player_id=f"p{i}", now_seconds=10,
        )
    assert p.transited_count(raid_id="r1") == MAX_RAID_TRANSIT
    overflow = p.transit(
        raid_id="r1", player_id="overflow", now_seconds=10,
    )
    assert overflow is False


def test_transit_unknown_raid():
    p = TyphoonPortal()
    assert p.transit(
        raid_id="ghost", player_id="p1", now_seconds=0,
    ) is False


def test_close_happy():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    assert p.close(raid_id="r1", now_seconds=10) is True
    assert p.state_of(raid_id="r1") == PortalState.CLOSED


def test_close_already_closed():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    p.close(raid_id="r1", now_seconds=10)
    assert p.close(raid_id="r1", now_seconds=20) is False


def test_start_royal_fight_only_after_close():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    assert p.start_royal_fight(
        raid_id="r1", now_seconds=10,
    ) is False  # still OPEN
    p.transit(raid_id="r1", player_id="p1", now_seconds=10)
    p.close(raid_id="r1", now_seconds=20)
    assert p.start_royal_fight(
        raid_id="r1", now_seconds=30,
    ) is True
    assert p.state_of(raid_id="r1") == PortalState.ROYAL_FIGHT


def test_start_royal_fight_no_transits():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    p.close(raid_id="r1", now_seconds=10)
    # nobody stepped through
    assert p.start_royal_fight(
        raid_id="r1", now_seconds=20,
    ) is False


def test_royal_fight_deadline_set():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    p.transit(raid_id="r1", player_id="p1", now_seconds=10)
    p.close(raid_id="r1", now_seconds=20)
    p.start_royal_fight(raid_id="r1", now_seconds=30)
    deadline = p.royal_fight_deadline(raid_id="r1")
    assert deadline == 30 + ROYAL_FIGHT_SECONDS


def test_royal_fight_in_progress():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    p.transit(raid_id="r1", player_id="p1", now_seconds=10)
    p.close(raid_id="r1", now_seconds=20)
    p.start_royal_fight(raid_id="r1", now_seconds=30)
    assert p.royal_fight_in_progress(
        raid_id="r1", now_seconds=100,
    ) is True


def test_royal_fight_expires_after_hour():
    p = TyphoonPortal()
    p.open(raid_id="r1", now_seconds=0)
    p.transit(raid_id="r1", player_id="p1", now_seconds=10)
    p.close(raid_id="r1", now_seconds=20)
    p.start_royal_fight(raid_id="r1", now_seconds=30)
    # past the deadline
    assert p.royal_fight_in_progress(
        raid_id="r1",
        now_seconds=30 + ROYAL_FIGHT_SECONDS + 100,
    ) is False
    assert p.state_of(raid_id="r1") == PortalState.EXPIRED


def test_unknown_helpers_return_safely():
    p = TyphoonPortal()
    assert p.state_of(raid_id="ghost") is None
    assert p.transited_count(raid_id="ghost") == 0
    assert p.royal_fight_deadline(raid_id="ghost") is None
    assert p.royal_fight_in_progress(
        raid_id="ghost", now_seconds=0,
    ) is False
