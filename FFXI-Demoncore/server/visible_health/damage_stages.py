"""DamageStage — the 7-stage entity HP grammar.

Per VISUAL_HEALTH_SYSTEM.md HP and MP bars are not visible by
default. Players read damage by posture, blood, limp, cough — the
way a soldier reads a battlefield.

Each entity has 7 visible damage stages mapped to HP bands. The
HP itself is server-side; the client renders the appropriate stage.

This module is for ENTITIES (humanoids, mobs, NPCs). The
structurally-similar but distinct grammar for STRUCTURES lives in
server.damage_physics — entities have 7 stages (pristine through
dead), structures have 5 (pristine through destroyed).
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DamageStage(str, enum.Enum):
    """The 7 stages from the doc table."""
    PRISTINE = "pristine"
    SCUFFED = "scuffed"
    BLOODIED = "bloodied"
    WOUNDED = "wounded"
    GRIEVOUS = "grievous"
    BROKEN = "broken"
    DEAD = "dead"


@dataclasses.dataclass(frozen=True)
class StageBand:
    """One row of the doc's HP-band table."""
    stage: DamageStage
    min_fraction: float            # inclusive lower bound (0.0..1.0)
    max_fraction: float            # exclusive upper bound (0.0..1.0)
    humanoid_cues: tuple[str, ...]
    mob_cues: tuple[str, ...]
    attack_speed_multiplier: float = 1.0   # mobs slow at lower stages
    audible_cue: str = ""


# Doc-exact band table. Note: 100-90 means HP_fraction in [0.90, 1.0],
# 90-70 means [0.70, 0.90), etc. We use closed-open intervals on the
# WAY DOWN: at 90% exactly the entity is still pristine.
STAGE_BANDS: tuple[StageBand, ...] = (
    StageBand(
        stage=DamageStage.PRISTINE,
        min_fraction=0.90, max_fraction=1.0001,
        humanoid_cues=(
            "clean armor", "full posture", "normal breathing",
        ),
        mob_cues=(
            "full color saturation", "alert posture",
        ),
        attack_speed_multiplier=1.0,
    ),
    StageBand(
        stage=DamageStage.SCUFFED,
        min_fraction=0.70, max_fraction=0.90,
        humanoid_cues=(
            "minor scratches", "dust on armor", "occasional wince",
        ),
        mob_cues=(
            "one fur patch matted", "ear flick",
        ),
        attack_speed_multiplier=1.0,
    ),
    StageBand(
        stage=DamageStage.BLOODIED,
        min_fraction=0.50, max_fraction=0.70,
        humanoid_cues=(
            "minor scratches", "dust on armor",
            "visible blood on armor", "slight limp on damaged side",
        ),
        mob_cues=(
            "favors one leg", "lower head",
        ),
        attack_speed_multiplier=0.95,
    ),
    StageBand(
        stage=DamageStage.WOUNDED,
        min_fraction=0.30, max_fraction=0.50,
        humanoid_cues=(
            "minor scratches", "visible blood on armor", "limp",
            "heavy blood", "slower attacks", "labored breathing",
        ),
        mob_cues=(
            "wing or tail droops", "slower charges",
        ),
        attack_speed_multiplier=0.85,
        audible_cue="labored_breathing",
    ),
    StageBand(
        stage=DamageStage.GRIEVOUS,
        min_fraction=0.10, max_fraction=0.30,
        humanoid_cues=(
            "heavy blood", "gash visible on body", "severe limp",
            "occasional stagger",
        ),
        mob_cues=(
            "half-collapsed posture", "weak roars",
        ),
        attack_speed_multiplier=0.75,
        audible_cue="weak_roar",
    ),
    StageBand(
        stage=DamageStage.BROKEN,
        min_fraction=0.0001, max_fraction=0.10,
        humanoid_cues=(
            "stumbling", "swaying", "weapon held loosely",
            "near-fall",
        ),
        mob_cues=(
            "crawling", "drag-walk", "shrill cries",
        ),
        attack_speed_multiplier=0.60,
        audible_cue="shrill_cry",
    ),
    StageBand(
        stage=DamageStage.DEAD,
        min_fraction=0.0, max_fraction=0.0001,
        humanoid_cues=(
            "death animation",
        ),
        mob_cues=(
            "death animation",
        ),
        attack_speed_multiplier=0.0,
    ),
)


# Stage -> band lookup.
STAGE_TO_BAND: dict[DamageStage, StageBand] = {b.stage: b for b in STAGE_BANDS}


def get_band(stage: DamageStage) -> StageBand:
    return STAGE_TO_BAND[stage]


def resolve_stage(hp_current: int, hp_max: int) -> DamageStage:
    """Map HP to a DamageStage. Doc-exact bands.

    Edge cases:
        - hp_current < 0      -> DEAD (clamped)
        - hp_max <= 0         -> DEAD (defensive)
        - hp_current > hp_max -> PRISTINE (capped)
    """
    if hp_max <= 0:
        return DamageStage.DEAD
    if hp_current <= 0:
        return DamageStage.DEAD
    fraction = min(1.0, hp_current / hp_max)
    for band in STAGE_BANDS:
        if band.stage == DamageStage.DEAD:
            continue
        if band.min_fraction <= fraction < band.max_fraction:
            return band.stage
    # Unreachable in practice — pristine catches the top
    return DamageStage.PRISTINE


def cues_for(stage: DamageStage, *, is_humanoid: bool = True
             ) -> tuple[str, ...]:
    """Return the visible cues a humanoid or mob shows at this stage."""
    band = get_band(stage)
    return band.humanoid_cues if is_humanoid else band.mob_cues


def attack_speed_multiplier(stage: DamageStage) -> float:
    return get_band(stage).attack_speed_multiplier


def audible_cue(stage: DamageStage) -> str:
    return get_band(stage).audible_cue


def stage_for_check_descriptor(stage: DamageStage) -> str:
    """Doc /check damage read. 'unharmed' / 'slightly hurt' / 'badly
    wounded'. Three-bucket folding of the 7 stages."""
    if stage in (DamageStage.PRISTINE, DamageStage.SCUFFED):
        return "unharmed"
    if stage in (DamageStage.BLOODIED, DamageStage.WOUNDED):
        return "slightly hurt"
    return "badly wounded"
