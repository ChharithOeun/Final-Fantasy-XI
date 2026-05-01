"""The 5 weight-driven formulas.

Pure-function math; deterministic; no random. Caller layers RNG on
top (e.g. the interrupt_chance is a probability that the caller
rolls against).

Per WEIGHT_PHYSICS.md:

1. speed_multiplier(W) = clamp(1.0 - 0.005 * (W - 30), 0.4, 1.2)
2. attack_delay_multiplier(weapon_w) = 1.0 + 0.003 * (weapon_w - 5)
3. cast_time(base, gear_w, fc, stationary, job_mod) =
       base * (1.0 + 0.004 * (gear_w - 30))
            * (1.0 - fc)
            * (0.85 if stationary else 1.0)
            * job_mod
4. accuracy_bonus(weapon_w, attacker_still, target_still) =
       weapon_w * 0.5 * (attacker_still + target_still)
5. interrupt_chance(base, gear_w, job_resist, step_mult) =
       base * (1.0 + 0.01 * gear_w) * job_resist * step_mult
"""
from __future__ import annotations

import enum

# ----------------------------------------------------------------------
# Tuning constants
# ----------------------------------------------------------------------

SPEED_BASELINE_WEIGHT = 30.0
SPEED_PER_POINT_PENALTY = 0.005
SPEED_MIN_MULTIPLIER = 0.4
SPEED_MAX_MULTIPLIER = 1.2

ATTACK_DELAY_BASELINE_WEAPON_WEIGHT = 5.0
ATTACK_DELAY_PER_POINT = 0.003

CAST_TIME_BASELINE_GEAR_WEIGHT = 30.0
CAST_TIME_PER_POINT = 0.004
CAST_TIME_STATIONARY_MULTIPLIER = 0.85

INTERRUPT_PER_GEAR_WEIGHT = 0.01

# Step-state multipliers for interrupt_chance.
# NIN signing ignores movement entirely (silent kinesthetic casting).
STEP_MULTIPLIERS = {
    # (state_name, is_rdm_chainspell, is_nin_signing, is_walk_cast_job)
    # → multiplier
    "still": 1.00,
    "one_step": 1.00,
    # walking thresholds
    "walking_walk_cast_job": 1.10,        # RDM/BRD walking
    "walking_other": 1.40,
    # running thresholds
    "running_other": 1.80,
    "running_chainspell": 1.10,
    "running_nin_signing": 1.00,
    "any_speed_nin_signing": 1.00,
}


class StepState(str, enum.Enum):
    """The kinematic state during a cast.

    The interrupt formula reads this to pick a step multiplier."""
    STILL = "still"
    ONE_STEP = "one_step"          # the universal free step
    WALKING = "walking"
    RUNNING = "running"


# ----------------------------------------------------------------------
# Formula 1: Movement speed multiplier
# ----------------------------------------------------------------------

def speed_multiplier(weight: float) -> float:
    """Movement speed multiplier as a function of effective weight.

    < W=30: small bonus (capped at 1.2)
    = W=30: 1.0 (baseline)
    > W=30: each additional point shaves 0.5%, floored at 0.4
    """
    raw = 1.0 - SPEED_PER_POINT_PENALTY * (weight - SPEED_BASELINE_WEIGHT)
    return max(SPEED_MIN_MULTIPLIER, min(SPEED_MAX_MULTIPLIER, raw))


# ----------------------------------------------------------------------
# Formula 2: Attack delay multiplier
# ----------------------------------------------------------------------

def attack_delay_multiplier(weapon_weight: float) -> float:
    """Per-weapon swing delay multiplier.

    Baseline weapon weight = 5; lighter weapons swing faster, heavier
    swing slower. No clamp (a wooden staff swings nearly instant; a
    Spharai is +9.6%)."""
    return 1.0 + ATTACK_DELAY_PER_POINT * (weapon_weight - ATTACK_DELAY_BASELINE_WEAPON_WEIGHT)


# ----------------------------------------------------------------------
# Formula 3: Cast time
# ----------------------------------------------------------------------

def cast_time(*,
               base_cast_time: float,
               gear_weight: float,
               fast_cast_mult: float = 0.0,
               stationary: bool = True,
               job_modifier: float = 1.0) -> float:
    """Effective cast time after weight + Fast Cast + stillness + job.

    Instant-cast spells (base_cast_time = 0) are NOT affected by
    weight — Quick Magic, Mythic Cape Procs, Magic Burst short-circuit
    cuts, Chainspell while Stoneskin is up. Pass base_cast_time=0 and
    you get 0 back.

    fast_cast_mult is applied as a percentage off (0.30 = 30% faster).
    Caller is responsible for capping fast_cast_mult sensibly (FFXI
    canonically caps Fast Cast at 80%).
    """
    if base_cast_time <= 0:
        return 0.0

    weight_factor = 1.0 + CAST_TIME_PER_POINT * (gear_weight - CAST_TIME_BASELINE_GEAR_WEIGHT)
    fc_factor = 1.0 - fast_cast_mult
    stationary_factor = (CAST_TIME_STATIONARY_MULTIPLIER
                          if stationary else 1.0)

    result = base_cast_time * weight_factor * fc_factor * stationary_factor * job_modifier
    return max(0.0, result)


# ----------------------------------------------------------------------
# Formula 4: Accuracy bonus
# ----------------------------------------------------------------------

def accuracy_bonus(*,
                    weapon_weight: float,
                    attacker_still: bool,
                    target_still: bool) -> float:
    """Stillness rewards.

    If you didn't move during the swing's wind-up: +weapon_w*0.5
    If target didn't move during your wind-up: +weapon_w*0.5
    Both still: +weapon_w (full bonus)
    """
    half = weapon_weight * 0.5
    bonus = 0.0
    if attacker_still:
        bonus += half
    if target_still:
        bonus += half
    return bonus


# ----------------------------------------------------------------------
# Formula 5: Interrupt chance
# ----------------------------------------------------------------------

def interrupt_chance(*,
                      base_chance: float,
                      gear_weight: float,
                      job_interrupt_resist: float,
                      step_multiplier: float) -> float:
    """Effective interrupt probability.

    base_chance: 0..1 baseline (e.g. 0.05 for 5% baseline)
    gear_weight: heavier = more obtrusive = more interruptible
    job_interrupt_resist: 0.30 (NIN) to 1.00 (BLM)
    step_multiplier: from step_multiplier_for() based on movement
    """
    raw = (base_chance
            * (1.0 + INTERRUPT_PER_GEAR_WEIGHT * gear_weight)
            * job_interrupt_resist
            * step_multiplier)
    return max(0.0, min(1.0, raw))


def step_multiplier_for(*,
                         step_state: StepState,
                         job: str,
                         is_chainspell_active: bool = False,
                         is_signing: bool = False) -> float:
    """Resolve the right step multiplier for the given context.

    NIN signing always ignores movement (1.00).
    RDM Chainspell + running is 1.10.
    RDM/BRD can walk-cast at 1.10.
    All other jobs: walking 1.40, running 1.80.
    Standing still or one free step: 1.00 for everyone.
    """
    if is_signing:
        return 1.00
    if step_state in (StepState.STILL, StepState.ONE_STEP):
        return 1.00

    walk_cast_jobs = {"RDM", "BRD"}
    if step_state == StepState.WALKING:
        if job in walk_cast_jobs:
            return 1.10
        return 1.40
    # RUNNING
    if step_state == StepState.RUNNING:
        if job == "RDM" and is_chainspell_active:
            return 1.10
        return 1.80

    return 1.00
