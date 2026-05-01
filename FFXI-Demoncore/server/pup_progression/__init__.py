"""PUP progression — slot/frame/attachment/capacity/burden/damage rules.

The user loves the PUP job; this module is the rules engine for
every PUP-specific progression axis Demoncore adds:

    Automaton slots (1 base / 2 at ML25 / 3 at ML50; Aphmau = 3 always)
    Frame unlocks (NIN at lvl 75 fully-merit, DRG/BLU hidden at ML)
    Attachment slots (base + lvl 80/85/90/95 quest gates)
    Elemental capacity (+10 at lvl 99, +10 at ML25, +10 at ML50)
    Maneuver burden (-70% global reduction)
    Damage multiplier (+25% on all automaton output)
    H2H dual-wield (PUP/MNK/WAR need both hands)

Public surface:
    AUTOMATON_BASE_SLOTS, automaton_slot_capacity(state)
    PupProgressionState
    FRAME_UNLOCK_REQUIREMENTS, can_use_frame(state, frame)
    BASE_ATTACHMENT_SLOTS, ATTACHMENT_SLOT_LEVEL_GATES
    base_elemental_capacity, elemental_capacity_for(state)
    MANEUVER_BURDEN_REDUCTION, effective_burden(base)
    AUTOMATON_DAMAGE_BUFF, buffed_damage(base)
    h2h_requires_dual_wield(job, weapon_class)
"""
from .h2h_dual_wield import (
    H2H_DUAL_WIELD_JOBS,
    H2H_WEAPON_CLASSES,
    h2h_requires_dual_wield,
    is_dual_wield_complete,
)
from .progression import (
    APHMAU_SLOT_COUNT,
    AUTOMATON_BASE_SLOTS,
    AUTOMATON_CAST_RANGE_BONUS,
    AUTOMATON_CAST_TIME_REDUCTION,
    AUTOMATON_CURE_POTENCY_BONUS,
    AUTOMATON_DAMAGE_BUFF,
    BASE_ATTACHMENT_SLOTS,
    ATTACHMENT_SLOT_LEVEL_GATES,
    ELEMENTAL_CAPACITY_LVL99_BUMP,
    ELEMENTAL_CAPACITY_ML25_BUMP,
    ELEMENTAL_CAPACITY_ML50_BUMP,
    FRAME_UNLOCK_REQUIREMENTS,
    FrameUnlockRequirement,
    MANEUVER_BURDEN_REDUCTION,
    MAX_ATTACHMENT_SLOTS,
    MAX_ELEMENTAL_CAPACITY_BONUS,
    PupProgressionState,
    additional_elemental_capacity,
    attachment_slot_capacity,
    automaton_slot_capacity,
    boosted_cure,
    buffed_damage,
    can_use_frame,
    effective_burden,
    elemental_capacity_for,
    extended_cast_range,
    reduced_cast_time,
)

__all__ = [
    # Slots
    "AUTOMATON_BASE_SLOTS",
    "APHMAU_SLOT_COUNT",
    "PupProgressionState",
    "automaton_slot_capacity",
    # Frames
    "FRAME_UNLOCK_REQUIREMENTS",
    "FrameUnlockRequirement",
    "can_use_frame",
    # Attachments (retail base 8 + 4 progression unlocks)
    "BASE_ATTACHMENT_SLOTS",
    "MAX_ATTACHMENT_SLOTS",
    "ATTACHMENT_SLOT_LEVEL_GATES",
    "attachment_slot_capacity",
    # Elemental capacity (Demoncore-only ADDITIVE bonus)
    "ELEMENTAL_CAPACITY_LVL99_BUMP",
    "ELEMENTAL_CAPACITY_ML25_BUMP",
    "ELEMENTAL_CAPACITY_ML50_BUMP",
    "MAX_ELEMENTAL_CAPACITY_BONUS",
    "additional_elemental_capacity",
    "elemental_capacity_for",
    # Burden
    "MANEUVER_BURDEN_REDUCTION",
    "effective_burden",
    # Damage
    "AUTOMATON_DAMAGE_BUFF",
    "buffed_damage",
    # New tuning: cast time / range / cure potency
    "AUTOMATON_CAST_TIME_REDUCTION",
    "AUTOMATON_CAST_RANGE_BONUS",
    "AUTOMATON_CURE_POTENCY_BONUS",
    "reduced_cast_time",
    "extended_cast_range",
    "boosted_cure",
    # H2H dual wield
    "H2H_DUAL_WIELD_JOBS",
    "H2H_WEAPON_CLASSES",
    "h2h_requires_dual_wield",
    "is_dual_wield_complete",
]
