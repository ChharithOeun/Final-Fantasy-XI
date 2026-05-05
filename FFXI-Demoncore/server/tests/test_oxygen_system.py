"""Tests for oxygen system."""
from __future__ import annotations

from server.oxygen_system import (
    BASE_OXYGEN_SECONDS,
    GEAR_BONUS_SECONDS,
    GearKind,
    OxygenSystem,
    SURFACE_BAND,
)


def test_register_happy():
    o = OxygenSystem()
    assert o.register(player_id="p1") is True


def test_register_blank():
    o = OxygenSystem()
    assert o.register(player_id="") is False


def test_register_double_blocked():
    o = OxygenSystem()
    o.register(player_id="p1")
    assert o.register(player_id="p1") is False


def test_capacity_default():
    o = OxygenSystem()
    o.register(player_id="p1")
    s = o.tick(player_id="p1", now_seconds=0)
    assert s.capacity_seconds == BASE_OXYGEN_SECONDS
    assert s.remaining_seconds == BASE_OXYGEN_SECONDS


def test_capacity_with_diving_suit():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.equip_gear(player_id="p1", gear=GearKind.DIVING_SUIT)
    s = o.tick(player_id="p1", now_seconds=0)
    expected = BASE_OXYGEN_SECONDS + GEAR_BONUS_SECONDS[GearKind.DIVING_SUIT]
    assert s.capacity_seconds == expected


def test_capacity_stacks_additive():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.equip_gear(player_id="p1", gear=GearKind.DIVING_SUIT)
    o.equip_gear(player_id="p1", gear=GearKind.PEARL_AMULET)
    s = o.tick(player_id="p1", now_seconds=0)
    expected = (
        BASE_OXYGEN_SECONDS
        + GEAR_BONUS_SECONDS[GearKind.DIVING_SUIT]
        + GEAR_BONUS_SECONDS[GearKind.PEARL_AMULET]
    )
    assert s.capacity_seconds == expected


def test_no_drain_at_surface():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.set_band(player_id="p1", band=SURFACE_BAND, now_seconds=0)
    s = o.tick(player_id="p1", now_seconds=120)
    assert s.remaining_seconds == BASE_OXYGEN_SECONDS
    assert s.drowning is False


def test_drain_underwater():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.set_band(player_id="p1", band=2, now_seconds=0)
    s = o.tick(player_id="p1", now_seconds=30)
    assert abs(s.remaining_seconds - (BASE_OXYGEN_SECONDS - 30)) < 0.01


def test_drowning_at_zero():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.set_band(player_id="p1", band=2, now_seconds=0)
    s = o.tick(player_id="p1", now_seconds=int(BASE_OXYGEN_SECONDS) + 5)
    assert s.remaining_seconds == 0.0
    assert s.drowning is True
    assert o.is_drowning(player_id="p1") is True


def test_surfacing_clears_drowning():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.set_band(player_id="p1", band=2, now_seconds=0)
    o.tick(player_id="p1", now_seconds=int(BASE_OXYGEN_SECONDS) + 5)
    o.set_band(player_id="p1", band=SURFACE_BAND, now_seconds=200)
    assert o.is_drowning(player_id="p1") is False


def test_surface_or_pocket_refills():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.set_band(player_id="p1", band=2, now_seconds=0)
    o.tick(player_id="p1", now_seconds=30)
    o.surface_or_pocket(player_id="p1", now_seconds=30)
    s = o.tick(player_id="p1", now_seconds=30)
    assert s.remaining_seconds == BASE_OXYGEN_SECONDS


def test_apply_drain_extra():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.set_band(player_id="p1", band=2, now_seconds=0)
    o.apply_drain(
        player_id="p1", drain_seconds=20, now_seconds=10,
    )
    s = o.tick(player_id="p1", now_seconds=10)
    # 10s elapsed underwater = -10, then -20 drain = -30
    assert abs(s.remaining_seconds - (BASE_OXYGEN_SECONDS - 30)) < 0.01


def test_unequip_caps_remaining():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.equip_gear(player_id="p1", gear=GearKind.DIVING_SUIT)
    s = o.tick(player_id="p1", now_seconds=0)
    assert s.remaining_seconds > BASE_OXYGEN_SECONDS
    o.unequip_gear(player_id="p1", gear=GearKind.DIVING_SUIT)
    s = o.tick(player_id="p1", now_seconds=0)
    assert s.remaining_seconds == BASE_OXYGEN_SECONDS


def test_equip_increases_remaining_for_drained_player():
    o = OxygenSystem()
    o.register(player_id="p1")
    o.set_band(player_id="p1", band=2, now_seconds=0)
    o.tick(player_id="p1", now_seconds=40)  # 20s left
    o.equip_gear(player_id="p1", gear=GearKind.DIVING_SUIT)
    s = o.tick(player_id="p1", now_seconds=40)
    # Should add the +180 bonus to remaining
    assert s.remaining_seconds == 20 + GEAR_BONUS_SECONDS[GearKind.DIVING_SUIT]


def test_unknown_player_returns_none():
    o = OxygenSystem()
    assert o.tick(player_id="ghost", now_seconds=0) is None
    assert o.is_drowning(player_id="ghost") is False
