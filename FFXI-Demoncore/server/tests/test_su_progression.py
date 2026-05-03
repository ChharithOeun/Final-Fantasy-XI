"""Tests for Su gear progression — Su5 i-lvl ladder + fuel-feed
upgrade pattern."""
from __future__ import annotations

import pytest

from server.su_progression import (
    SU_BASE_ILVL,
    SU_LADDER_TIERS,
    FuelRequirement,
    PlayerSuProgression,
    SuArchetype,
    SuFuelTier,
    SuKind,
    SuSlot,
    apply_su_tier_bonus,
    base_stat_block,
    fuel_required,
    ilvl_for_su_tier,
    kind_for_slot,
)


def test_ilvl_for_tier_starts_at_119():
    assert ilvl_for_su_tier(0) == SU_BASE_ILVL == 119


def test_ilvl_for_tier_max_reaches_175():
    assert ilvl_for_su_tier(SU_LADDER_TIERS - 1) == 175


def test_ilvl_ladder_strictly_monotonic():
    last = -1
    for t in range(SU_LADDER_TIERS):
        cur = ilvl_for_su_tier(t)
        assert cur > last
        last = cur


def test_ilvl_for_tier_out_of_range():
    with pytest.raises(ValueError):
        ilvl_for_su_tier(-1)
    with pytest.raises(ValueError):
        ilvl_for_su_tier(SU_LADDER_TIERS)


def test_kind_for_slot_armor_vs_weapon():
    assert kind_for_slot(SuSlot.HEAD) == SuKind.ARMOR
    assert kind_for_slot(SuSlot.MAIN_HAND_MELEE) == SuKind.WEAPON
    assert kind_for_slot(SuSlot.RANGED) == SuKind.WEAPON


def test_fuel_required_t0_is_free():
    assert fuel_required(kind=SuKind.ARMOR, ilvl_tier=0) == ()


def test_fuel_required_t1_armor_one_su2():
    reqs = fuel_required(kind=SuKind.ARMOR, ilvl_tier=1)
    assert reqs == (FuelRequirement(SuFuelTier.SU2, 1),)


def test_fuel_required_t11_armor_4_tokens():
    reqs = fuel_required(kind=SuKind.ARMOR, ilvl_tier=11)
    assert reqs == (FuelRequirement(SuFuelTier.SU5_TOKEN, 4),)


def test_weapons_double_armor_fuel():
    """Weapons need 2x the fuel armor needs at every tier."""
    for tier in range(1, SU_LADDER_TIERS):
        armor_reqs = fuel_required(kind=SuKind.ARMOR, ilvl_tier=tier)
        weapon_reqs = fuel_required(kind=SuKind.WEAPON, ilvl_tier=tier)
        assert len(weapon_reqs) == len(armor_reqs)
        for ar, wr in zip(armor_reqs, weapon_reqs):
            assert wr.fuel_tier == ar.fuel_tier
            assert wr.count == ar.count * 2


def test_base_stat_block_returns_copy():
    b1 = base_stat_block(slot=SuSlot.HEAD)
    b2 = base_stat_block(slot=SuSlot.HEAD)
    b1["str"] = 999
    assert b2["str"] != 999


def test_apply_su_tier_bonus_scales_stats():
    base = base_stat_block(slot=SuSlot.HEAD)
    t0 = apply_su_tier_bonus(base=base, ilvl_tier=0)
    t11 = apply_su_tier_bonus(base=base, ilvl_tier=11)
    assert t0["str"] == base["str"]      # T0 = no bump
    assert t11["str"] > t0["str"]
    assert t11["defense"] > t0["defense"]


def test_apply_su_tier_bonus_preserves_delay_on_weapons():
    """Weapon `delay` is a fixed swing-cycle constant — bumps
    must not inflate it."""
    base = base_stat_block(slot=SuSlot.MAIN_HAND_MELEE)
    t11 = apply_su_tier_bonus(base=base, ilvl_tier=11)
    assert t11["delay"] == base["delay"]
    assert t11["damage"] > base["damage"]


def test_craft_new_starts_at_t0_119():
    prog = PlayerSuProgression(player_id="alice")
    p = prog.craft_new(
        piece_id="head_a", slot=SuSlot.HEAD,
        archetype=SuArchetype.CASTER,
    )
    assert p.ilvl_tier == 0
    assert p.ilvl == 119
    assert p.kind == SuKind.ARMOR
    assert prog.get("head_a") is p


def test_advance_one_tier_with_fuel():
    prog = PlayerSuProgression(player_id="alice")
    prog.craft_new(
        piece_id="hd", slot=SuSlot.HEAD,
        archetype=SuArchetype.CASTER,
    )
    res = prog.advance_ilvl(
        piece_id="hd", target_step=1,
        available_fuel={SuFuelTier.SU2: 5},
    )
    assert res.accepted
    assert res.new_ilvl_tier == 1
    assert res.new_ilvl == 125
    assert FuelRequirement(SuFuelTier.SU2, 1) in res.fuel_consumed


def test_advance_skipping_tiers_rejected():
    prog = PlayerSuProgression(player_id="alice")
    prog.craft_new(
        piece_id="hd", slot=SuSlot.HEAD,
        archetype=SuArchetype.CASTER,
    )
    res = prog.advance_ilvl(
        piece_id="hd", target_step=2,
        available_fuel={SuFuelTier.SU2: 99, SuFuelTier.SU3: 99},
    )
    assert not res.accepted
    assert "one tier at a time" in res.reason


def test_advance_without_fuel_rejected():
    prog = PlayerSuProgression(player_id="alice")
    prog.craft_new(
        piece_id="hd", slot=SuSlot.HEAD,
        archetype=SuArchetype.CASTER,
    )
    res = prog.advance_ilvl(piece_id="hd", target_step=1)
    assert not res.accepted
    assert "fuel" in res.reason


def test_advance_unknown_piece_rejected():
    prog = PlayerSuProgression(player_id="alice")
    res = prog.advance_ilvl(
        piece_id="ghost", target_step=1,
        available_fuel={SuFuelTier.SU2: 1},
    )
    assert not res.accepted


def test_advance_at_max_rejected():
    prog = PlayerSuProgression(player_id="alice")
    prog.craft_new(
        piece_id="hd", slot=SuSlot.HEAD,
        archetype=SuArchetype.CASTER,
    )
    # Climb to top
    big_pool = {
        SuFuelTier.SU2: 99, SuFuelTier.SU3: 99,
        SuFuelTier.SU4: 99, SuFuelTier.SU5_TOKEN: 99,
    }
    for tier in range(1, SU_LADDER_TIERS):
        prog.advance_ilvl(
            piece_id="hd", target_step=tier,
            available_fuel=big_pool,
        )
    # Try to push past the cap
    over = prog.advance_ilvl(
        piece_id="hd", target_step=SU_LADDER_TIERS,
        available_fuel=big_pool,
    )
    assert not over.accepted


def test_can_advance_returns_false_at_top():
    prog = PlayerSuProgression(player_id="alice")
    prog.craft_new(
        piece_id="hd", slot=SuSlot.HEAD,
        archetype=SuArchetype.CASTER,
    )
    assert prog.can_advance(piece_id="hd")
    big_pool = {
        SuFuelTier.SU2: 99, SuFuelTier.SU3: 99,
        SuFuelTier.SU4: 99, SuFuelTier.SU5_TOKEN: 99,
    }
    for tier in range(1, SU_LADDER_TIERS):
        prog.advance_ilvl(
            piece_id="hd", target_step=tier,
            available_fuel=big_pool,
        )
    assert not prog.can_advance(piece_id="hd")


def test_full_climb_armor_total_fuel():
    """Verify the lifetime fuel cost for a full T0 -> T11 climb
    matches what individual steps require."""
    prog = PlayerSuProgression(player_id="alice")
    totals = prog.total_fuel_for_full_climb(kind=SuKind.ARMOR)
    # Manually sum the table
    expected: dict[SuFuelTier, int] = {}
    for t in range(1, SU_LADDER_TIERS):
        for r in fuel_required(kind=SuKind.ARMOR, ilvl_tier=t):
            expected[r.fuel_tier] = (
                expected.get(r.fuel_tier, 0) + r.count
            )
    assert totals == expected
    # Sanity: tokens dominate the late game
    assert totals[SuFuelTier.SU5_TOKEN] >= totals[SuFuelTier.SU2]


def test_full_climb_weapon_costs_more_than_armor():
    prog = PlayerSuProgression(player_id="alice")
    armor_totals = prog.total_fuel_for_full_climb(kind=SuKind.ARMOR)
    weapon_totals = prog.total_fuel_for_full_climb(kind=SuKind.WEAPON)
    for tier, count in armor_totals.items():
        assert weapon_totals[tier] == count * 2


def test_full_lifecycle_su_armor_climb():
    """End-to-end: drop a Su5 head, climb every tier, verify
    final ilvl + stat block."""
    prog = PlayerSuProgression(player_id="alice")
    prog.craft_new(
        piece_id="hd", slot=SuSlot.HEAD,
        archetype=SuArchetype.MELEE,
    )
    pool = {
        SuFuelTier.SU2: 99, SuFuelTier.SU3: 99,
        SuFuelTier.SU4: 99, SuFuelTier.SU5_TOKEN: 99,
    }
    for tier in range(1, SU_LADDER_TIERS):
        res = prog.advance_ilvl(
            piece_id="hd", target_step=tier,
            available_fuel=pool,
        )
        assert res.accepted
        assert res.new_ilvl_tier == tier
    p = prog.get("hd")
    assert p.ilvl == 175
    stats = p.stats()
    base = base_stat_block(slot=SuSlot.HEAD)
    # T11 stats are massively higher than base
    assert stats["str"] > base["str"]
    assert stats["defense"] >= base["defense"] + 11 * 4
