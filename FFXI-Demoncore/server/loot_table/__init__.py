"""Loot tables — mob drop rolls, rarity tiers, Treasure Hunter.

Why this module exists
----------------------
Every mob in Vana'diel has a drop table, and FFXI's classic
charm is the per-tier rarity grammar:

    common    - drops most fights (60-100% post-TH)
    uncommon  - shows up regularly (15-50%)
    rare      - the thing you actually came here for (1-12%)
    super_rare- the lottery item (0.1-2%)
    ex        - exclusive/cannot be sold; gated by other rules

Treasure Hunter (THF subjob) bumps drop rates per tier — modeled
here as a multiplicative modifier per-tier so a TH IV THF/THF
gets a meaningful bump on rares without inflating commons past
their cap.

The roll engine is deterministic given an RngPool — the same
world seed + same kill order produces the same drops, which is
the property the replay system depends on.

Public surface
--------------
    Rarity                  enum (COMMON/UNCOMMON/RARE/SUPER_RARE/EX)
    DropEntry               immutable: item_id, base_rate, rarity
    DropTable               mob_class_id + entries + extras
    ItemDrop                what came out of a roll
    treasure_hunter_modifier(tier, th_level)  -> multiplier
    roll_drops(*, table, rng_pool, th_level)  -> list[ItemDrop]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_LOOT_DROPS


class Rarity(str, enum.Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    SUPER_RARE = "super_rare"
    EX = "ex"


@dataclasses.dataclass(frozen=True)
class DropEntry:
    """One slot in a mob's drop table."""
    item_id: str
    base_rate: float                  # 0..1 inclusive
    rarity: Rarity
    label: str = ""                   # human-friendly name (optional)

    def __post_init__(self) -> None:
        if not 0.0 <= self.base_rate <= 1.0:
            raise ValueError(
                f"base_rate {self.base_rate} out of [0,1]"
            )


@dataclasses.dataclass(frozen=True)
class DropTable:
    """A mob's complete drop table.

    `entries` is rolled per kill. Each entry rolls independently;
    the same kill can drop multiple items (FFXI doesn't have a
    "one drop per kill" cap; gil counts as one entry too).
    """
    mob_class_id: str
    entries: tuple[DropEntry, ...]
    label: str = ""

    def by_rarity(self, r: Rarity) -> tuple[DropEntry, ...]:
        return tuple(e for e in self.entries if e.rarity == r)


@dataclasses.dataclass(frozen=True)
class ItemDrop:
    """One result of a single drop roll."""
    item_id: str
    rarity: Rarity
    rolled_against: float             # the threshold the dice cleared


# Treasure Hunter caps per tier — TH only ever HELPS, never lowers
# a rate, and at high tiers it caps so commons don't go past 100%.
# Numbers loosely calibrated against retail FFXI tier shifts:
#   TH I/II/III/IV adds modest, diminishing boosts.
#   Beyond IV the boost levels off — what TH IV+ buys you is the
#   re-roll on the rare tier when the first roll fails, but for
#   simplicity we just bump the multiplier here.
_TH_MODIFIERS: dict[Rarity, dict[int, float]] = {
    Rarity.COMMON: {
        0: 1.00, 1: 1.05, 2: 1.10, 3: 1.13, 4: 1.15,
        5: 1.16, 6: 1.17, 7: 1.18, 8: 1.19, 9: 1.20,
    },
    Rarity.UNCOMMON: {
        0: 1.00, 1: 1.10, 2: 1.20, 3: 1.27, 4: 1.32,
        5: 1.36, 6: 1.40, 7: 1.43, 8: 1.46, 9: 1.50,
    },
    Rarity.RARE: {
        0: 1.00, 1: 1.20, 2: 1.40, 3: 1.55, 4: 1.65,
        5: 1.74, 6: 1.82, 7: 1.90, 8: 1.97, 9: 2.05,
    },
    Rarity.SUPER_RARE: {
        0: 1.00, 1: 1.25, 2: 1.50, 3: 1.70, 4: 1.85,
        5: 1.97, 6: 2.07, 7: 2.16, 8: 2.24, 9: 2.30,
    },
    # EX items have fixed gates — TH does not affect them. The
    # modifier is identity at every TH level.
    Rarity.EX: {i: 1.0 for i in range(10)},
}

MAX_TH_LEVEL = 9


def treasure_hunter_modifier(rarity: Rarity, th_level: int) -> float:
    """Return the multiplicative TH modifier for *rarity* at
    Treasure Hunter level *th_level* (0..9).

    Out-of-range th_levels saturate at MAX_TH_LEVEL.
    """
    if th_level < 0:
        raise ValueError(f"th_level {th_level} must be >= 0")
    clamped = min(th_level, MAX_TH_LEVEL)
    return _TH_MODIFIERS[rarity][clamped]


def _effective_rate(entry: DropEntry, th_level: int) -> float:
    """Compute the post-TH drop rate, clamped to [0, 1]."""
    raw = entry.base_rate * treasure_hunter_modifier(
        entry.rarity, th_level
    )
    return min(1.0, raw)


def roll_drops(
    *,
    table: DropTable,
    rng_pool: RngPool,
    th_level: int = 0,
    stream_name: str = STREAM_LOOT_DROPS,
) -> tuple[ItemDrop, ...]:
    """Roll *table* once and return what dropped.

    Each entry rolls an independent percentage. Items drop when
    their roll is below the post-TH effective rate. Stream is
    the rng_pool stream — defaults to STREAM_LOOT_DROPS so all
    loot is reproducible from world_seed alone.
    """
    out: list[ItemDrop] = []
    rng = rng_pool.stream(stream_name)
    for entry in table.entries:
        threshold = _effective_rate(entry, th_level)
        roll = rng.random()
        if roll < threshold:
            out.append(ItemDrop(
                item_id=entry.item_id,
                rarity=entry.rarity,
                rolled_against=threshold,
            ))
    return tuple(out)


def drops_count_by_rarity(
    drops: t.Sequence[ItemDrop],
) -> dict[Rarity, int]:
    """Convenience: histogram drops by rarity."""
    bucket: dict[Rarity, int] = {r: 0 for r in Rarity}
    for d in drops:
        bucket[d.rarity] += 1
    return bucket


__all__ = [
    "Rarity",
    "DropEntry",
    "DropTable",
    "ItemDrop",
    "MAX_TH_LEVEL",
    "treasure_hunter_modifier",
    "roll_drops",
    "drops_count_by_rarity",
]
