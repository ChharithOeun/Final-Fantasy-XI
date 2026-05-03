"""Tests for the wayfinder compass."""
from __future__ import annotations

import math

from server.wayfinder_compass import (
    PinCategory,
    Visibility,
    WayfinderCompass,
)


def test_pin_creates_waypoint():
    cmp = WayfinderCompass()
    wp = cmp.pin(
        owner_player_id="alice", label="quest goal",
        zone_id="ronfaure", x=10, y=20,
        category=PinCategory.QUEST_OBJECTIVE,
    )
    assert wp.pin_id.startswith("pin_")
    assert wp.category == PinCategory.QUEST_OBJECTIVE


def test_unpin_owner():
    cmp = WayfinderCompass()
    wp = cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=0, y=0,
    )
    assert cmp.unpin(
        owner_player_id="alice", pin_id=wp.pin_id,
    )
    assert cmp.total_pins() == 0


def test_unpin_wrong_owner_rejected():
    cmp = WayfinderCompass()
    wp = cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=0, y=0,
    )
    assert not cmp.unpin(
        owner_player_id="bob", pin_id=wp.pin_id,
    )


def test_unpin_unknown():
    cmp = WayfinderCompass()
    assert not cmp.unpin(
        owner_player_id="alice", pin_id="ghost",
    )


def test_pins_for_filter():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="a",
        zone_id="z", x=0, y=0,
    )
    cmp.pin(
        owner_player_id="bob", label="b",
        zone_id="z", x=0, y=0,
    )
    alice_pins = cmp.pins_for(owner_player_id="alice")
    assert len(alice_pins) == 1


def test_reading_includes_distance():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=0, y=10,
    )
    reading = cmp.reading_for(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    assert len(reading.pins) == 1
    assert reading.pins[0].distance == 10.0


def test_reading_north_bearing():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=0, y=10,
    )
    reading = cmp.reading_for(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    # Pin directly north — bearing should be ~0
    assert abs(reading.pins[0].bearing_radians) < 1e-6


def test_reading_east_bearing():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=10, y=0,
    )
    reading = cmp.reading_for(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    # East — bearing should be ~+pi/2
    assert (
        abs(reading.pins[0].bearing_radians - math.pi / 2)
        < 1e-6
    )


def test_reading_same_zone_first():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="far",
        zone_id="other", x=0, y=0,
    )
    cmp.pin(
        owner_player_id="alice", label="near",
        zone_id="z", x=10, y=10,
    )
    reading = cmp.reading_for(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    # same-zone pin should come first
    assert reading.pins[0].label == "near"
    assert reading.pins[0].same_zone


def test_reading_only_owner_pins():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="a",
        zone_id="z", x=0, y=10,
    )
    cmp.pin(
        owner_player_id="bob", label="b",
        zone_id="z", x=0, y=20,
    )
    reading = cmp.reading_for(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    assert len(reading.pins) == 1


def test_check_arrival_clears_close_pin():
    cmp = WayfinderCompass(arrival_radius=10.0)
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=5, y=5,
    )
    cleared = cmp.check_arrival(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    assert len(cleared) == 1
    assert cmp.total_pins() == 0


def test_check_arrival_far_pin_remains():
    cmp = WayfinderCompass(arrival_radius=5.0)
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=100, y=100,
    )
    cleared = cmp.check_arrival(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    assert cleared == ()
    assert cmp.total_pins() == 1


def test_check_arrival_only_owner_pins():
    cmp = WayfinderCompass(arrival_radius=10.0)
    cmp.pin(
        owner_player_id="bob", label="b",
        zone_id="z", x=1, y=1,
    )
    cleared = cmp.check_arrival(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    # Bob's pin not cleared by Alice walking through
    assert cleared == ()
    assert cmp.total_pins() == 1


def test_check_arrival_skips_other_zone():
    cmp = WayfinderCompass(arrival_radius=10.0)
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="other_zone", x=1, y=1,
    )
    cleared = cmp.check_arrival(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    assert cleared == ()


def test_expire_check_removes_old():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=0, y=0,
        now_seconds=0.0, expires_at_seconds=100.0,
    )
    expired = cmp.expire_check(now_seconds=200.0)
    assert len(expired) == 1
    assert cmp.total_pins() == 0


def test_expire_check_keeps_fresh():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=0, y=0,
        now_seconds=0.0, expires_at_seconds=200.0,
    )
    expired = cmp.expire_check(now_seconds=100.0)
    assert expired == ()


def test_expire_check_skips_no_expiry():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=0, y=0,
    )
    expired = cmp.expire_check(now_seconds=10000.0)
    assert expired == ()


def test_color_per_category():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=0, y=10,
        category=PinCategory.NM_SIGHTING,
    )
    reading = cmp.reading_for(
        player_id="alice", zone_id="z", x=0, y=0,
    )
    assert reading.pins[0].color == "red"


def test_visibility_default_private():
    cmp = WayfinderCompass()
    wp = cmp.pin(
        owner_player_id="alice", label="x",
        zone_id="z", x=0, y=0,
    )
    assert wp.visibility == Visibility.PRIVATE


def test_total_pins():
    cmp = WayfinderCompass()
    cmp.pin(
        owner_player_id="a", label="x",
        zone_id="z", x=0, y=0,
    )
    cmp.pin(
        owner_player_id="b", label="x",
        zone_id="z", x=0, y=0,
    )
    assert cmp.total_pins() == 2
