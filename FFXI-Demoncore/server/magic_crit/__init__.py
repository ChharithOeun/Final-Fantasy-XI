"""Magic crit — critical hits for spells.

Parallel to physical crits in combat_outcomes. Magic spells can
land a CRIT applying a damage (or heal) multiplier. This module
resolves whether a magic crit fires and what multiplier to apply.

Inputs include the caster's stat (INT for damage, MND for heal),
gear-granted magic_crit_rate bonus, target Magic Defense Bonus
crits-resist, and the spell tier (higher tiers crit slightly less
often by default). Healing crits are a separate path: a Cure-V
that crits doubles. Different from physical crits because:

* Magic crit chance is lower baseline (5% vs 10% physical)
* Some spells CANNOT crit (status effects, summons, dispels)
* Some spells crit harder (Drain crit returns 2x HP to caster)

Public surface
--------------
    SpellKind enum (DAMAGE / HEAL / DRAIN / DISPEL_LIKE /
                     STATUS_LIKE / SUMMON_LIKE)
    MagicCritContext dataclass
    MagicCritOutcome dataclass
    resolve_magic_crit(context, rng) -> MagicCritOutcome
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


# Default base crit rate for damage spells (percentage points).
BASE_DAMAGE_CRIT_RATE_PCT = 5
BASE_HEAL_CRIT_RATE_PCT = 5
BASE_DRAIN_CRIT_RATE_PCT = 3

# Default crit multipliers.
DAMAGE_CRIT_MULTIPLIER = 1.5
HEAL_CRIT_MULTIPLIER = 2.0           # heroic heal moment
DRAIN_CRIT_MULTIPLIER = 2.0           # double drain return

# Crit-rate cap.
MAX_CRIT_RATE_PCT = 50


class SpellKind(str, enum.Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    DRAIN = "drain"
    DISPEL_LIKE = "dispel_like"
    STATUS_LIKE = "status_like"
    SUMMON_LIKE = "summon_like"


_CRITTABLE: frozenset[SpellKind] = frozenset({
    SpellKind.DAMAGE, SpellKind.HEAL, SpellKind.DRAIN,
})


@dataclasses.dataclass(frozen=True)
class MagicCritContext:
    spell_id: str
    spell_kind: SpellKind
    spell_tier: int = 1                  # 1..6 typically
    caster_stat_value: int = 0           # INT for damage; MND heal
    target_magic_defense_bonus: int = 0  # mob mdb (resists crits)
    gear_magic_crit_bonus_pct: int = 0   # +rate from gear
    is_burst: bool = False                # in magic burst window


@dataclasses.dataclass(frozen=True)
class MagicCritOutcome:
    crit: bool
    multiplier: float
    effective_rate_pct: int
    notes: str = ""


def _base_rate(kind: SpellKind) -> int:
    if kind == SpellKind.DAMAGE:
        return BASE_DAMAGE_CRIT_RATE_PCT
    if kind == SpellKind.HEAL:
        return BASE_HEAL_CRIT_RATE_PCT
    if kind == SpellKind.DRAIN:
        return BASE_DRAIN_CRIT_RATE_PCT
    return 0


def _crit_multiplier(kind: SpellKind) -> float:
    if kind == SpellKind.DAMAGE:
        return DAMAGE_CRIT_MULTIPLIER
    if kind == SpellKind.HEAL:
        return HEAL_CRIT_MULTIPLIER
    if kind == SpellKind.DRAIN:
        return DRAIN_CRIT_MULTIPLIER
    return 1.0


def resolve_magic_crit(
    *, context: MagicCritContext,
    rng: t.Optional[random.Random] = None,
) -> MagicCritOutcome:
    rng = rng or random.Random()
    if context.spell_kind not in _CRITTABLE:
        return MagicCritOutcome(
            crit=False, multiplier=1.0,
            effective_rate_pct=0,
            notes=(
                f"{context.spell_kind.value} cannot crit"
            ),
        )
    rate = _base_rate(context.spell_kind)
    rate += context.gear_magic_crit_bonus_pct
    # +1% per 10 caster stat above 50 (rough scaling)
    if context.caster_stat_value > 50:
        rate += (context.caster_stat_value - 50) // 10
    # Higher-tier spells crit slightly less reliably
    if context.spell_tier > 3:
        rate -= (context.spell_tier - 3) * 1
    # MDB on target reduces crit rate (each 5 MDB = -1%)
    rate -= context.target_magic_defense_bonus // 5
    # Magic-burst window adds +5%
    if context.is_burst:
        rate += 5
    rate = max(0, min(MAX_CRIT_RATE_PCT, rate))
    if rate == 0:
        return MagicCritOutcome(
            crit=False, multiplier=1.0,
            effective_rate_pct=0,
        )
    crit = rng.randint(1, 100) <= rate
    return MagicCritOutcome(
        crit=crit,
        multiplier=(
            _crit_multiplier(context.spell_kind) if crit else 1.0
        ),
        effective_rate_pct=rate,
    )


__all__ = [
    "BASE_DAMAGE_CRIT_RATE_PCT", "BASE_HEAL_CRIT_RATE_PCT",
    "BASE_DRAIN_CRIT_RATE_PCT",
    "DAMAGE_CRIT_MULTIPLIER", "HEAL_CRIT_MULTIPLIER",
    "DRAIN_CRIT_MULTIPLIER",
    "MAX_CRIT_RATE_PCT",
    "SpellKind",
    "MagicCritContext", "MagicCritOutcome",
    "resolve_magic_crit",
]
