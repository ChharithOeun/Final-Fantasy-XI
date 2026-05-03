"""Positional damage — back/flank/front attack modifiers.

Extends combat_outcomes by computing the damage MULTIPLIER for
attacks based on the attack angle. Side hits roll a touch
better than head-on; rear hits dramatically better; THF/NIN
sneak-attack from the rear lands disproportionately so. Some
mob defensive postures REDUCE rear damage (a turtle in shell)
or make front damage worse than usual (FRONT_ARMOR plate).

Public surface
--------------
    PositionalProfile dataclass — per-target armor profile
    SneakAttackContext dataclass — the bonus inputs
    PositionalResult dataclass — the resolved multiplier
    positional_multiplier(angle, attacker_job, profile,
                           sneak_ctx)
        -> PositionalResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.combat_outcomes import AttackAngle


# Base positional multipliers (no defensive profile).
_BASE_BY_ANGLE: dict[AttackAngle, float] = {
    AttackAngle.FRONT: 1.0,
    AttackAngle.SIDE: 1.10,
    AttackAngle.REAR: 1.25,
}


# Sneak Attack / Trick Attack tiers.
SA_REAR_BONUS = 1.5         # multiplicative on top of rear bonus
SA_SIDE_BONUS = 1.0         # SA only fires from rear (no side)
SA_FRONT_BONUS = 1.0


class JobAffinity(str, enum.Enum):
    """Job-specific positional bonuses."""
    GENERIC = "generic"
    THIEF = "thief"
    NINJA = "ninja"
    DRAGOON = "dragoon"   # Jump from front face is potent
    DANCER = "dancer"


@dataclasses.dataclass(frozen=True)
class PositionalProfile:
    """Per-target armor profile."""
    target_id: str
    front_armor: float = 1.0       # 1.0 = neutral; 1.2 = 20%
                                    # less damage taken from front
    rear_vulnerable: float = 1.0    # 1.0 = neutral; 0.8 = 20%
                                    # extra damage from rear
    side_armor: float = 1.0
    immune_to_sneak: bool = False  # bosses sometimes immune


@dataclasses.dataclass(frozen=True)
class SneakAttackContext:
    has_sneak_attack: bool = False
    has_trick_attack: bool = False
    bonus_dex: int = 0          # extra DEX scaling for SA


@dataclasses.dataclass(frozen=True)
class PositionalResult:
    angle: AttackAngle
    base_multiplier: float
    armor_multiplier: float
    sneak_multiplier: float
    final_multiplier: float
    notes: str = ""


def _sneak_for_angle(
    *, angle: AttackAngle,
    sneak_ctx: SneakAttackContext,
    profile: PositionalProfile,
) -> float:
    if profile.immune_to_sneak:
        return 1.0
    if not (
        sneak_ctx.has_sneak_attack
        or sneak_ctx.has_trick_attack
    ):
        return 1.0
    if angle == AttackAngle.REAR:
        # SA is the rear-only big bonus
        if sneak_ctx.has_sneak_attack:
            bonus = SA_REAR_BONUS
            if sneak_ctx.bonus_dex > 0:
                # +0.05x per 10 DEX
                bonus += (sneak_ctx.bonus_dex // 10) * 0.05
            return bonus
        # TA from rear is small
        return 1.10
    if angle == AttackAngle.SIDE:
        # TA from side / behind ally lands modest bonus
        if sneak_ctx.has_trick_attack:
            return 1.20
    return 1.0


def positional_multiplier(
    *, angle: AttackAngle,
    attacker_job: JobAffinity = JobAffinity.GENERIC,
    profile: t.Optional[PositionalProfile] = None,
    sneak_ctx: t.Optional[SneakAttackContext] = None,
) -> PositionalResult:
    if profile is None:
        profile = PositionalProfile(target_id="generic")
    if sneak_ctx is None:
        sneak_ctx = SneakAttackContext()
    base = _BASE_BY_ANGLE[angle]
    # Armor profile divides damage from the corresponding face
    armor_mult = 1.0
    if angle == AttackAngle.FRONT:
        armor_mult = 1.0 / max(0.1, profile.front_armor)
    elif angle == AttackAngle.SIDE:
        armor_mult = 1.0 / max(0.1, profile.side_armor)
    elif angle == AttackAngle.REAR:
        # rear_vulnerable is a DAMAGE-AMPLIFIER (>1 = amped)
        # but we keep semantics: rear_vulnerable < 1 means
        # "still armored from rear", >1 means "soft from rear"
        armor_mult = 1.0 / max(0.1, profile.rear_vulnerable)
    sneak_mult = _sneak_for_angle(
        angle=angle, sneak_ctx=sneak_ctx, profile=profile,
    )
    # Job affinity flat bonuses
    job_mult = 1.0
    if attacker_job == JobAffinity.THIEF and angle == AttackAngle.REAR:
        job_mult = 1.10
    if attacker_job == JobAffinity.NINJA and angle == AttackAngle.SIDE:
        job_mult = 1.05
    if attacker_job == JobAffinity.DRAGOON and angle == AttackAngle.FRONT:
        job_mult = 1.05
    final = base * armor_mult * sneak_mult * job_mult
    return PositionalResult(
        angle=angle,
        base_multiplier=base,
        armor_multiplier=armor_mult,
        sneak_multiplier=sneak_mult,
        final_multiplier=round(final, 4),
    )


__all__ = [
    "JobAffinity",
    "PositionalProfile", "SneakAttackContext",
    "PositionalResult",
    "positional_multiplier",
    "SA_REAR_BONUS",
]
