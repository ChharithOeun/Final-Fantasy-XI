"""Tests for the mounted combat engine.

Run:  python -m pytest server/tests/test_mounted_combat.py -v
"""
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from mounted_combat import (
    CAVALRY_CATALOG,
    CAVALRY_UNLOCK_LEVEL,
    CavalryAction,
    CavalryActionResult,
    CavalryStance,
    MountEquipment,
    MountEquipmentLoadout,
    MountEquipmentSlot,
    SAMPLE_BARDINGS,
    SAMPLE_HEADGEAR,
    SAMPLE_SADDLEBAGS,
    SAMPLE_SADDLES,
    TAME_THRESHOLD_HP_PCT,
    TameResult,
    TameableMonster,
    WILD_MOUNTS,
    attempt_tame,
    can_enter_cavalry_stance,
    resolve_cavalry_action,
    weapon_fit_multiplier,
)
from mounted_combat.cavalry_actions import (
    CAVALRY_LEVEL_SCALING_PER_LEVEL,
    CAVALRY_STANCE_BONUS,
)


# ----------------------------------------------------------------------
# Cavalry stance gate
# ----------------------------------------------------------------------

def test_cavalry_unlock_at_75():
    assert CAVALRY_UNLOCK_LEVEL == 75


def test_low_level_rider_cannot_enter_cavalry():
    assert can_enter_cavalry_stance(
        rider_level=70, mount_level=75,
        mount_is_alive=True,
    ) is False


def test_low_level_mount_cannot_be_cavalry():
    assert can_enter_cavalry_stance(
        rider_level=75, mount_level=70,
        mount_is_alive=True,
    ) is False


def test_dead_mount_cannot_be_cavalry():
    assert can_enter_cavalry_stance(
        rider_level=80, mount_level=80,
        mount_is_alive=False,
    ) is False


def test_lost_mount_cannot_be_cavalry():
    assert can_enter_cavalry_stance(
        rider_level=80, mount_level=80,
        mount_is_alive=True, mount_is_lost=True,
    ) is False


def test_full_grandmaster_can_enter_cavalry():
    assert can_enter_cavalry_stance(
        rider_level=99, mount_level=99,
        mount_is_alive=True,
    ) is True


# ----------------------------------------------------------------------
# Weapon fit
# ----------------------------------------------------------------------

def test_lance_is_canonical_cavalry_weapon():
    assert weapon_fit_multiplier("lance") == 1.20
    assert weapon_fit_multiplier("polearm") == 1.20


def test_great_axe_unwieldy_from_horseback():
    assert weapon_fit_multiplier("great_axe") < 1.0


def test_hand_to_hand_terrible_from_mount():
    assert weapon_fit_multiplier("hand_to_hand") < 0.80


def test_bow_strong_from_horseback():
    """Mounted archers should be effective."""
    assert weapon_fit_multiplier("bow") == 1.15


def test_unknown_weapon_neutral():
    assert weapon_fit_multiplier("dagger") == 1.0


# ----------------------------------------------------------------------
# Cavalry action resolution
# ----------------------------------------------------------------------

def test_cavalry_catalog_has_canonical_actions():
    for required in ("charge", "lance_attack", "trample",
                       "rear_kick", "drive_by_strike"):
        assert required in CAVALRY_CATALOG


def test_charge_requires_minimum_speed():
    """Doc: Charge needs >= 8 m/s. At 5 m/s it should refuse."""
    result = resolve_cavalry_action(
        action_id="charge", stance=CavalryStance.CAVALRY,
        rider_level=80, mount_level=80, mount_is_alive=True,
        current_speed_ms=5.0, weapon_class="lance",
    )
    assert result.success is False
    assert "speed" in result.reason


def test_charge_succeeds_at_full_speed():
    result = resolve_cavalry_action(
        action_id="charge", stance=CavalryStance.CAVALRY,
        rider_level=80, mount_level=80, mount_is_alive=True,
        current_speed_ms=12.0, weapon_class="lance",
    )
    assert result.success is True
    assert result.action.name == "Charge"


def test_lance_attack_no_speed_requirement():
    """Lance Attack can fire from a stand-still."""
    result = resolve_cavalry_action(
        action_id="lance_attack", stance=CavalryStance.CAVALRY,
        rider_level=80, mount_level=80, mount_is_alive=True,
        current_speed_ms=0.0, weapon_class="lance",
    )
    assert result.success is True


def test_transit_stance_blocks_cavalry_actions():
    """A player in TRANSIT mode can't fire cavalry-only actions."""
    result = resolve_cavalry_action(
        action_id="charge", stance=CavalryStance.TRANSIT,
        rider_level=80, mount_level=80, mount_is_alive=True,
        current_speed_ms=12.0, weapon_class="lance",
    )
    assert result.success is False
    assert "stance" in result.reason


def test_dead_mount_refuses_action():
    result = resolve_cavalry_action(
        action_id="charge", stance=CavalryStance.CAVALRY,
        rider_level=80, mount_level=80, mount_is_alive=False,
        current_speed_ms=12.0, weapon_class="lance",
    )
    assert result.success is False
    assert "dead" in result.reason


def test_unknown_action_refuses():
    result = resolve_cavalry_action(
        action_id="ride_of_the_apocalypse",
        stance=CavalryStance.CAVALRY,
        rider_level=80, mount_level=80, mount_is_alive=True,
        current_speed_ms=12.0, weapon_class="lance",
    )
    assert result.success is False
    assert "unknown" in result.reason


def test_low_rider_level_blocks_action():
    result = resolve_cavalry_action(
        action_id="charge", stance=CavalryStance.CAVALRY,
        rider_level=70, mount_level=80, mount_is_alive=True,
        current_speed_ms=12.0, weapon_class="lance",
    )
    assert result.success is False
    assert "75" in result.reason


def test_damage_scales_with_mount_level():
    """+1.5% per mount level over 75."""
    base = resolve_cavalry_action(
        action_id="lance_attack", stance=CavalryStance.CAVALRY,
        rider_level=75, mount_level=75, mount_is_alive=True,
        current_speed_ms=0.0, weapon_class="lance",
    )
    high = resolve_cavalry_action(
        action_id="lance_attack", stance=CavalryStance.CAVALRY,
        rider_level=99, mount_level=99, mount_is_alive=True,
        current_speed_ms=0.0, weapon_class="lance",
    )
    assert high.final_damage_per_target > base.final_damage_per_target


def test_weapon_fit_modifies_damage():
    """Lance > great_axe at the same other parameters."""
    lance = resolve_cavalry_action(
        action_id="lance_attack", stance=CavalryStance.CAVALRY,
        rider_level=80, mount_level=80, mount_is_alive=True,
        current_speed_ms=0.0, weapon_class="lance",
    )
    axe = resolve_cavalry_action(
        action_id="lance_attack", stance=CavalryStance.CAVALRY,
        rider_level=80, mount_level=80, mount_is_alive=True,
        current_speed_ms=0.0, weapon_class="great_axe",
    )
    assert lance.final_damage_per_target > axe.final_damage_per_target


def test_cavalry_aoe_shape_propagated():
    """Result carries the shape so caller can feed aoe_telegraph."""
    result = resolve_cavalry_action(
        action_id="charge", stance=CavalryStance.CAVALRY,
        rider_level=80, mount_level=80, mount_is_alive=True,
        current_speed_ms=12.0, weapon_class="lance",
    )
    assert result.aoe_shape == "cone"
    assert result.aoe_radius_cm == 1000
    assert result.aoe_angle_deg == 60


# ----------------------------------------------------------------------
# Mount equipment
# ----------------------------------------------------------------------

def test_each_slot_type_has_samples():
    assert len(SAMPLE_BARDINGS) >= 3
    assert len(SAMPLE_SADDLES) >= 3
    assert len(SAMPLE_HEADGEAR) >= 3
    assert len(SAMPLE_SADDLEBAGS) >= 3


def test_loadout_starts_empty():
    loadout = MountEquipmentLoadout()
    assert loadout.total_weight() == 0.0
    assert loadout.total_storage_slots() == 0


def test_equip_sets_slot():
    loadout = MountEquipmentLoadout()
    barding = SAMPLE_BARDINGS["leather_barding"]
    prev = loadout.equip(barding)
    assert prev is None
    assert loadout.slots[MountEquipmentSlot.BARDING] is barding


def test_equip_returns_previous():
    loadout = MountEquipmentLoadout()
    loadout.equip(SAMPLE_BARDINGS["leather_barding"])
    prev = loadout.equip(SAMPLE_BARDINGS["scale_barding"])
    assert prev is SAMPLE_BARDINGS["leather_barding"]


def test_total_weight_aggregates():
    loadout = MountEquipmentLoadout()
    loadout.equip(SAMPLE_BARDINGS["scale_barding"])     # 18
    loadout.equip(SAMPLE_SADDLES["knight_saddle"])       # 10
    loadout.equip(SAMPLE_HEADGEAR["iron_chamfron"])      # 8
    loadout.equip(SAMPLE_SADDLEBAGS["small_saddlebag"])  # 2
    assert loadout.total_weight() == 38.0


def test_total_storage_aggregates():
    loadout = MountEquipmentLoadout()
    loadout.equip(SAMPLE_SADDLES["ranger_saddle"])         # 4
    loadout.equip(SAMPLE_SADDLEBAGS["expedition_saddlebag"])  # 32
    assert loadout.total_storage_slots() == 36


def test_aggregated_stats_sum():
    loadout = MountEquipmentLoadout()
    loadout.equip(SAMPLE_BARDINGS["scale_barding"])      # def 60
    loadout.equip(SAMPLE_HEADGEAR["iron_chamfron"])      # def 30
    stats = loadout.aggregated_stats()
    assert stats["defense"] == 90


def test_unequip_clears_slot():
    loadout = MountEquipmentLoadout()
    loadout.equip(SAMPLE_BARDINGS["adaman_barding"])
    removed = loadout.unequip(MountEquipmentSlot.BARDING)
    assert removed.item_id == "adaman_barding"
    assert loadout.slots[MountEquipmentSlot.BARDING] is None
    assert loadout.total_weight() == 0.0


def test_apex_loadout_is_heavy():
    """Adaman barding + knight saddle + iron chamfron + expedition bag."""
    loadout = MountEquipmentLoadout()
    loadout.equip(SAMPLE_BARDINGS["adaman_barding"])      # 44
    loadout.equip(SAMPLE_SADDLES["knight_saddle"])         # 10
    loadout.equip(SAMPLE_HEADGEAR["iron_chamfron"])        # 8
    loadout.equip(SAMPLE_SADDLEBAGS["expedition_saddlebag"])  # 8
    assert loadout.total_weight() == 70.0


def test_equipped_items_listing():
    loadout = MountEquipmentLoadout()
    loadout.equip(SAMPLE_BARDINGS["leather_barding"])
    loadout.equip(SAMPLE_SADDLES["common_saddle"])
    items = loadout.equipped_items()
    assert len(items) == 2


# ----------------------------------------------------------------------
# Monster taming
# ----------------------------------------------------------------------

def _force_succeed_rng() -> random.Random:
    rng = random.Random()
    rng.random = lambda: 0.0   # type: ignore
    return rng


def _force_fail_rng() -> random.Random:
    rng = random.Random()
    rng.random = lambda: 0.99   # type: ignore
    return rng


def test_taming_blocked_below_75():
    result = attempt_tame(
        rider_level=70, rider_has_tame_skill=True,
        monster_species="wolf", monster_hp_pct=0.05,
        rng=_force_succeed_rng(),
    )
    assert result.success is False
    assert "75" in result.reason


def test_taming_requires_skill():
    result = attempt_tame(
        rider_level=80, rider_has_tame_skill=False,
        monster_species="wolf", monster_hp_pct=0.05,
        rng=_force_succeed_rng(),
    )
    assert result.success is False
    assert "skill" in result.reason


def test_taming_requires_low_hp():
    result = attempt_tame(
        rider_level=80, rider_has_tame_skill=True,
        monster_species="wolf", monster_hp_pct=0.50,
        rng=_force_succeed_rng(),
    )
    assert result.success is False
    assert "HP" in result.reason


def test_taming_rejects_unknown_species():
    result = attempt_tame(
        rider_level=80, rider_has_tame_skill=True,
        monster_species="behemoth", monster_hp_pct=0.05,
        rng=_force_succeed_rng(),
    )
    assert result.success is False
    assert "tame" in result.reason


def test_taming_succeeds_with_force_rng():
    result = attempt_tame(
        rider_level=80, rider_has_tame_skill=True,
        monster_species="wolf", monster_hp_pct=0.05,
        rng=_force_succeed_rng(),
    )
    assert result.success is True
    assert result.monster is not None
    assert result.monster.species == "wolf"


def test_high_level_rider_higher_tame_rate():
    """Rider 99 vs wolf (difficulty 75) > rider 75 vs wolf."""
    result_high = attempt_tame(
        rider_level=99, rider_has_tame_skill=True,
        monster_species="wolf", monster_hp_pct=0.05,
        rng=_force_succeed_rng(),   # roll always succeeds
    )
    assert result_high.success_rate > 0.40


def test_below_difficulty_rider_low_rate():
    """Wolf difficulty=75; rider 75 has 0.40 base rate."""
    result = attempt_tame(
        rider_level=75, rider_has_tame_skill=True,
        monster_species="wolf", monster_hp_pct=0.05,
        rng=_force_succeed_rng(),
    )
    # At parity rate is BASE 0.40
    assert result.success_rate == pytest.approx(0.40)


def test_tameable_species_all_have_traits():
    for species, monster in WILD_MOUNTS.items():
        assert isinstance(monster.cavalry_traits, tuple)
        assert len(monster.cavalry_traits) >= 2


def test_dhalmel_high_carry_for_traders():
    dhalmel = WILD_MOUNTS["dhalmel"]
    assert "high_carry" in dhalmel.cavalry_traits


def test_buffalo_trample_strong():
    buffalo = WILD_MOUNTS["buffalo"]
    assert "trample_strong" in buffalo.cavalry_traits


# ----------------------------------------------------------------------
# Integration: full cavalry combat scenario
# ----------------------------------------------------------------------

def test_grandmaster_lancer_charge_scenario():
    """Lvl 99 PLD on lvl 90 chocobo with lance enters cavalry, charges
    a target. Verify damage, AOE shape, all the modifiers compose."""
    assert can_enter_cavalry_stance(
        rider_level=99, mount_level=90,
        mount_is_alive=True,
    ) is True

    result = resolve_cavalry_action(
        action_id="charge", stance=CavalryStance.CAVALRY,
        rider_level=99, mount_level=90, mount_is_alive=True,
        current_speed_ms=14.0, weapon_class="lance",
    )
    assert result.success is True
    # base 400 * (1 + 0.015 * 15) = 400 * 1.225 = 490
    # * 1.20 lance fit * 1.10 stance = 490 * 1.32 = 646.8 -> 647
    expected = int(round(400 * (1 + 0.015 * 15) * 1.20 * 1.10))
    assert result.final_damage_per_target == expected
    # Cone shape preserved for downstream AOE telegraph
    assert result.aoe_shape == "cone"
    assert result.aoe_radius_cm == 1000


def test_constants_match_spec():
    assert CAVALRY_LEVEL_SCALING_PER_LEVEL == 0.015
    assert CAVALRY_STANCE_BONUS == 0.10
    assert TAME_THRESHOLD_HP_PCT == 0.10
