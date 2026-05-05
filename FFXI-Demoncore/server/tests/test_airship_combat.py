"""Tests for airship combat."""
from __future__ import annotations

from server.airship_combat import (
    AirshipClass,
    AirshipCombat,
    CLASS_HP_MAX,
    GRAPPLE_SPEED_GAP_MAX,
)


def test_register_happy():
    c = AirshipCombat()
    assert c.register(
        ship_id="s1", ship_class=AirshipClass.GUNBOAT,
    ) is True
    assert c.hp_of(ship_id="s1") == CLASS_HP_MAX[AirshipClass.GUNBOAT]


def test_register_blank():
    c = AirshipCombat()
    assert c.register(
        ship_id="", ship_class=AirshipClass.GUNBOAT,
    ) is False


def test_register_double_blocked():
    c = AirshipCombat()
    c.register(ship_id="s1", ship_class=AirshipClass.GUNBOAT)
    assert c.register(
        ship_id="s1", ship_class=AirshipClass.SKIFF,
    ) is False


def test_change_band():
    c = AirshipCombat()
    c.register(ship_id="s1", ship_class=AirshipClass.GUNBOAT, band=2)
    assert c.change_band(ship_id="s1", new_band=3) is True


def test_change_band_unknown():
    c = AirshipCombat()
    assert c.change_band(ship_id="ghost", new_band=2) is False


def test_cannon_volley_happy():
    c = AirshipCombat()
    c.register(
        ship_id="a", ship_class=AirshipClass.GUNBOAT,
        gun_count=8, crew_skill=20,
    )
    c.register(
        ship_id="t", ship_class=AirshipClass.SKIFF,
    )
    r = c.cannon_volley(attacker_id="a", target_id="t")
    assert r.accepted is True
    assert r.damage_dealt > 0
    assert r.target_hp_after < CLASS_HP_MAX[AirshipClass.SKIFF]


def test_volley_band_mismatch_blocked():
    c = AirshipCombat()
    c.register(
        ship_id="a", ship_class=AirshipClass.GUNBOAT,
        gun_count=8, band=2,
    )
    c.register(
        ship_id="t", ship_class=AirshipClass.SKIFF, band=3,
    )
    r = c.cannon_volley(attacker_id="a", target_id="t")
    assert r.accepted is False
    assert r.reason == "band mismatch"


def test_volley_no_guns_blocked():
    c = AirshipCombat()
    c.register(
        ship_id="a", ship_class=AirshipClass.SKIFF,
        gun_count=0,
    )
    c.register(ship_id="t", ship_class=AirshipClass.SKIFF)
    r = c.cannon_volley(attacker_id="a", target_id="t")
    assert r.accepted is False


def test_volley_unknown_ship():
    c = AirshipCombat()
    r = c.cannon_volley(attacker_id="ghost", target_id="other")
    assert r.accepted is False


def test_volley_resist_reduces_damage():
    c = AirshipCombat()
    c.register(
        ship_id="a", ship_class=AirshipClass.GUNBOAT,
        gun_count=8,
    )
    c.register(ship_id="skiff_t", ship_class=AirshipClass.SKIFF)
    c.register(ship_id="dread_t", ship_class=AirshipClass.DREADNOUGHT)
    r1 = c.cannon_volley(attacker_id="a", target_id="skiff_t")
    r2 = c.cannon_volley(attacker_id="a", target_id="dread_t")
    # dreadnought resist > skiff resist; same volley does less to dread
    assert r2.damage_dealt < r1.damage_dealt


def test_ram_does_self_damage():
    c = AirshipCombat()
    c.register(
        ship_id="a", ship_class=AirshipClass.GUNBOAT,
    )
    c.register(ship_id="t", ship_class=AirshipClass.SKIFF)
    r = c.ram(attacker_id="a", target_id="t")
    assert r.accepted is True
    assert r.damage_dealt > 0
    assert r.self_damage > 0
    assert r.attacker_hp_after < CLASS_HP_MAX[AirshipClass.GUNBOAT]


def test_ram_band_mismatch_blocked():
    c = AirshipCombat()
    c.register(
        ship_id="a", ship_class=AirshipClass.GUNBOAT, band=2,
    )
    c.register(
        ship_id="t", ship_class=AirshipClass.SKIFF, band=4,
    )
    r = c.ram(attacker_id="a", target_id="t")
    assert r.accepted is False


def test_grapple_happy():
    c = AirshipCombat()
    c.register(
        ship_id="a", ship_class=AirshipClass.GUNBOAT, speed=1.0,
    )
    c.register(
        ship_id="t", ship_class=AirshipClass.SKIFF, speed=1.2,
    )
    r = c.grapple(attacker_id="a", target_id="t")
    assert r.accepted is True
    assert r.grappled is True


def test_grapple_speed_gap_blocked():
    c = AirshipCombat()
    c.register(
        ship_id="a", ship_class=AirshipClass.GUNBOAT, speed=1.0,
    )
    c.register(
        ship_id="t", ship_class=AirshipClass.SKIFF,
        speed=1.0 + GRAPPLE_SPEED_GAP_MAX + 0.5,
    )
    r = c.grapple(attacker_id="a", target_id="t")
    assert r.accepted is False
    assert r.reason == "speed gap too wide"


def test_grapple_band_mismatch_blocked():
    c = AirshipCombat()
    c.register(
        ship_id="a", ship_class=AirshipClass.GUNBOAT,
        speed=1.0, band=2,
    )
    c.register(
        ship_id="t", ship_class=AirshipClass.SKIFF,
        speed=1.0, band=4,
    )
    r = c.grapple(attacker_id="a", target_id="t")
    assert r.accepted is False


def test_skill_bonus_increases_volley():
    c = AirshipCombat()
    c.register(
        ship_id="green", ship_class=AirshipClass.GUNBOAT,
        gun_count=8, crew_skill=0,
    )
    c.register(
        ship_id="vet", ship_class=AirshipClass.GUNBOAT,
        gun_count=8, crew_skill=50,
    )
    c.register(ship_id="t1", ship_class=AirshipClass.SKIFF)
    c.register(ship_id="t2", ship_class=AirshipClass.SKIFF)
    r_green = c.cannon_volley(attacker_id="green", target_id="t1")
    r_vet = c.cannon_volley(attacker_id="vet", target_id="t2")
    assert r_vet.damage_dealt > r_green.damage_dealt


def test_hp_of_unknown():
    c = AirshipCombat()
    assert c.hp_of(ship_id="ghost") == 0
