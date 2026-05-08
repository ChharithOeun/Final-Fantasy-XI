"""Tests for vr_torch_lighting."""
from __future__ import annotations

from server.vr_torch_lighting import (
    Hand, LightKind, LightSource, VrTorchLighting,
)


def test_equip_default_torch():
    t = VrTorchLighting()
    assert t.equip(
        player_id="bob", kind=LightKind.TORCH,
        hand=Hand.RIGHT,
    ) is True
    h = t.held(player_id="bob")
    assert h is not None
    assert h.kind == LightKind.TORCH
    assert h.is_lit is True
    # Default fuel ~ 900s
    assert h.fuel_remaining_s == 900.0


def test_equip_blank_blocked():
    t = VrTorchLighting()
    assert t.equip(
        player_id="", kind=LightKind.TORCH,
        hand=Hand.RIGHT,
    ) is False


def test_equip_already_holding_blocked():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.TORCH,
        hand=Hand.RIGHT,
    )
    assert t.equip(
        player_id="bob", kind=LightKind.LANTERN,
        hand=Hand.LEFT,
    ) is False


def test_unequip():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.TORCH,
        hand=Hand.RIGHT,
    )
    assert t.unequip(player_id="bob") is True
    assert t.held(player_id="bob") is None


def test_unequip_unknown():
    t = VrTorchLighting()
    assert t.unequip(player_id="ghost") is False


def test_aim_at():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.TORCH,
        hand=Hand.RIGHT,
    )
    assert t.aim_at(
        player_id="bob", x=5, y=2, z=3,
    ) is True
    h = t.held(player_id="bob")
    assert h.aim_x == 5
    assert h.aim_y == 2
    assert h.aim_z == 3


def test_aim_unequipped_blocked():
    t = VrTorchLighting()
    assert t.aim_at(
        player_id="bob", x=0, y=0, z=0,
    ) is False


def test_tick_burns_fuel():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.PHOSPHOR,
        hand=Hand.LEFT,
    )
    t.tick(player_id="bob", elapsed_s=30.0)
    h = t.held(player_id="bob")
    # PHOSPHOR starts at 120s -> 90s
    assert h.fuel_remaining_s == 90.0


def test_tick_runs_out():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.PHOSPHOR,
        hand=Hand.LEFT,
    )
    t.tick(player_id="bob", elapsed_s=200.0)
    h = t.held(player_id="bob")
    assert h.fuel_remaining_s == 0.0
    assert h.is_lit is False


def test_tick_infinite_fuel():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.GLOW_STONE,
        hand=Hand.RIGHT,
    )
    t.tick(player_id="bob", elapsed_s=999999.0)
    h = t.held(player_id="bob")
    assert h.fuel_remaining_s == -1.0
    assert h.is_lit is True


def test_refuel_lantern():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.LANTERN,
        hand=Hand.RIGHT,
    )
    t.tick(player_id="bob", elapsed_s=600.0)
    # Now at 1200s
    assert t.refuel(
        player_id="bob", fuel_s=300.0,
    ) is True
    h = t.held(player_id="bob")
    assert h.fuel_remaining_s == 1500.0


def test_refuel_torch_blocked():
    """Torches aren't refuelable."""
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.TORCH,
        hand=Hand.RIGHT,
    )
    assert t.refuel(
        player_id="bob", fuel_s=100.0,
    ) is False


def test_refuel_doesnt_exceed_default():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.LANTERN,
        hand=Hand.RIGHT,
    )
    # At default 1800s, refuel by 1000 should clamp at 1800
    t.refuel(player_id="bob", fuel_s=1000.0)
    h = t.held(player_id="bob")
    assert h.fuel_remaining_s == 1800.0


def test_refuel_unequipped_blocked():
    t = VrTorchLighting()
    assert t.refuel(
        player_id="bob", fuel_s=100.0,
    ) is False


def test_refuel_zero_blocked():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.LANTERN,
        hand=Hand.RIGHT,
    )
    assert t.refuel(
        player_id="bob", fuel_s=0,
    ) is False


def test_held_unknown_player():
    t = VrTorchLighting()
    assert t.held(player_id="ghost") is None


def test_torch_radius():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.TORCH,
        hand=Hand.RIGHT,
    )
    h = t.held(player_id="bob")
    assert h.radius_m == 8.0


def test_lantern_brighter_than_torch():
    t = VrTorchLighting()
    t.equip(
        player_id="bob", kind=LightKind.LANTERN,
        hand=Hand.RIGHT,
    )
    h = t.held(player_id="bob")
    assert h.radius_m == 12.0


def test_register_custom_light():
    t = VrTorchLighting()
    custom = LightSource(
        kind=LightKind.PHOSPHOR, radius_m=10.0,
        color_temp_k=5000, flicker=False,
        refuelable=True, default_fuel_s=200.0,
    )
    assert t.register_light_kind(source=custom) is True
    t.equip(
        player_id="bob", kind=LightKind.PHOSPHOR,
        hand=Hand.LEFT,
    )
    h = t.held(player_id="bob")
    assert h.radius_m == 10.0


def test_register_zero_radius_blocked():
    t = VrTorchLighting()
    bad = LightSource(
        kind=LightKind.PHOSPHOR, radius_m=0,
        color_temp_k=5000, flicker=False,
        refuelable=False, default_fuel_s=120.0,
    )
    assert t.register_light_kind(source=bad) is False


def test_four_light_kinds():
    assert len(list(LightKind)) == 4
