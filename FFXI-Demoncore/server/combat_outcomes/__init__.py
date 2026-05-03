"""Combat outcomes — per-attack hit/miss/crit/graze resolution.

Sitting between auto_attack/weapon_skills and damage_formula,
this module resolves what KIND of attack outcome happened. The
caller passes attacker + defender + weapon + angle + status; we
return an OutcomeResolution the damage stack consumes (and the
auto_attack/swing FSM uses to decide if a parry triggered a
counter, etc).

Resolution stack (priority order)
---------------------------------
For each incoming attack:
1) EVADE     — defender's evasion vs attacker's accuracy
2) PARRY     — defender's parry skill vs weapon (front-only)
3) BLOCK     — shield block (front-only) when shielded
4) COUNTER   — MNK/PUP counter chance after a missed/parried hit
5) MISS      — when no other outcome triggered & accuracy fails
6) GRAZE     — partial-damage glancing hit (low-roll path)
7) CRIT      — high-roll path, applies CRIT_MULTIPLIER
8) HIT       — clean hit, normal damage

Public surface
--------------
    AttackKind enum
    AttackAngle enum (FRONT / SIDE / REAR)
    OutcomeKind enum
    AttackContext dataclass — all the inputs
    OutcomeResolution dataclass — the result
    resolve_outcome(context, rng) -> OutcomeResolution
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


CRIT_MULTIPLIER = 2.0
GRAZE_MULTIPLIER = 0.5

# Hard floors / ceilings on outcome chances — keeps the
# resolution deterministic-ish even with absurd inputs.
HIT_RATE_MIN = 0.20
HIT_RATE_MAX = 0.95


class AttackKind(str, enum.Enum):
    MELEE = "melee"
    RANGED = "ranged"
    WEAPONSKILL = "weaponskill"


class AttackAngle(str, enum.Enum):
    FRONT = "front"
    SIDE = "side"
    REAR = "rear"


class OutcomeKind(str, enum.Enum):
    EVADE = "evade"
    PARRY = "parry"
    BLOCK = "block"
    COUNTER = "counter"
    MISS = "miss"
    GRAZE = "graze"
    CRIT = "crit"
    HIT = "hit"


@dataclasses.dataclass(frozen=True)
class AttackContext:
    """Everything the resolver needs."""
    attack_kind: AttackKind
    angle: AttackAngle = AttackAngle.FRONT
    # Stats — use whatever scale the caller likes; only ratios
    # matter for resolution.
    attacker_accuracy: int = 100
    defender_evasion: int = 100
    attacker_crit_rate_pct: int = 5      # 0..50
    defender_parry_rate_pct: int = 0     # 0..40
    defender_shielded: bool = False
    defender_block_rate_pct: int = 0     # 0..40 if shielded
    defender_counter_rate_pct: int = 0   # MNK/PUP only
    # Status modifiers
    attacker_blinded: bool = False
    defender_stunned: bool = False
    defender_sleeping: bool = False
    defender_petrified: bool = False
    # Special: WS attacks bypass parry/block entirely (canonical).
    bypass_defenses: bool = False


@dataclasses.dataclass(frozen=True)
class OutcomeResolution:
    outcome: OutcomeKind
    damage_multiplier: float            # to apply to base damage
    triggered_counter: bool = False
    notes: str = ""


def _hit_rate(
    *, attacker_accuracy: int, defender_evasion: int,
    attacker_blinded: bool,
) -> float:
    if defender_evasion <= 0:
        rate = 1.0
    else:
        # Canonical-ish FFXI formula: 0.75 + 0.5 * (acc/eva - 1)
        ratio = attacker_accuracy / defender_evasion
        rate = 0.75 + 0.5 * (ratio - 1.0)
    if attacker_blinded:
        rate *= 0.5
    return max(HIT_RATE_MIN, min(HIT_RATE_MAX, rate))


def _stunned_or_sleeping(ctx: AttackContext) -> bool:
    return (
        ctx.defender_stunned
        or ctx.defender_sleeping
        or ctx.defender_petrified
    )


def _can_parry(ctx: AttackContext) -> bool:
    if ctx.bypass_defenses or _stunned_or_sleeping(ctx):
        return False
    if ctx.angle != AttackAngle.FRONT:
        return False
    if ctx.attack_kind == AttackKind.RANGED:
        return False
    return ctx.defender_parry_rate_pct > 0


def _can_block(ctx: AttackContext) -> bool:
    if ctx.bypass_defenses or _stunned_or_sleeping(ctx):
        return False
    if ctx.angle != AttackAngle.FRONT:
        return False
    return (
        ctx.defender_shielded
        and ctx.defender_block_rate_pct > 0
    )


def _can_counter(ctx: AttackContext) -> bool:
    if _stunned_or_sleeping(ctx):
        return False
    if ctx.attack_kind == AttackKind.RANGED:
        return False
    return ctx.defender_counter_rate_pct > 0


def resolve_outcome(
    *, context: AttackContext,
    rng: t.Optional[random.Random] = None,
) -> OutcomeResolution:
    """Resolve a single incoming attack into an OutcomeResolution."""
    rng = rng or random.Random()
    # Sleeping / petrified targets always crit (canonical).
    if context.defender_sleeping or context.defender_petrified:
        return OutcomeResolution(
            outcome=OutcomeKind.CRIT,
            damage_multiplier=CRIT_MULTIPLIER,
            notes=(
                "defender vulnerable -> auto-crit"
            ),
        )
    # 1) Evade — only if NOT stunned (stun blocks evade)
    if not context.defender_stunned:
        hit_rate = _hit_rate(
            attacker_accuracy=context.attacker_accuracy,
            defender_evasion=context.defender_evasion,
            attacker_blinded=context.attacker_blinded,
        )
        if rng.random() > hit_rate:
            return OutcomeResolution(
                outcome=OutcomeKind.EVADE,
                damage_multiplier=0.0,
                notes="defender evaded",
            )
    # 2) Parry
    if _can_parry(context):
        if rng.random() < (context.defender_parry_rate_pct / 100):
            # 3) Counter chance after parry
            if _can_counter(context) and rng.random() < (
                context.defender_counter_rate_pct / 100
            ):
                return OutcomeResolution(
                    outcome=OutcomeKind.COUNTER,
                    damage_multiplier=0.0,
                    triggered_counter=True,
                    notes="parried + countered",
                )
            return OutcomeResolution(
                outcome=OutcomeKind.PARRY,
                damage_multiplier=0.0,
                notes="defender parried",
            )
    # 4) Block (with shield)
    if _can_block(context):
        if rng.random() < (context.defender_block_rate_pct / 100):
            return OutcomeResolution(
                outcome=OutcomeKind.BLOCK,
                damage_multiplier=0.25,    # shields don't void
                notes="defender blocked with shield",
            )
    # 5) Counter without parry — MNK/PUP signature
    if _can_counter(context):
        # Counter chance fires on a CLEAN attack (not just parries)
        if rng.random() < (
            context.defender_counter_rate_pct / 100 * 0.5
        ):
            return OutcomeResolution(
                outcome=OutcomeKind.COUNTER,
                damage_multiplier=0.0,
                triggered_counter=True,
                notes="defender countered",
            )
    # 6) Crit roll — clamp 0..50
    crit_pct = max(0, min(50, context.attacker_crit_rate_pct))
    if rng.random() < (crit_pct / 100):
        return OutcomeResolution(
            outcome=OutcomeKind.CRIT,
            damage_multiplier=CRIT_MULTIPLIER,
            notes="critical hit",
        )
    # 7) Graze — 10% of the time, a low-roll glancing blow.
    #    Models the "barely connected" hit retail uses for
    #    near-miss frames. Not a graze for ranged WS.
    if (
        context.attack_kind != AttackKind.WEAPONSKILL
        and rng.random() < 0.10
    ):
        return OutcomeResolution(
            outcome=OutcomeKind.GRAZE,
            damage_multiplier=GRAZE_MULTIPLIER,
            notes="glancing blow",
        )
    # 8) Clean hit
    return OutcomeResolution(
        outcome=OutcomeKind.HIT,
        damage_multiplier=1.0,
        notes="clean hit",
    )


__all__ = [
    "CRIT_MULTIPLIER", "GRAZE_MULTIPLIER",
    "HIT_RATE_MIN", "HIT_RATE_MAX",
    "AttackKind", "AttackAngle", "OutcomeKind",
    "AttackContext", "OutcomeResolution",
    "resolve_outcome",
]
