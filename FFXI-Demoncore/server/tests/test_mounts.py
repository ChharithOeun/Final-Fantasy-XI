"""Tests for the mount engine.

Run:  python -m pytest server/tests/test_mounts.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from mounts import (
    AUTO_ATTACK_DMG_MULT,
    AbsorptionResult,
    AggroSense,
    CAST_TIME_MULT,
    DamageAbsorption,
    MOUNT_LOSS_THRESHOLD,
    MOUNT_LOSS_WINDOW_SECONDS,
    MountAggroModifier,
    MountProgression,
    MountSnapshot,
    MountType,
    MountedActionModifiers,
    WEAPON_SKILL_TP_COST_MULT,
    XP_PER_HOSTILE_ZONE_RIDE,
    XP_PER_RACE_WIN,
    spawn_chocobo,
    stats_for_level,
)


# ----------------------------------------------------------------------
# Mount stats + spawning
# ----------------------------------------------------------------------

def test_chocobo_base_stats_at_level_20():
    """Doc table: HP 2000, speed 12, def = player_lvl * 5."""
    stats = stats_for_level(MountType.CHOCOBO, 20, rider_level=20)
    assert stats["hp"] == 2000
    assert stats["speed_ms"] == 12.0
    assert stats["defense"] == 100   # player lvl 20 * 5
    assert stats["aggro_range_fraction"] == 0.60


def test_chocobo_scaling_per_level():
    stats = stats_for_level(MountType.CHOCOBO, 30, rider_level=20)
    assert stats["hp"] == 2000 + 200 * 10
    assert stats["speed_ms"] == pytest.approx(12.0 + 0.05 * 10)


def test_spawn_chocobo_full_hp():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    assert mount.mount_type == MountType.CHOCOBO
    assert mount.current_hp == mount.max_hp == 2000
    assert mount.is_alive is True


def test_level_30_chocobo_unlocks_sprint():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=30, rider_level=30)
    assert "sprint" in mount.abilities_unlocked


def test_low_level_chocobo_no_sprint():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    assert "sprint" not in mount.abilities_unlocked


def test_wyvern_lighter_hp_scaling():
    """Wyvern post-v1 reservation uses 0.85x HP factor (faster but
    fragile)."""
    chocobo_hp = stats_for_level(MountType.CHOCOBO, 30, rider_level=30)["hp"]
    wyvern_hp = stats_for_level(MountType.WYVERN, 30, rider_level=30)["hp"]
    assert wyvern_hp < chocobo_hp


# ----------------------------------------------------------------------
# Damage absorption
# ----------------------------------------------------------------------

def test_partial_absorption_no_spillover():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    abs_eng = DamageAbsorption()
    result = abs_eng.apply_damage(mount, incoming_dmg=1500)
    assert result.mount_dmg_absorbed == 1500
    assert result.rider_dmg_spillover == 0
    assert result.mount_died is False
    assert mount.current_hp == 500


def test_full_absorption_kills_mount_no_spillover():
    """If incoming_dmg == mount_hp exactly, mount dies but no spillover."""
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    mount.current_hp = 500
    abs_eng = DamageAbsorption()
    result = abs_eng.apply_damage(mount, incoming_dmg=500)
    assert result.mount_died is True
    assert result.mount_dmg_absorbed == 500
    assert result.rider_dmg_spillover == 0
    assert mount.is_alive is False


def test_overkill_spills_to_rider():
    """Doc example: 1500 dmg vs mount with 100 HP left → mount dies,
    1400 spills to rider."""
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    mount.current_hp = 100
    abs_eng = DamageAbsorption()
    result = abs_eng.apply_damage(mount, incoming_dmg=1500)
    assert result.mount_died is True
    assert result.mount_dmg_absorbed == 100
    assert result.rider_dmg_spillover == 1400


def test_dead_mount_no_absorption():
    """Damage to an already-dead mount goes entirely to the rider."""
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    mount.is_alive = False
    mount.current_hp = 0
    abs_eng = DamageAbsorption()
    result = abs_eng.apply_damage(mount, incoming_dmg=500)
    assert result.mount_dmg_absorbed == 0
    assert result.rider_dmg_spillover == 500


def test_zero_damage_returns_neutral():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    result = DamageAbsorption().apply_damage(mount, incoming_dmg=0)
    assert result.mount_dmg_absorbed == 0
    assert result.rider_dmg_spillover == 0


def test_heal_clamps_to_max():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    mount.current_hp = 1500
    healed = DamageAbsorption().heal(mount, amount=2000)
    assert healed == 500
    assert mount.current_hp == mount.max_hp


def test_heal_dead_mount_does_nothing():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    mount.is_alive = False
    mount.current_hp = 0
    healed = DamageAbsorption().heal(mount, amount=2000)
    assert healed == 0


def test_gysahl_greens_30_pct_heal():
    """Doc: gysahl greens restore 30% HP."""
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    mount.current_hp = 100   # nearly dead
    healed = DamageAbsorption().feed_gysahl_greens(mount)
    assert healed == 600   # 30% of 2000 = 600


# ----------------------------------------------------------------------
# Mounted action modifiers
# ----------------------------------------------------------------------

def test_auto_attack_half_damage():
    assert AUTO_ATTACK_DMG_MULT == 0.50
    assert MountedActionModifiers.adjusted_auto_attack_damage(100) == 50


def test_cast_time_50pct_longer():
    assert CAST_TIME_MULT == 1.50
    assert MountedActionModifiers.adjusted_cast_time(2.0) == 3.0


def test_weapon_skill_25pct_more_tp():
    assert WEAPON_SKILL_TP_COST_MULT == 1.25
    assert MountedActionModifiers.adjusted_weapon_skill_tp(100) == 125


def test_two_hour_blocked():
    assert MountedActionModifiers.can_use_two_hour_ability() is False


def test_stealth_blocked():
    assert MountedActionModifiers.can_use_stealth_skill("sneak") is False
    assert MountedActionModifiers.can_use_stealth_skill("invisible") is False
    assert MountedActionModifiers.can_use_stealth_skill("hide") is False
    assert MountedActionModifiers.can_use_stealth_skill("perfect_dodge") is False


def test_other_skills_allowed():
    assert MountedActionModifiers.can_use_stealth_skill("provoke") is True
    assert MountedActionModifiers.can_use_stealth_skill("warcry") is True


def test_zero_inputs_clamp():
    assert MountedActionModifiers.adjusted_cast_time(0) == 0.0
    assert MountedActionModifiers.adjusted_auto_attack_damage(0) == 0
    assert MountedActionModifiers.adjusted_weapon_skill_tp(0) == 0


# ----------------------------------------------------------------------
# Mount progression + permadeath
# ----------------------------------------------------------------------

def test_grant_xp_levels_up():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    prog = MountProgression()
    # Level 21 needs 21 * 100 = 2100 XP
    new_level = prog.grant_xp(mount, xp=2100, rider_level=20)
    assert new_level == 21
    # max_hp got refreshed (one extra level worth of HP)
    assert mount.max_hp == 2000 + 200


def test_grant_xp_through_multiple_levels():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=20, rider_level=20)
    prog = MountProgression()
    # 21->22->23: 2100 + 2200 + 2300 = 6600 XP
    prog.grant_xp(mount, xp=6600, rider_level=20)
    assert mount.level == 23


def test_level_30_triggers_sprint_unlock():
    """Granting enough XP to land on lvl 30 unlocks sprint mid-flight."""
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=29, rider_level=29)
    prog = MountProgression()
    prog.grant_xp(mount, xp=3000, rider_level=29)
    assert mount.level == 30
    assert "sprint" in mount.abilities_unlocked


def test_first_two_deaths_no_loss():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=25, rider_level=25)
    prog = MountProgression()
    assert prog.notify_death(mount, now=0) is False
    prog.attempt_revive_via_stable(mount, rider_level=25)
    assert prog.notify_death(mount, now=1000) is False
    prog.attempt_revive_via_stable(mount, rider_level=25)
    assert mount.is_lost is False


def test_third_death_triggers_permadeath():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=25, rider_level=25)
    prog = MountProgression()
    prog.notify_death(mount, now=0)
    prog.attempt_revive_via_stable(mount, rider_level=25)
    prog.notify_death(mount, now=1000)
    prog.attempt_revive_via_stable(mount, rider_level=25)
    became_lost = prog.notify_death(mount, now=2000)
    assert became_lost is True
    assert mount.is_lost is True


def test_deaths_outside_24h_window_dont_count():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=25, rider_level=25)
    prog = MountProgression()
    prog.notify_death(mount, now=0)
    prog.attempt_revive_via_stable(mount, rider_level=25)
    prog.notify_death(mount, now=1000)
    prog.attempt_revive_via_stable(mount, rider_level=25)
    # Third death 25 hours later — first two should have aged out
    became_lost = prog.notify_death(mount, now=25 * 3600)
    assert became_lost is False
    assert mount.is_lost is False


def test_lost_mount_cannot_be_revived():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=25, rider_level=25)
    mount.is_lost = True
    mount.is_alive = False
    prog = MountProgression()
    assert prog.attempt_revive_via_stable(mount, rider_level=25) is False
    assert mount.is_alive is False


def test_lost_mount_no_xp_gain():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=25, rider_level=25)
    mount.is_lost = True
    mount.is_alive = False
    prog = MountProgression()
    new_level = prog.grant_xp(mount, xp=10000, rider_level=25)
    assert new_level == 25


def test_revive_restores_full_hp():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=25, rider_level=25)
    prog = MountProgression()
    prog.notify_death(mount, now=0)
    prog.attempt_revive_via_stable(mount, rider_level=25)
    assert mount.is_alive is True
    assert mount.current_hp == mount.max_hp


def test_deaths_in_window_count():
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=25, rider_level=25)
    prog = MountProgression()
    for i in range(2):
        prog.notify_death(mount, now=i * 100)
        prog.attempt_revive_via_stable(mount, rider_level=25)
    assert prog.deaths_in_window(mount, now=300) == 2
    assert prog.deaths_in_window(mount, now=25 * 3600) == 0


# ----------------------------------------------------------------------
# Mount aggro modifiers
# ----------------------------------------------------------------------

def test_unmounted_player_no_modifier():
    for sense in AggroSense:
        mult = MountAggroModifier.aggro_range_multiplier(
            sense, is_mounted=False)
        assert mult == 1.0


def test_sound_aggro_15x_when_mounted():
    """Skeletons/ghosts hear hooves at 1.5x range."""
    mult = MountAggroModifier.aggro_range_multiplier(
        AggroSense.SOUND, is_mounted=True)
    assert mult == 1.5


def test_sight_aggro_unchanged_when_mounted():
    mult = MountAggroModifier.aggro_range_multiplier(
        AggroSense.SIGHT, is_mounted=True)
    assert mult == 1.0


def test_true_sight_aggro_unchanged():
    """True-sight mobs (NMs) ignore mount visibility entirely."""
    mult = MountAggroModifier.aggro_range_multiplier(
        AggroSense.TRUE_SIGHT, is_mounted=True)
    assert mult == 1.0


def test_magic_aggro_unchanged():
    """Mount HP doesn't shield mana signature; magic-aggro mobs see
    you the same."""
    mult = MountAggroModifier.aggro_range_multiplier(
        AggroSense.MAGIC, is_mounted=True)
    assert mult == 1.0


def test_scent_aggro_increased():
    """Mounts add scent footprint."""
    mult = MountAggroModifier.aggro_range_multiplier(
        AggroSense.SCENT, is_mounted=True)
    assert mult > 1.0


def test_effective_aggro_range_composes():
    base = 1000.0
    sound_mounted = MountAggroModifier.effective_aggro_range(
        base_range_cm=base, sense=AggroSense.SOUND, is_mounted=True,
    )
    assert sound_mounted == 1500.0


# ----------------------------------------------------------------------
# Integration: travel from Bastok to Norg
# ----------------------------------------------------------------------

def test_bastok_to_norg_travel_scenario():
    """Doc example: trip uses mount HP as a resource. Verify the
    absorption + heal cycle works end-to-end."""
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=25, rider_level=25)
    abs_eng = DamageAbsorption()
    initial_hp = mount.current_hp

    # 1. Outrun goblins through Pashhow — lose ~600 HP
    abs_eng.apply_damage(mount, incoming_dmg=600)
    assert mount.current_hp == initial_hp - 600

    # 2. Stop at Selbina, feed mount — recover 30% (~600 HP)
    healed = abs_eng.feed_gysahl_greens(mount)
    assert healed > 500

    # 3. Ride hard through Buburimu — lose 400 HP
    abs_eng.apply_damage(mount, incoming_dmg=400)

    # Ferry to Mhaura: no HP loss

    # Final ride to Norg: mount survives the trip
    assert mount.is_alive is True
    assert mount.current_hp > 0


def test_overkill_at_low_hp_kills_rider_too():
    """Solo-in-high-tier-zone scenario: small remaining HP, big hit,
    spillover to rider."""
    mount = spawn_chocobo(mount_id="m1", owner_id="alice",
                            level=30, rider_level=30)
    mount.current_hp = 200   # nearly dead
    abs_eng = DamageAbsorption()
    result = abs_eng.apply_damage(mount, incoming_dmg=1500)
    assert result.mount_died is True
    # 1500 - 200 mount HP = 1300 spillover
    assert result.rider_dmg_spillover == 1300


# ----------------------------------------------------------------------
# Constants sanity
# ----------------------------------------------------------------------

def test_loss_constants_match_doc():
    assert MOUNT_LOSS_THRESHOLD == 3
    assert MOUNT_LOSS_WINDOW_SECONDS == 24 * 3600


def test_xp_constants_present():
    assert XP_PER_HOSTILE_ZONE_RIDE > 0
    assert XP_PER_RACE_WIN > XP_PER_HOSTILE_ZONE_RIDE
