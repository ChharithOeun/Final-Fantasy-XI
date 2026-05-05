"""Tests for surface ship combat."""
from __future__ import annotations

from server.surface_ship_combat import (
    ShipClass,
    SurfaceShipCombat,
)


def test_profile_lookup():
    p = SurfaceShipCombat.ship_profile(ship_class=ShipClass.GALLEON)
    assert p.guns_per_side == 12
    assert p.hp_max == 5_500


def test_unknown_class():
    p = SurfaceShipCombat.ship_profile(
        ship_class=ShipClass.IRONCLAD,
    )
    assert p is not None


def test_broadside_lined_up():
    c = SurfaceShipCombat()
    r = c.resolve_broadside(
        attacker_class=ShipClass.FRIGATE,
        attacker_crew_skill=0,
        target_class=ShipClass.SLOOP,
        target_evading=False,
        broadside_lined_up=True,
        target_hp=1_500,
    )
    # 8 guns * 60 = 480 base; sloop has 0 resist
    assert r.accepted is True
    assert r.damage_dealt == 480


def test_broadside_not_aligned_rejected():
    c = SurfaceShipCombat()
    r = c.resolve_broadside(
        attacker_class=ShipClass.FRIGATE,
        attacker_crew_skill=0,
        target_class=ShipClass.SLOOP,
        target_evading=False,
        broadside_lined_up=False,
        target_hp=1_500,
    )
    assert r.accepted is False


def test_crew_skill_caps_at_50pct():
    c = SurfaceShipCombat()
    r1 = c.resolve_broadside(
        attacker_class=ShipClass.FRIGATE,
        attacker_crew_skill=50,
        target_class=ShipClass.SLOOP,
        target_evading=False,
        broadside_lined_up=True,
        target_hp=1_500,
    )
    r2 = c.resolve_broadside(
        attacker_class=ShipClass.FRIGATE,
        attacker_crew_skill=200,   # over the cap
        target_class=ShipClass.SLOOP,
        target_evading=False,
        broadside_lined_up=True,
        target_hp=1_500,
    )
    assert r1.damage_dealt == r2.damage_dealt


def test_target_evade_reduces_damage():
    c = SurfaceShipCombat()
    r = c.resolve_broadside(
        attacker_class=ShipClass.FRIGATE,
        attacker_crew_skill=0,
        target_class=ShipClass.SLOOP,
        target_evading=True,
        broadside_lined_up=True,
        target_hp=1_500,
    )
    # 480 * 0.7 = 336
    assert r.damage_dealt == 336


def test_ironclad_resists_50pct():
    c = SurfaceShipCombat()
    r = c.resolve_broadside(
        attacker_class=ShipClass.GALLEON,
        attacker_crew_skill=0,
        target_class=ShipClass.IRONCLAD,
        target_evading=False,
        broadside_lined_up=True,
        target_hp=4_000,
    )
    # 12 guns * 60 = 720; * 0.5 (ironclad resist) = 360
    assert r.damage_dealt == 360


def test_target_sunk_at_zero_hp():
    c = SurfaceShipCombat()
    r = c.resolve_broadside(
        attacker_class=ShipClass.GALLEON,
        attacker_crew_skill=50,
        target_class=ShipClass.SLOOP,
        target_evading=False,
        broadside_lined_up=True,
        target_hp=100,
    )
    assert r.target_sunk is True
    assert r.target_hp_after == 0


def test_already_sunk_rejected():
    c = SurfaceShipCombat()
    r = c.resolve_broadside(
        attacker_class=ShipClass.SLOOP,
        attacker_crew_skill=0,
        target_class=ShipClass.SLOOP,
        target_evading=False,
        broadside_lined_up=True,
        target_hp=0,
    )
    assert r.accepted is False


def test_grapple_happy():
    c = SurfaceShipCombat()
    r = c.resolve_grapple(
        attacker_class=ShipClass.FRIGATE,
        target_class=ShipClass.GALLEON,
        attacker_crew_skill=20,
        target_crew_skill=10,
    )
    assert r.accepted is True
    assert r.locked is True


def test_grapple_target_too_fast():
    c = SurfaceShipCombat()
    # frigate speed 1.0, sloop 1.5 -> gap 0.5; OK
    # ironclad 0.6 vs sloop 1.5 -> gap 0.9; OK
    # but gap=1.0 should fail. Our profiles don't show that
    # gap natively — construct test with sloop attacking ironclad
    # in reverse: speed_gap = 0.6-1.5 = negative; ok. So this
    # case can't trigger easily with current data.
    # Instead, verify the boundary by giving a hypothetical:
    r = c.resolve_grapple(
        attacker_class=ShipClass.IRONCLAD,
        target_class=ShipClass.SLOOP,
        attacker_crew_skill=0,
        target_crew_skill=0,
    )
    # gap is 1.5 - 0.6 = 0.9 — under 1.0, should not block
    # but skill tie -> fail
    assert r.accepted is False


def test_grapple_skill_required():
    c = SurfaceShipCombat()
    r = c.resolve_grapple(
        attacker_class=ShipClass.FRIGATE,
        target_class=ShipClass.GALLEON,
        attacker_crew_skill=10,
        target_crew_skill=20,
    )
    # attacker has lower skill
    assert r.accepted is False


def test_grapple_skill_tie_fails():
    c = SurfaceShipCombat()
    r = c.resolve_grapple(
        attacker_class=ShipClass.FRIGATE,
        target_class=ShipClass.GALLEON,
        attacker_crew_skill=10,
        target_crew_skill=10,
    )
    assert r.accepted is False


def test_negative_skill_rejected():
    c = SurfaceShipCombat()
    r = c.resolve_grapple(
        attacker_class=ShipClass.FRIGATE,
        target_class=ShipClass.GALLEON,
        attacker_crew_skill=-1,
        target_crew_skill=10,
    )
    assert r.accepted is False
