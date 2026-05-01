"""Per-mob-class visible-damage cue overrides.

Per VISUAL_HEALTH_SYSTEM.md the doc names 6 mob class overrides:
    Dragon NMs   wing droops on damaged side at WOUNDED; tip drags
                  ground at BROKEN; fire-breath windup visibly slower
    Slime/jelly  lose translucency progressively; fully opaque at
                  BROKEN; trail goo
    Goblin       limp + drop sack of stolen junk by GRIEVOUS
    Quadav       shield drops by WOUNDED; helmet falls off at BROKEN
    Yagudo       feathers fall progressively across stages
    Worm         segments visibly split apart from WOUNDED onward
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .damage_stages import DamageStage


class MobClass(str, enum.Enum):
    """Mob classes that have per-stage cue overrides."""
    DRAGON = "dragon"
    SLIME = "slime"
    GOBLIN = "goblin"
    QUADAV = "quadav"
    YAGUDO = "yagudo"
    WORM = "worm"


@dataclasses.dataclass(frozen=True)
class MobCueOverride:
    """Per-(mob_class, stage) override appended to the mob cues."""
    mob_class: MobClass
    stage: DamageStage
    extra_cues: tuple[str, ...]
    drop_decoration: t.Optional[str] = None   # 'shield' / 'helmet' /
                                                  # 'sack' visible drop
    geometry_change: t.Optional[str] = None   # 'wing_droop' / 'segment_split'
    translucency_multiplier: float = 1.0
    feathers_lost_count: int = 0
    cast_speed_multiplier: float = 1.0


MOB_CLASS_OVERRIDES: dict[MobClass, dict[DamageStage, MobCueOverride]] = {
    MobClass.DRAGON: {
        DamageStage.WOUNDED: MobCueOverride(
            mob_class=MobClass.DRAGON, stage=DamageStage.WOUNDED,
            extra_cues=("wing droops on damaged side",),
            geometry_change="wing_droop",
            cast_speed_multiplier=0.85,
        ),
        DamageStage.GRIEVOUS: MobCueOverride(
            mob_class=MobClass.DRAGON, stage=DamageStage.GRIEVOUS,
            extra_cues=("wing tip nears the ground",
                          "labored fire-breath windup"),
            geometry_change="wing_droop_low",
            cast_speed_multiplier=0.70,
        ),
        DamageStage.BROKEN: MobCueOverride(
            mob_class=MobClass.DRAGON, stage=DamageStage.BROKEN,
            extra_cues=("wing tip drags the ground",
                          "fire-breath stalls visibly"),
            geometry_change="wing_drag_ground",
            cast_speed_multiplier=0.55,
        ),
    },
    MobClass.SLIME: {
        DamageStage.SCUFFED: MobCueOverride(
            mob_class=MobClass.SLIME, stage=DamageStage.SCUFFED,
            extra_cues=("slight cloudiness",),
            translucency_multiplier=0.85,
        ),
        DamageStage.BLOODIED: MobCueOverride(
            mob_class=MobClass.SLIME, stage=DamageStage.BLOODIED,
            extra_cues=("noticeably opaque",),
            translucency_multiplier=0.65,
        ),
        DamageStage.WOUNDED: MobCueOverride(
            mob_class=MobClass.SLIME, stage=DamageStage.WOUNDED,
            extra_cues=("hard to see through",),
            translucency_multiplier=0.40,
        ),
        DamageStage.GRIEVOUS: MobCueOverride(
            mob_class=MobClass.SLIME, stage=DamageStage.GRIEVOUS,
            extra_cues=("nearly opaque",
                          "trails goo"),
            translucency_multiplier=0.20,
        ),
        DamageStage.BROKEN: MobCueOverride(
            mob_class=MobClass.SLIME, stage=DamageStage.BROKEN,
            extra_cues=("fully opaque",
                          "trails goo continuously"),
            translucency_multiplier=0.0,
        ),
    },
    MobClass.GOBLIN: {
        DamageStage.WOUNDED: MobCueOverride(
            mob_class=MobClass.GOBLIN, stage=DamageStage.WOUNDED,
            extra_cues=("pronounced limp",),
        ),
        DamageStage.GRIEVOUS: MobCueOverride(
            mob_class=MobClass.GOBLIN, stage=DamageStage.GRIEVOUS,
            extra_cues=("drops sack of stolen junk",),
            drop_decoration="goblin_sack",
        ),
        DamageStage.BROKEN: MobCueOverride(
            mob_class=MobClass.GOBLIN, stage=DamageStage.BROKEN,
            extra_cues=("severe limp", "no sack",),
        ),
    },
    MobClass.QUADAV: {
        DamageStage.WOUNDED: MobCueOverride(
            mob_class=MobClass.QUADAV, stage=DamageStage.WOUNDED,
            extra_cues=("shield drops",),
            drop_decoration="quadav_shield",
        ),
        DamageStage.GRIEVOUS: MobCueOverride(
            mob_class=MobClass.QUADAV, stage=DamageStage.GRIEVOUS,
            extra_cues=("helmet wobbles",),
        ),
        DamageStage.BROKEN: MobCueOverride(
            mob_class=MobClass.QUADAV, stage=DamageStage.BROKEN,
            extra_cues=("helmet falls off",),
            drop_decoration="quadav_helmet",
        ),
    },
    MobClass.YAGUDO: {
        DamageStage.SCUFFED: MobCueOverride(
            mob_class=MobClass.YAGUDO, stage=DamageStage.SCUFFED,
            extra_cues=("a few feathers fall",),
            feathers_lost_count=2,
        ),
        DamageStage.BLOODIED: MobCueOverride(
            mob_class=MobClass.YAGUDO, stage=DamageStage.BLOODIED,
            extra_cues=("more feathers fall",),
            feathers_lost_count=5,
        ),
        DamageStage.WOUNDED: MobCueOverride(
            mob_class=MobClass.YAGUDO, stage=DamageStage.WOUNDED,
            extra_cues=("clumps of feathers",),
            feathers_lost_count=10,
        ),
        DamageStage.GRIEVOUS: MobCueOverride(
            mob_class=MobClass.YAGUDO, stage=DamageStage.GRIEVOUS,
            extra_cues=("plumage thinning",),
            feathers_lost_count=18,
        ),
        DamageStage.BROKEN: MobCueOverride(
            mob_class=MobClass.YAGUDO, stage=DamageStage.BROKEN,
            extra_cues=("most feathers gone",),
            feathers_lost_count=28,
        ),
    },
    MobClass.WORM: {
        DamageStage.WOUNDED: MobCueOverride(
            mob_class=MobClass.WORM, stage=DamageStage.WOUNDED,
            extra_cues=("segments visibly split apart",),
            geometry_change="segment_split",
        ),
        DamageStage.GRIEVOUS: MobCueOverride(
            mob_class=MobClass.WORM, stage=DamageStage.GRIEVOUS,
            extra_cues=("segments dragging behind",),
            geometry_change="segment_drag",
        ),
        DamageStage.BROKEN: MobCueOverride(
            mob_class=MobClass.WORM, stage=DamageStage.BROKEN,
            extra_cues=("segments fully separated",),
            geometry_change="segment_separated",
        ),
    },
}


def get_override(mob_class: MobClass, stage: DamageStage
                  ) -> t.Optional[MobCueOverride]:
    return MOB_CLASS_OVERRIDES.get(mob_class, {}).get(stage)


def has_override(mob_class_id: str, stage: DamageStage) -> bool:
    """Convenience: does this mob class have ANY override for the
    given stage? Used by the BPC pipeline to know whether to look up
    the special-case render."""
    try:
        mc = MobClass(mob_class_id)
    except ValueError:
        return False
    return stage in MOB_CLASS_OVERRIDES.get(mc, {})
