"""Layer 3: phases mapped to visible-health stages.

Per BOSS_GRAMMAR.md the 6 phases align directly with VISUAL_HEALTH:
    Pristine -> Scuffed -> Bloodied -> Wounded -> Grievous -> Broken
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BossPhase(str, enum.Enum):
    PRISTINE = "pristine"
    SCUFFED = "scuffed"
    BLOODIED = "bloodied"
    WOUNDED = "wounded"
    GRIEVOUS = "grievous"
    BROKEN = "broken"


BOSS_PHASE_ORDER: tuple[BossPhase, ...] = tuple(BossPhase)


@dataclasses.dataclass(frozen=True)
class PhaseRule:
    """Per-phase behavior shifts."""
    phase: BossPhase
    hp_band_min: float            # inclusive lower
    hp_band_max: float            # exclusive upper
    posture_change: str
    repertoire_unlocks: tuple[str, ...]
    castspeed_multiplier: float
    extra_aoe_per_minute: float
    is_panic: bool = False
    is_enraged: bool = False
    drops_armor_piece: t.Optional[str] = None


PHASE_RULES: dict[BossPhase, PhaseRule] = {
    BossPhase.PRISTINE: PhaseRule(
        phase=BossPhase.PRISTINE,
        hp_band_min=0.90, hp_band_max=1.0001,
        posture_change="standard repertoire; all attacks available",
        repertoire_unlocks=(),
        castspeed_multiplier=1.0,
        extra_aoe_per_minute=0.0,
    ),
    BossPhase.SCUFFED: PhaseRule(
        phase=BossPhase.SCUFFED,
        hp_band_min=0.70, hp_band_max=0.90,
        posture_change="opens with signature buff; faster wind-ups",
        repertoire_unlocks=("hassou_stance",),
        castspeed_multiplier=1.10,
        extra_aoe_per_minute=1.0,
    ),
    BossPhase.BLOODIED: PhaseRule(
        phase=BossPhase.BLOODIED,
        hp_band_min=0.50, hp_band_max=0.70,
        posture_change="drops one armor piece visibly; mood furious",
        repertoire_unlocks=("ultimate_extra_1", "ultimate_extra_2"),
        castspeed_multiplier=1.20,
        extra_aoe_per_minute=2.0,
        drops_armor_piece="helmet",
    ),
    BossPhase.WOUNDED: PhaseRule(
        phase=BossPhase.WOUNDED,
        hp_band_min=0.30, hp_band_max=0.50,
        posture_change="enrages; visible wound + breath rasp gets louder",
        repertoire_unlocks=(),
        castspeed_multiplier=1.30,
        extra_aoe_per_minute=3.0,
        is_enraged=True,
    ),
    BossPhase.GRIEVOUS: PhaseRule(
        phase=BossPhase.GRIEVOUS,
        hp_band_min=0.10, hp_band_max=0.30,
        posture_change="panic moves; arena-wide AOE every 5 seconds",
        repertoire_unlocks=("desperate_arena_aoe",),
        castspeed_multiplier=1.40,
        extra_aoe_per_minute=12.0,    # one every 5s == 12/min
        is_panic=True,
    ),
    BossPhase.BROKEN: PhaseRule(
        phase=BossPhase.BROKEN,
        hp_band_min=0.0001, hp_band_max=0.10,
        posture_change="stumbling, swaying; some kneel, others Berserker",
        repertoire_unlocks=("final_berserker",),
        castspeed_multiplier=1.50,
        extra_aoe_per_minute=4.0,
    ),
}


@dataclasses.dataclass(frozen=True)
class PhaseTransitionEvent:
    boss_id: str
    from_phase: BossPhase
    to_phase: BossPhase
    at_time: float


def phase_for_hp_fraction(fraction: float) -> BossPhase:
    """Map HP fraction in [0..1] to a BossPhase."""
    if fraction <= 0:
        return BossPhase.BROKEN
    if fraction >= 0.90:
        return BossPhase.PRISTINE
    if fraction >= 0.70:
        return BossPhase.SCUFFED
    if fraction >= 0.50:
        return BossPhase.BLOODIED
    if fraction >= 0.30:
        return BossPhase.WOUNDED
    if fraction >= 0.10:
        return BossPhase.GRIEVOUS
    return BossPhase.BROKEN


def get_rule(phase: BossPhase) -> PhaseRule:
    return PHASE_RULES[phase]
