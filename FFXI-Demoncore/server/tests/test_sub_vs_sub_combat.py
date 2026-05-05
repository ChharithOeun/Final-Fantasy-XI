"""Tests for sub vs sub combat."""
from __future__ import annotations

from server.sub_vs_sub_combat import (
    SubVsSubCombat,
    WeaponKind,
)


def test_can_engage_happy():
    assert SubVsSubCombat.can_engage(
        attacker_id="a", defender_id="b",
        attacker_zone="abyss_trench",
        defender_zone="abyss_trench",
    ) is True


def test_can_engage_blocks_self():
    assert SubVsSubCombat.can_engage(
        attacker_id="a", defender_id="a",
        attacker_zone="z", defender_zone="z",
    ) is False


def test_can_engage_blocks_different_zone():
    assert SubVsSubCombat.can_engage(
        attacker_id="a", defender_id="b",
        attacker_zone="z", defender_zone="other",
    ) is False


def test_torpedo_full_damage_when_attacker_faster():
    c = SubVsSubCombat()
    r = c.resolve_attack(
        attacker_id="a", defender_id="b",
        weapon=WeaponKind.TORPEDO,
        attacker_speed_bonus=1.5,
        defender_speed_bonus=1.0,
        attacker_depth=200, defender_depth=200,
        attacker_hp=900, defender_hp=900,
    )
    assert r.accepted is True
    assert r.damage_dealt == 350
    assert r.defender_hp_after == 550


def test_torpedo_half_damage_when_defender_faster():
    c = SubVsSubCombat()
    r = c.resolve_attack(
        attacker_id="a", defender_id="b",
        weapon=WeaponKind.TORPEDO,
        attacker_speed_bonus=1.0,
        defender_speed_bonus=2.0,
        attacker_depth=200, defender_depth=200,
        attacker_hp=900, defender_hp=900,
    )
    # defender 2x faster -> 50% damage
    assert r.damage_dealt == 175


def test_depth_charge_full_damage():
    c = SubVsSubCombat()
    r = c.resolve_attack(
        attacker_id="a", defender_id="b",
        weapon=WeaponKind.DEPTH_CHARGE,
        attacker_speed_bonus=1.0,
        defender_speed_bonus=2.0,
        attacker_depth=200, defender_depth=200,
        attacker_hp=900, defender_hp=900,
    )
    # depth charge isn't dodged by speed
    assert r.damage_dealt == 250


def test_ramming_self_damage():
    c = SubVsSubCombat()
    r = c.resolve_attack(
        attacker_id="a", defender_id="b",
        weapon=WeaponKind.RAMMING,
        attacker_speed_bonus=1.0,
        defender_speed_bonus=1.0,
        attacker_depth=200, defender_depth=200,
        attacker_hp=2000, defender_hp=2000,
    )
    # ram base 900; self 60% = 540
    assert r.damage_dealt == 900
    assert r.self_damage == 540


def test_shooting_up_penalty():
    c = SubVsSubCombat()
    r = c.resolve_attack(
        attacker_id="a", defender_id="b",
        weapon=WeaponKind.DEPTH_CHARGE,
        attacker_speed_bonus=1.0,
        defender_speed_bonus=1.0,
        attacker_depth=400, defender_depth=200,  # shooting up
        attacker_hp=900, defender_hp=900,
    )
    # 250 * 0.75 = 187
    assert r.damage_dealt == 187


def test_breach_at_zero_hp():
    c = SubVsSubCombat()
    r = c.resolve_attack(
        attacker_id="a", defender_id="b",
        weapon=WeaponKind.RAMMING,
        attacker_speed_bonus=1.0,
        defender_speed_bonus=1.0,
        attacker_depth=200, defender_depth=200,
        attacker_hp=2000, defender_hp=500,
    )
    assert r.defender_breached is True
    assert r.defender_hp_after == 0


def test_attacker_can_self_breach_with_ramming():
    c = SubVsSubCombat()
    # 60% of 900 = 540 self damage; if attacker has 400 hp -> breach
    r = c.resolve_attack(
        attacker_id="a", defender_id="b",
        weapon=WeaponKind.RAMMING,
        attacker_speed_bonus=1.0,
        defender_speed_bonus=1.0,
        attacker_depth=200, defender_depth=200,
        attacker_hp=400, defender_hp=2000,
    )
    assert r.attacker_breached is True


def test_self_targeting_rejected():
    c = SubVsSubCombat()
    r = c.resolve_attack(
        attacker_id="a", defender_id="a",
        weapon=WeaponKind.TORPEDO,
        attacker_speed_bonus=1.0,
        defender_speed_bonus=1.0,
        attacker_depth=200, defender_depth=200,
        attacker_hp=900, defender_hp=900,
    )
    assert r.accepted is False


def test_dead_sub_rejected():
    c = SubVsSubCombat()
    r = c.resolve_attack(
        attacker_id="a", defender_id="b",
        weapon=WeaponKind.TORPEDO,
        attacker_speed_bonus=1.0,
        defender_speed_bonus=1.0,
        attacker_depth=200, defender_depth=200,
        attacker_hp=900, defender_hp=0,
    )
    assert r.accepted is False


def test_profile_lookup():
    p = SubVsSubCombat.profile_for(weapon=WeaponKind.RAMMING)
    assert p.base_damage == 900
    assert p.self_damage_pct == 60


def test_torpedo_zero_attacker_speed_safe():
    c = SubVsSubCombat()
    # divide-by-zero protection
    r = c.resolve_attack(
        attacker_id="a", defender_id="b",
        weapon=WeaponKind.TORPEDO,
        attacker_speed_bonus=0,
        defender_speed_bonus=2.0,
        attacker_depth=200, defender_depth=200,
        attacker_hp=900, defender_hp=900,
    )
    assert r.accepted is True
