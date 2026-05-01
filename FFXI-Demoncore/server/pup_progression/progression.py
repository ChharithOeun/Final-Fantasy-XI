"""PUP progression rules — slots, frames, attachments, capacity,
burden, damage.

Per the user direction:

  Slots (simultaneous active automatons):
    Aphmau              : 3 at any level (unique exception)
    Other PUPs base     : 1
    Other PUPs ML25     : 2  (gated by lvl-99 quest series + battlefield)
    Other PUPs ML50     : 3  (gated by separate quest series + battlefield)

  Frames:
    Standard (Valoredge / Sharpshot / Stormwaker / Soulsoother /
              Spiritreaver) : always available
    NIN frame  : lvl 75 fully-merit, head + body separate quests
    DRG frame  : hidden, lvl 99 + job mastered, secret quest
    BLU frame  : hidden, lvl 99 + job mastered, secret quest

  Attachment slots:
    Retail base 8 (FFXI cap). Demoncore adds +1 at lvl 80 / 85 / 90 / 95
    each gated behind a quest, for an apex of 12.

  Elemental capacity (per element):
    Additive bonus on top of whatever retail base the automaton already
    has from frames + attachments. +10 at lvl 99 / +10 at ML25 / +10 at
    ML50 — apex bonus of +30 (caller layers retail base separately).

  Maneuver burden:
    Reduced 70% from canonical FFXI; effective_burden = base * 0.30

  Automaton damage / cast / range / cure tuning:
    +25% global damage multiplier
    -50% cast time
    +15% cast range
    +25% cure potency
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# ----------------------------------------------------------------------
# Slots
# ----------------------------------------------------------------------

AUTOMATON_BASE_SLOTS = 1
APHMAU_SLOT_COUNT = 3      # unique; not gated by ML
ML25_THRESHOLD = 25
ML50_THRESHOLD = 50


@dataclasses.dataclass
class PupProgressionState:
    """Per-character PUP progression snapshot."""
    actor_id: str
    job: str = "PUP"
    job_level: int = 75
    master_level: int = 0
    is_aphmau: bool = False
    job_mastered: bool = False
    is_fully_merit: bool = False             # lvl 75 cap full merits
    # Quest/battlefield completion flags
    second_automaton_unlocked: bool = False
    third_automaton_unlocked: bool = False
    nin_head_unlocked: bool = False
    nin_frame_unlocked: bool = False
    drg_head_unlocked: bool = False
    drg_frame_unlocked: bool = False
    blu_head_unlocked: bool = False
    blu_frame_unlocked: bool = False
    attachment_slots_unlocked: set[int] = dataclasses.field(
        default_factory=set)            # lvl thresholds completed: {80, 85, 90, 95}


def automaton_slot_capacity(state: PupProgressionState) -> int:
    """Return the maximum simultaneous automatons this character can deploy.

    Aphmau is unique (3 at any level). All others: 1 base, 2 at ML25
    (gated quests), 3 at ML50 (gated quests).
    """
    if state.is_aphmau:
        return APHMAU_SLOT_COUNT
    if state.master_level >= ML50_THRESHOLD and state.third_automaton_unlocked:
        return 3
    if state.master_level >= ML25_THRESHOLD and state.second_automaton_unlocked:
        return 2
    return AUTOMATON_BASE_SLOTS


# ----------------------------------------------------------------------
# Frame unlocks
# ----------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class FrameUnlockRequirement:
    """Conditions for a PUP to use a frame."""
    frame_id: str
    head_quest_required: bool = False
    frame_quest_required: bool = False
    requires_lvl: int = 1
    requires_master_level: int = 0
    requires_full_merit: bool = False
    requires_job_mastered: bool = False
    is_hidden: bool = False
    notes: str = ""


# Default frames (always available to any PUP at appropriate lvl)
_STANDARD_FRAMES = {
    "automaton_valoredge", "automaton_sharpshot", "automaton_stormwaker",
    "automaton_soulsoother", "automaton_spiritreaver", "automaton_mnejing",
}


FRAME_UNLOCK_REQUIREMENTS: dict[str, FrameUnlockRequirement] = {
    "automaton_ninja": FrameUnlockRequirement(
        frame_id="automaton_ninja",
        head_quest_required=True, frame_quest_required=True,
        requires_lvl=75, requires_full_merit=True,
        notes="Lvl 75 fully-merit; head + frame are separate quests",
    ),
    "automaton_dragoon": FrameUnlockRequirement(
        frame_id="automaton_dragoon",
        head_quest_required=True, frame_quest_required=True,
        requires_lvl=99, requires_job_mastered=True, is_hidden=True,
        notes="hidden; lvl 99 + job mastered; difficult secret quest",
    ),
    "automaton_blue": FrameUnlockRequirement(
        frame_id="automaton_blue",
        head_quest_required=True, frame_quest_required=True,
        requires_lvl=99, requires_job_mastered=True, is_hidden=True,
        notes="hidden; lvl 99 + job mastered; difficult secret quest",
    ),
}


def can_use_frame(state: PupProgressionState, frame_id: str) -> bool:
    """Whether this PUP can deploy the given frame."""
    if frame_id in _STANDARD_FRAMES:
        return True

    req = FRAME_UNLOCK_REQUIREMENTS.get(frame_id)
    if req is None:
        return False

    if state.job_level < req.requires_lvl:
        return False
    if state.master_level < req.requires_master_level:
        return False
    if req.requires_full_merit and not state.is_fully_merit:
        return False
    if req.requires_job_mastered and not state.job_mastered:
        return False

    # Specific unlock flags per frame family
    if frame_id == "automaton_ninja":
        return state.nin_head_unlocked and state.nin_frame_unlocked
    if frame_id == "automaton_dragoon":
        return state.drg_head_unlocked and state.drg_frame_unlocked
    if frame_id == "automaton_blue":
        return state.blu_head_unlocked and state.blu_frame_unlocked

    return False


# ----------------------------------------------------------------------
# Attachment slots
# ----------------------------------------------------------------------

BASE_ATTACHMENT_SLOTS = 8                  # retail FFXI cap
ATTACHMENT_SLOT_LEVEL_GATES = (80, 85, 90, 95)
MAX_ATTACHMENT_SLOTS = BASE_ATTACHMENT_SLOTS + len(ATTACHMENT_SLOT_LEVEL_GATES)


def attachment_slot_capacity(state: PupProgressionState) -> int:
    """Retail-base 8 + number of level-gate quests completed (apex 12)."""
    unlocked = sum(1 for lvl in ATTACHMENT_SLOT_LEVEL_GATES
                     if lvl in state.attachment_slots_unlocked)
    return BASE_ATTACHMENT_SLOTS + unlocked


# ----------------------------------------------------------------------
# Elemental capacity (additive bonus on top of retail base)
# ----------------------------------------------------------------------

ELEMENTAL_CAPACITY_LVL99_BUMP = 10
ELEMENTAL_CAPACITY_ML25_BUMP = 10
ELEMENTAL_CAPACITY_ML50_BUMP = 10
MAX_ELEMENTAL_CAPACITY_BONUS = (ELEMENTAL_CAPACITY_LVL99_BUMP
                                  + ELEMENTAL_CAPACITY_ML25_BUMP
                                  + ELEMENTAL_CAPACITY_ML50_BUMP)


def additional_elemental_capacity(state: PupProgressionState) -> int:
    """Demoncore-only ADDITIVE elemental capacity bonus. Caller layers
    this on top of whatever retail base capacity the automaton has
    from its frame + attachments. Apex bonus is +30."""
    bonus = 0
    if state.job_level >= 99:
        bonus += ELEMENTAL_CAPACITY_LVL99_BUMP
    if state.master_level >= ML25_THRESHOLD:
        bonus += ELEMENTAL_CAPACITY_ML25_BUMP
    if state.master_level >= ML50_THRESHOLD:
        bonus += ELEMENTAL_CAPACITY_ML50_BUMP
    return bonus


def elemental_capacity_for(state: PupProgressionState,
                             *,
                             retail_base: int) -> int:
    """Total per-element capacity = retail_base + additional bonus.

    Caller passes the retail base from the automaton's current frame
    + attachment loadout; we layer the Demoncore-only bonus on top.
    """
    return retail_base + additional_elemental_capacity(state)


# ----------------------------------------------------------------------
# Maneuver burden
# ----------------------------------------------------------------------

MANEUVER_BURDEN_REDUCTION = 0.70    # 70% reduction
BURDEN_RETENTION = 1.0 - MANEUVER_BURDEN_REDUCTION   # 0.30


def effective_burden(base_burden: float) -> float:
    """Apply the global 70% maneuver-burden reduction."""
    return base_burden * BURDEN_RETENTION


# ----------------------------------------------------------------------
# Damage buff
# ----------------------------------------------------------------------

AUTOMATON_DAMAGE_BUFF = 0.25         # +25% global damage multiplier
DAMAGE_MULTIPLIER = 1.0 + AUTOMATON_DAMAGE_BUFF


def buffed_damage(base_damage: float) -> float:
    """Apply the +25% global automaton damage buff."""
    return base_damage * DAMAGE_MULTIPLIER


# ----------------------------------------------------------------------
# Automaton cast time / range / cure-potency tuning
# ----------------------------------------------------------------------

AUTOMATON_CAST_TIME_REDUCTION = 0.50         # -50%
AUTOMATON_CAST_RANGE_BONUS = 0.15            # +15%
AUTOMATON_CURE_POTENCY_BONUS = 0.25          # +25%

CAST_TIME_MULTIPLIER = 1.0 - AUTOMATON_CAST_TIME_REDUCTION   # 0.50
CAST_RANGE_MULTIPLIER = 1.0 + AUTOMATON_CAST_RANGE_BONUS     # 1.15
CURE_POTENCY_MULTIPLIER = 1.0 + AUTOMATON_CURE_POTENCY_BONUS  # 1.25


def reduced_cast_time(base_cast_time: float) -> float:
    """Apply the -50% automaton cast-time reduction. Instant casts
    (base 0) stay 0."""
    if base_cast_time <= 0:
        return 0.0
    return base_cast_time * CAST_TIME_MULTIPLIER


def extended_cast_range(base_range_cm: float) -> float:
    """Apply the +15% automaton cast-range bonus."""
    return base_range_cm * CAST_RANGE_MULTIPLIER


def boosted_cure(base_cure_amount: float) -> float:
    """Apply the +25% automaton cure-potency bonus."""
    return base_cure_amount * CURE_POTENCY_MULTIPLIER
