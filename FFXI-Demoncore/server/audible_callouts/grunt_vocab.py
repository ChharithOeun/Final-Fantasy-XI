"""Universal grunt vocabulary — the involuntary voice the body emits.

Per AUDIBLE_CALLOUTS.md the grunt vocabulary is universal across
all actors (player + NPC + mob): on-swing exertion, on-hit pain,
on-low-hp gasping, on-death rattle, on-effort cast strain, on-relief
healing, on-frustration, on-skillchain-line.

These play even outside chatbox-callout events — they are the
constant audio backdrop of combat.
"""
from __future__ import annotations

import dataclasses
import enum


class GruntCategory(str, enum.Enum):
    EXERTION = "exertion"            # weapon swing, melee strike
    PAIN = "pain"                    # took a hit
    LOW_HP_GASP = "low_hp_gasp"      # broken / grievous stage
    DEATH_RATTLE = "death_rattle"    # dying
    CAST_STRAIN = "cast_strain"      # mid-cast vocalization
    RELIEF = "relief"                # heal landed
    FRUSTRATION = "frustration"      # interrupt, miss
    EFFORT = "effort"                # WS / TP burst


@dataclasses.dataclass(frozen=True)
class GruntEntry:
    category: GruntCategory
    label: str                       # human-readable
    audio_id: str                    # voice pipeline lookup id
    plays_during: tuple[str, ...]    # which event_kinds trigger this


GRUNT_VOCAB: dict[GruntCategory, GruntEntry] = {
    GruntCategory.EXERTION: GruntEntry(
        category=GruntCategory.EXERTION,
        label="exertion",
        audio_id="grunt_exertion",
        plays_during=("auto_attack_swing", "weapon_skill_open"),
    ),
    GruntCategory.PAIN: GruntEntry(
        category=GruntCategory.PAIN,
        label="pain",
        audio_id="grunt_pain",
        plays_during=("hp_decrease", "stage_change_down"),
    ),
    GruntCategory.LOW_HP_GASP: GruntEntry(
        category=GruntCategory.LOW_HP_GASP,
        label="low-hp gasp",
        audio_id="grunt_gasp_continuous",
        plays_during=("stage_broken", "stage_grievous"),
    ),
    GruntCategory.DEATH_RATTLE: GruntEntry(
        category=GruntCategory.DEATH_RATTLE,
        label="death rattle",
        audio_id="grunt_death",
        plays_during=("death",),
    ),
    GruntCategory.CAST_STRAIN: GruntEntry(
        category=GruntCategory.CAST_STRAIN,
        label="cast strain",
        audio_id="grunt_cast_strain",
        plays_during=("spell_cast_mid",),
    ),
    GruntCategory.RELIEF: GruntEntry(
        category=GruntCategory.RELIEF,
        label="relief",
        audio_id="grunt_relief",
        plays_during=("heal_received",),
    ),
    GruntCategory.FRUSTRATION: GruntEntry(
        category=GruntCategory.FRUSTRATION,
        label="frustration",
        audio_id="grunt_frustration",
        plays_during=("cast_interrupted", "ws_missed",
                        "intervention_failed"),
    ),
    GruntCategory.EFFORT: GruntEntry(
        category=GruntCategory.EFFORT,
        label="effort",
        audio_id="grunt_effort",
        plays_during=("two_hour_ability", "weapon_skill_close"),
    ),
}


# Reverse index: event_kind -> GruntCategory
def grunt_for_event(event_kind: str) -> GruntCategory | None:
    """Resolve which grunt category should fire for a given event."""
    for entry in GRUNT_VOCAB.values():
        if event_kind in entry.plays_during:
            return entry.category
    return None
