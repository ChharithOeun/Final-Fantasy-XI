"""Tests for the weight physics engine.

Run:  python -m pytest server/tests/test_weight_physics.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from weight_physics import (
    JOB_PROFILES,
    KNOWN_MODIFIERS,
    SPEED_MAX_MULTIPLIER,
    SPEED_MIN_MULTIPLIER,
    StepState,
    WeightModifier,
    WeightModifierStack,
    accuracy_bonus,
    attack_delay_multiplier,
    cast_time,
    interrupt_chance,
    job_modifiers_for,
    speed_multiplier,
)
from weight_physics.formulas import step_multiplier_for


# ----------------------------------------------------------------------
# Speed multiplier
# ----------------------------------------------------------------------

def test_speed_at_baseline_30_is_1():
    assert speed_multiplier(30) == pytest.approx(1.0)


def test_speed_below_30_gets_bonus():
    """A naked Tarutaru at W=1 moves faster than baseline."""
    assert speed_multiplier(1) > 1.0
    # W=1 → 1 - 0.005*(1-30) = 1 + 0.145 = 1.145
    assert speed_multiplier(1) == pytest.approx(1.145)


def test_speed_caps_at_max_multiplier():
    """At very low weight, speed caps at SPEED_MAX_MULTIPLIER (1.2)."""
    assert speed_multiplier(0) == pytest.approx(1.15)
    # Force well below: still capped
    assert speed_multiplier(-1000) == SPEED_MAX_MULTIPLIER


def test_war_at_120_walks():
    """Doc example: WAR at W=120 moves at 0.55× base."""
    assert speed_multiplier(120) == pytest.approx(0.55)


def test_speed_floors_at_min_multiplier():
    """Even at W=200 you can still walk (floor 0.4)."""
    assert speed_multiplier(200) == pytest.approx(0.4)
    # Ridiculous weights stay at floor
    assert speed_multiplier(1000) == SPEED_MIN_MULTIPLIER


def test_nin_at_20_slightly_faster_than_baseline():
    """Doc example: NIN at W=20 moves at 1.05×."""
    assert speed_multiplier(20) == pytest.approx(1.05)


def test_naked_galkan_at_5_moves_at_1_125():
    """Doc example: a naked Galkan at W=5 moves at 1.125×."""
    assert speed_multiplier(5) == pytest.approx(1.125)


# ----------------------------------------------------------------------
# Attack delay
# ----------------------------------------------------------------------

def test_attack_delay_baseline_at_5():
    assert attack_delay_multiplier(5) == pytest.approx(1.0)


def test_bronze_sword_swings_near_instant():
    """Doc example: bronze sword (3) swings at 0.994×."""
    assert attack_delay_multiplier(3) == pytest.approx(0.994)


def test_curtana_swings_at_1_027():
    """Doc example: Curtana (14) swings at 1.027×."""
    assert attack_delay_multiplier(14) == pytest.approx(1.027)


def test_spharai_swings_at_1_081():
    """Doc example: Spharai greataxe (32) swings at 1.081×."""
    assert attack_delay_multiplier(32) == pytest.approx(1.081)


# ----------------------------------------------------------------------
# Cast time
# ----------------------------------------------------------------------

def test_cast_time_at_baseline_weight_stationary():
    """Gear=30, FC=0, stationary, no job mod → 0.85× base."""
    result = cast_time(base_cast_time=4.0, gear_weight=30,
                        fast_cast_mult=0.0, stationary=True,
                        job_modifier=1.0)
    assert result == pytest.approx(4.0 * 0.85)


def test_cast_time_walking_no_stationary_bonus():
    result = cast_time(base_cast_time=4.0, gear_weight=30,
                        fast_cast_mult=0.0, stationary=False,
                        job_modifier=1.0)
    assert result == pytest.approx(4.0)


def test_cast_time_heavy_gear_penalizes():
    """Heavy gear (W=100, +70 over baseline) adds 28% to cast time."""
    result = cast_time(base_cast_time=4.0, gear_weight=100,
                        fast_cast_mult=0.0, stationary=False,
                        job_modifier=1.0)
    # 4.0 * (1 + 0.004 * 70) = 4.0 * 1.28 = 5.12
    assert result == pytest.approx(5.12)


def test_cast_time_fast_cast_reduces():
    result = cast_time(base_cast_time=4.0, gear_weight=30,
                        fast_cast_mult=0.30, stationary=False,
                        job_modifier=1.0)
    # 4.0 * 1.0 * 0.70 * 1.0 * 1.0 = 2.8
    assert result == pytest.approx(2.8)


def test_sch_job_modifier_applies():
    """SCH gets 0.85× cast modifier (Strategos)."""
    result = cast_time(base_cast_time=4.0, gear_weight=30,
                        fast_cast_mult=0.0, stationary=False,
                        job_modifier=0.85)
    assert result == pytest.approx(3.4)


def test_instant_cast_unaffected_by_weight():
    """base_cast_time=0 stays 0 regardless of inputs."""
    result = cast_time(base_cast_time=0, gear_weight=200,
                        fast_cast_mult=0.0, stationary=False,
                        job_modifier=1.0)
    assert result == 0.0


def test_cast_time_combines_all_factors():
    """RDM walking with FC 30%, gear=30, base=2s → 2 * 1 * 0.7 * 1 * 0.9 = 1.26"""
    result = cast_time(base_cast_time=2.0, gear_weight=30,
                        fast_cast_mult=0.30, stationary=False,
                        job_modifier=0.90)
    assert result == pytest.approx(2.0 * 0.70 * 0.90)


# ----------------------------------------------------------------------
# Accuracy bonus
# ----------------------------------------------------------------------

def test_accuracy_zero_when_both_moving():
    assert accuracy_bonus(weapon_weight=14, attacker_still=False,
                            target_still=False) == 0.0


def test_accuracy_full_when_both_still():
    """Curtana stationary + target still: +14 acc."""
    assert accuracy_bonus(weapon_weight=14, attacker_still=True,
                            target_still=True) == 14.0


def test_accuracy_half_when_one_still():
    assert accuracy_bonus(weapon_weight=14, attacker_still=True,
                            target_still=False) == 7.0
    assert accuracy_bonus(weapon_weight=14, attacker_still=False,
                            target_still=True) == 7.0


def test_heavier_weapon_bigger_bonus():
    spharai = accuracy_bonus(weapon_weight=32, attacker_still=True,
                                target_still=True)
    curtana = accuracy_bonus(weapon_weight=14, attacker_still=True,
                                target_still=True)
    assert spharai > curtana


# ----------------------------------------------------------------------
# Interrupt chance
# ----------------------------------------------------------------------

def test_interrupt_baseline_blm_standing_still():
    """BLM at W=30 standing still: base 5% × (1 + 0.30) × 1.0 × 1.0 = 6.5%"""
    chance = interrupt_chance(
        base_chance=0.05, gear_weight=30,
        job_interrupt_resist=1.00, step_multiplier=1.00,
    )
    assert chance == pytest.approx(0.065)


def test_interrupt_nin_resists_heavily():
    """NIN job resist is 0.30. Same scenario: 0.05 × 1.30 × 0.30 × 1.0 = 0.0195"""
    chance = interrupt_chance(
        base_chance=0.05, gear_weight=30,
        job_interrupt_resist=0.30, step_multiplier=1.00,
    )
    assert chance == pytest.approx(0.0195)


def test_interrupt_running_other_job_amplifies():
    """Running with non-walk-cast job: 1.80x step penalty."""
    standing = interrupt_chance(
        base_chance=0.05, gear_weight=30,
        job_interrupt_resist=1.00, step_multiplier=1.00,
    )
    running = interrupt_chance(
        base_chance=0.05, gear_weight=30,
        job_interrupt_resist=1.00, step_multiplier=1.80,
    )
    assert running == pytest.approx(standing * 1.80)


def test_interrupt_clamps_to_one():
    chance = interrupt_chance(
        base_chance=0.99, gear_weight=200,
        job_interrupt_resist=1.00, step_multiplier=1.80,
    )
    assert chance == 1.0


def test_step_multiplier_still_for_anyone():
    assert step_multiplier_for(step_state=StepState.STILL,
                                 job="BLM") == 1.00


def test_step_multiplier_one_step_free_for_all():
    assert step_multiplier_for(step_state=StepState.ONE_STEP,
                                 job="BLM") == 1.00


def test_step_multiplier_walking_rdm_walk_cast():
    assert step_multiplier_for(step_state=StepState.WALKING,
                                 job="RDM") == 1.10
    assert step_multiplier_for(step_state=StepState.WALKING,
                                 job="BRD") == 1.10


def test_step_multiplier_walking_other_jobs_penalized():
    assert step_multiplier_for(step_state=StepState.WALKING,
                                 job="BLM") == 1.40


def test_step_multiplier_running_chainspell():
    assert step_multiplier_for(step_state=StepState.RUNNING,
                                 job="RDM",
                                 is_chainspell_active=True) == 1.10


def test_step_multiplier_running_other_jobs():
    assert step_multiplier_for(step_state=StepState.RUNNING,
                                 job="BLM") == 1.80


def test_nin_signing_ignores_movement():
    """NIN hand signs are kinesthetic + silent — movement irrelevant."""
    for state in (StepState.STILL, StepState.WALKING, StepState.RUNNING):
        assert step_multiplier_for(
            step_state=state, job="NIN", is_signing=True,
        ) == 1.00


# ----------------------------------------------------------------------
# Buff stacking
# ----------------------------------------------------------------------

def test_haste_lifts_effective_weight():
    """WAR at W=120 with Haste III: 120 × 0.6 = 72."""
    stack = WeightModifierStack()
    stack.apply("haste_iii")
    assert stack.effective_weight(120) == pytest.approx(72.0)


def test_haste_plus_march_multiplicative():
    """Doc example: Haste III + March III on WAR W=120
    = 120 × 0.6 × 0.85 = 61.2 (≈ 61.2)"""
    stack = WeightModifierStack()
    stack.apply("haste_iii")
    stack.apply("march_iii")
    assert stack.effective_weight(120) == pytest.approx(61.2)


def test_gravity_increases_effective_weight():
    """Gravity is the bottom-line slow: +50% on top of existing."""
    stack = WeightModifierStack()
    stack.apply("gravity")
    assert stack.effective_weight(120) == pytest.approx(180.0)


def test_gravity_hits_heavy_classes_hardest():
    """Doc example: WAR W=120 Gravity → walking pace; WHM W=12 → 18 (barely)."""
    stack = WeightModifierStack()
    stack.apply("gravity")
    war_eff = stack.effective_weight(120)
    whm_eff = stack.effective_weight(12)
    # The WAR's speed crashes; the WHM barely notices
    assert speed_multiplier(war_eff) == pytest.approx(0.4)   # at floor
    assert speed_multiplier(whm_eff) > 1.0   # still light


def test_encumber_stacks_compound():
    """Encumber +10% per stack: 3 stacks = 1.331×."""
    stack = WeightModifierStack()
    for _ in range(3):
        stack.apply("encumber_stack")
    # We refresh in place; check stack count
    assert stack.stacks_of("encumber_stack") == 3
    # Effective: 100 × 1.10^3 = 133.1
    assert stack.effective_weight(100) == pytest.approx(133.1, rel=1e-4)


def test_modifier_stack_remove():
    stack = WeightModifierStack()
    stack.apply("haste_iii")
    assert stack.has("haste_iii")
    assert stack.remove("haste_iii") is True
    assert not stack.has("haste_iii")
    # Removing again is a no-op
    assert stack.remove("haste_iii") is False


def test_thf_flee_expires_after_60s():
    stack = WeightModifierStack()
    stack.apply("thf_flee", now=0)
    # 30s in: still active
    expired = stack.tick_expirations(now=30)
    assert expired == []
    assert stack.has("thf_flee")
    # 61s in: expired
    expired = stack.tick_expirations(now=61)
    assert "thf_flee" in expired
    assert not stack.has("thf_flee")


def test_unknown_modifier_raises():
    stack = WeightModifierStack()
    with pytest.raises(KeyError, match="unknown modifier"):
        stack.apply("non_existent")


def test_apply_custom_modifier_directly():
    """Custom mods (not in KNOWN_MODIFIERS) can be applied via the
    WeightModifier object directly."""
    stack = WeightModifierStack()
    custom = WeightModifier(name="experimental_drug", multiplier=0.50,
                              duration_seconds=30)
    stack.apply(custom, now=0)
    assert stack.effective_weight(100) == 50


# ----------------------------------------------------------------------
# Job profiles
# ----------------------------------------------------------------------

def test_job_profile_lookup():
    nin = job_modifiers_for("NIN")
    assert nin.job == "NIN"
    assert nin.interrupt_resist == 0.30
    assert nin.uses_hand_signs is True


def test_unknown_job_returns_neutral_profile():
    """Unknown jobs (NPCs / mobs) get a neutral profile."""
    profile = job_modifiers_for("ZGB")   # Zilart Guardian Beast (made up)
    assert profile.interrupt_resist == 1.00
    assert profile.cast_time_modifier == 1.0


def test_rdm_walk_cast_capable():
    rdm = job_modifiers_for("RDM")
    assert rdm.can_walk_cast is True
    assert rdm.can_run_cast_under_chainspell is True
    assert rdm.cast_time_modifier == 0.90


def test_sch_has_lowest_cast_modifier():
    sch = job_modifiers_for("SCH")
    assert sch.cast_time_modifier == 0.85
    assert sch.interrupt_resist == 0.80


def test_blm_has_full_interrupt_chance():
    blm = job_modifiers_for("BLM")
    assert blm.interrupt_resist == 1.00


# ----------------------------------------------------------------------
# Integration: realistic combat scenarios
# ----------------------------------------------------------------------

def test_war_haste_iii_runs_almost_normal():
    """WAR W=120 with Haste III: 120 × 0.6 = 72 → speed ≈ 0.79"""
    stack = WeightModifierStack()
    stack.apply("haste_iii")
    eff = stack.effective_weight(120)
    speed = speed_multiplier(eff)
    assert speed == pytest.approx(0.79, abs=0.01)


def test_blm_walking_firaga_iii_high_interrupt_risk():
    """BLM in heavy gear walking through a Firaga III cast: hefty interrupt."""
    blm = job_modifiers_for("BLM")
    step_mult = step_multiplier_for(step_state=StepState.WALKING,
                                       job="BLM")
    chance = interrupt_chance(
        base_chance=0.05, gear_weight=50,
        job_interrupt_resist=blm.interrupt_resist,
        step_multiplier=step_mult,
    )
    # BLM walking penalty is 1.40, gear factor is 1.5, base 5% → 10.5%
    assert chance > 0.05
    # Compare to standing still: drops back to baseline-ish
    still_chance = interrupt_chance(
        base_chance=0.05, gear_weight=50,
        job_interrupt_resist=blm.interrupt_resist, step_multiplier=1.0,
    )
    assert still_chance < chance


def test_nin_sprinting_seal_cast_safe():
    """NIN sprinting while signing: full 1.00 step mult + 0.30 job resist."""
    nin = job_modifiers_for("NIN")
    step_mult = step_multiplier_for(step_state=StepState.RUNNING,
                                       job="NIN", is_signing=True)
    assert step_mult == 1.00
    chance = interrupt_chance(
        base_chance=0.05, gear_weight=15,
        job_interrupt_resist=nin.interrupt_resist,
        step_multiplier=step_mult,
    )
    # Very low interrupt risk
    assert chance < 0.02


def test_known_modifiers_table_complete():
    """Sanity: the doc lists ~14 reducers + ~7 increasers; verify the
    table at least has the canonical entries."""
    for required in ("haste_iii", "march_iii", "thf_flee",
                       "gravity", "slow_ii", "encumber_stack"):
        assert required in KNOWN_MODIFIERS
