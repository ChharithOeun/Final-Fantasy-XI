"""Augment engine — random stat rolls on items.

Magian Trials, Reisenjima drops, and Empyreal upgrades all add 1-N
"random" augments per item. Each pool defines a weighted catalog
of (stat, value) entries; rolling pulls without replacement so a
single augment slot doesn't repeat. rng_pool integration keeps the
rolls deterministic and replayable.

Public surface
--------------
    AugmentStat enum (canonical FFXI stat tokens)
    AugmentEntry: stat, value, weight
    AugmentPool: id, label, entries, max_per_roll
    Augment: result of one slot's roll
    AUGMENT_POOLS sample catalog
    roll_augments(pool, rng_pool, count)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_LOOT_DROPS


class AugmentStat(str, enum.Enum):
    STR = "str"
    DEX = "dex"
    VIT = "vit"
    AGI = "agi"
    INT = "int"
    MND = "mnd"
    CHR = "chr"
    HP = "hp"
    MP = "mp"
    ATTACK = "attack"
    ACCURACY = "accuracy"
    MAGIC_ATTACK = "magic_attack"
    MAGIC_ACCURACY = "magic_accuracy"
    HASTE = "haste"
    DOUBLE_ATTACK = "double_attack"
    CRIT_RATE = "crit_rate"
    REGEN = "regen"
    REFRESH = "refresh"


@dataclasses.dataclass(frozen=True)
class AugmentEntry:
    stat: AugmentStat
    value: int           # how much of the stat
    weight: int          # relative odds of being selected


@dataclasses.dataclass(frozen=True)
class AugmentPool:
    pool_id: str
    label: str
    entries: tuple[AugmentEntry, ...]
    max_per_roll: int    # limit of augments per item

    def total_weight(self) -> int:
        return sum(e.weight for e in self.entries)


@dataclasses.dataclass(frozen=True)
class Augment:
    stat: AugmentStat
    value: int
    pool_id: str


# Sample pools
AUGMENT_POOLS: tuple[AugmentPool, ...] = (
    AugmentPool(
        pool_id="magian_dd",
        label="Magian Trial - Damage Dealer",
        entries=(
            AugmentEntry(AugmentStat.STR, 5, weight=20),
            AugmentEntry(AugmentStat.DEX, 5, weight=20),
            AugmentEntry(AugmentStat.ATTACK, 12, weight=15),
            AugmentEntry(AugmentStat.ACCURACY, 8, weight=15),
            AugmentEntry(AugmentStat.HASTE, 2, weight=8),
            AugmentEntry(AugmentStat.DOUBLE_ATTACK, 3, weight=6),
            AugmentEntry(AugmentStat.CRIT_RATE, 4, weight=6),
            AugmentEntry(AugmentStat.HP, 30, weight=10),
        ),
        max_per_roll=3,
    ),
    AugmentPool(
        pool_id="magian_caster",
        label="Magian Trial - Caster",
        entries=(
            AugmentEntry(AugmentStat.INT, 6, weight=18),
            AugmentEntry(AugmentStat.MND, 6, weight=18),
            AugmentEntry(AugmentStat.MAGIC_ATTACK, 10, weight=18),
            AugmentEntry(AugmentStat.MAGIC_ACCURACY, 10, weight=18),
            AugmentEntry(AugmentStat.MP, 40, weight=12),
            AugmentEntry(AugmentStat.REFRESH, 1, weight=8),
            AugmentEntry(AugmentStat.HP, 25, weight=8),
        ),
        max_per_roll=3,
    ),
    AugmentPool(
        pool_id="reisenjima_high",
        label="Reisenjima High-Tier",
        entries=(
            AugmentEntry(AugmentStat.STR, 10, weight=10),
            AugmentEntry(AugmentStat.DEX, 10, weight=10),
            AugmentEntry(AugmentStat.HP, 60, weight=10),
            AugmentEntry(AugmentStat.MP, 80, weight=10),
            AugmentEntry(AugmentStat.HASTE, 4, weight=8),
            AugmentEntry(AugmentStat.REGEN, 4, weight=8),
        ),
        max_per_roll=4,
    ),
)

POOL_BY_ID: dict[str, AugmentPool] = {
    p.pool_id: p for p in AUGMENT_POOLS
}


def _weighted_pick(
    entries: t.Sequence[AugmentEntry],
    rng,
) -> AugmentEntry:
    total = sum(e.weight for e in entries)
    roll = rng.uniform(0, total)
    cum = 0.0
    for e in entries:
        cum += e.weight
        if roll <= cum:
            return e
    return entries[-1]


def roll_augments(
    *,
    pool: AugmentPool,
    rng_pool: RngPool,
    count: int,
    stream_name: str = STREAM_LOOT_DROPS,
) -> tuple[Augment, ...]:
    """Roll up to *count* augments from *pool*. Without replacement
    by stat — the same stat won't appear twice in one roll. Caps
    at pool.max_per_roll."""
    if count < 0:
        raise ValueError("count must be >= 0")
    if count == 0:
        return ()
    rolls = min(count, pool.max_per_roll, len(pool.entries))
    rng = rng_pool.stream(stream_name)
    available = list(pool.entries)
    out: list[Augment] = []
    used_stats: set[AugmentStat] = set()
    for _ in range(rolls):
        eligible = [e for e in available
                    if e.stat not in used_stats]
        if not eligible:
            break
        picked = _weighted_pick(eligible, rng)
        out.append(Augment(
            stat=picked.stat, value=picked.value,
            pool_id=pool.pool_id,
        ))
        used_stats.add(picked.stat)
    return tuple(out)


__all__ = [
    "AugmentStat", "AugmentEntry", "AugmentPool", "Augment",
    "AUGMENT_POOLS", "POOL_BY_ID",
    "roll_augments",
]
