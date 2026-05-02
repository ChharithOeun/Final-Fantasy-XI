"""Item-level (i-lvl) system — level-relative ceiling.

Canonical FFXI froze i-lvl at 119 (a +20 effective-level bump on
top of a level-99 character). Demoncore's ML 100-150 expansion
makes that ceiling stale: at level 150 the player's own stat
pool already exceeds what i-lvl 119 represented.

Solution: tie the i-lvl ceiling to the player's actual level.

    i_lvl_ceiling = player_level + ILVL_BUFFER

with ILVL_BUFFER = 25, matching the canonical +20 the meta is
already used to (with a small breathing margin so existing
i-lvl 119 gear remains usable through ML 100).

| Player level | i-lvl ceiling |
|---|---|
| 75  | 100 (legacy)        |
| 99  | 124                  |
| 100 | 125                  |
| 125 | 150                  |
| 150 | **175**              |

The ceiling is the **average** of equipped i-lvls (canonical
behavior). Lower-i-lvl pieces in some slots can be carried by
higher pieces in others. Equipment with i-lvl above the
ceiling cannot equip — it stays in storage until you outlevel
the cap.

Public surface
--------------
    ILVL_BUFFER, LEGACY_ILVL_FLOOR, LEGACY_ILVL_HARD_CAP
    level_relative_ceiling(player_level) -> int
    average_ilvl(equipped) -> float
    can_equip(ilvl, player_level) -> bool
    excess_ceiling(equipped, player_level) -> int
"""
from __future__ import annotations

import typing as t


# How far above the player's level i-lvl can stretch.
ILVL_BUFFER = 25

# Canonical FFXI floor — i-lvl pieces don't exist below this.
LEGACY_ILVL_FLOOR = 100

# Canonical FFXI's old hard cap; we keep it as a soft floor so
# legacy gear still works on early-leveling characters.
LEGACY_ILVL_HARD_CAP = 119


def level_relative_ceiling(*, player_level: int) -> int:
    """Maximum allowed i-lvl for this player.

    Below the legacy floor (level 75 era) i-lvl gear is rare
    anyway, but we still report a sensible ceiling. At lvl 75
    or higher, ceiling is `level + 25`.
    """
    if player_level < 75:
        return max(LEGACY_ILVL_FLOOR, player_level + ILVL_BUFFER)
    return player_level + ILVL_BUFFER


def can_equip(*, item_ilvl: int, player_level: int) -> bool:
    """True iff this single item is at-or-below the player's ceiling."""
    if item_ilvl <= 0:
        return True   # non-i-lvl gear (level-based) always fine
    return item_ilvl <= level_relative_ceiling(player_level=player_level)


def average_ilvl(equipped_ilvls: t.Iterable[int]) -> float:
    """Average i-lvl across equipped slots. Slots with 0 (no
    i-lvl item, level-based gear) are excluded from the average
    — they don't drag it down."""
    ilvls = [i for i in equipped_ilvls if i > 0]
    if not ilvls:
        return 0.0
    return sum(ilvls) / len(ilvls)


def excess_ceiling(*, equipped_ilvls: t.Iterable[int],
                    player_level: int) -> int:
    """Headroom: ceiling - current_average_ilvl. Positive means
    you can equip a higher i-lvl piece without violating the
    average cap; negative means you're over (and effectively
    over-geared, which the equip system can use to refuse the
    last attempted piece)."""
    avg = average_ilvl(equipped_ilvls)
    cap = level_relative_ceiling(player_level=player_level)
    return int(cap - avg)


# Helper for migration: every place that hardcoded 119 should
# now route through this module.
def is_above_legacy_cap(item_ilvl: int) -> bool:
    return item_ilvl > LEGACY_ILVL_HARD_CAP


__all__ = [
    "ILVL_BUFFER",
    "LEGACY_ILVL_FLOOR", "LEGACY_ILVL_HARD_CAP",
    "level_relative_ceiling",
    "can_equip",
    "average_ilvl",
    "excess_ceiling",
    "is_above_legacy_cap",
]
