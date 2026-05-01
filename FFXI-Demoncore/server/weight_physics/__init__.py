"""Weight physics engine — the physical-truth pillar of Demoncore combat.

Per WEIGHT_PHYSICS.md: every piece of equipment has weight; weight
drives movement speed, attack delay, cast time, accuracy, and spell
interrupt chance. One legible number replaces FFXI's stat-soup of
Haste / Move Speed / Snapshot / Fast Cast / Refresh.

This module owns:
    - The 5 weight-driven formulas (formulas.py)
    - Buff/debuff stacking that adjusts EFFECTIVE weight (buffs.py)
    - Per-job profiles (job_profiles.py): weight band targets +
      interrupt-resist + casting modifiers

Public surface:
    speed_multiplier(weight)
    attack_delay_multiplier(weapon_weight)
    cast_time(base_cast_time, gear_weight, fast_cast_mult, stationary,
              job_modifier)
    accuracy_bonus(weapon_weight, attacker_still, target_still)
    interrupt_chance(base_chance, gear_weight, job, step_state)
    StepState (enum)
    WeightModifier, WeightModifierStack, KNOWN_MODIFIERS
    JobProfile, JOB_PROFILES, job_modifiers_for(job)
"""
from .buffs import (
    KNOWN_MODIFIERS,
    WeightModifier,
    WeightModifierStack,
)
from .formulas import (
    SPEED_MAX_MULTIPLIER,
    SPEED_MIN_MULTIPLIER,
    StepState,
    accuracy_bonus,
    attack_delay_multiplier,
    cast_time,
    interrupt_chance,
    speed_multiplier,
)
from .job_profiles import (
    JOB_PROFILES,
    JobProfile,
    job_modifiers_for,
)

__all__ = [
    # Formulas
    "speed_multiplier",
    "attack_delay_multiplier",
    "cast_time",
    "accuracy_bonus",
    "interrupt_chance",
    "StepState",
    "SPEED_MIN_MULTIPLIER",
    "SPEED_MAX_MULTIPLIER",
    # Buffs
    "WeightModifier",
    "WeightModifierStack",
    "KNOWN_MODIFIERS",
    # Jobs
    "JobProfile",
    "JOB_PROFILES",
    "job_modifiers_for",
]
