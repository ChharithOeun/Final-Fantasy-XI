"""Respawn timers — the doc's halved spawn schedule.

Per COMBAT_TEMPO.md the rule is:
    'Routine trash respawns in 1-15 minutes depending on zone tier.'
    'Standard NMs:                30 min - 2 hr'
    'Tougher NMs:                 4-12 hr'
    'Endgame placeholder-chain NMs (HNMs): 24 hr but with PoP spawn
        condition or trigger items, not pure timer'

10 minutes is the sweet spot for most tiers; newbie 5, end-game 15.
"""
from __future__ import annotations

import dataclasses
import enum

from .zone_density import ZoneTier


class RespawnCategory(str, enum.Enum):
    """The four spawn cadences the doc names."""
    TRASH = "trash"
    NM_STANDARD = "nm_standard"
    NM_TOUGH = "nm_tough"
    HNM = "hnm"


@dataclasses.dataclass(frozen=True)
class RespawnBand:
    """One respawn category's range and default."""
    category: RespawnCategory
    min_seconds: int
    max_seconds: int
    default_seconds: int
    has_pop_condition: bool = False
    notes: str = ""


# Convert minutes to seconds inline so tests can sanity-check.
_M = 60
_H = 3600

RESPAWN_BANDS: dict[RespawnCategory, RespawnBand] = {
    RespawnCategory.TRASH: RespawnBand(
        category=RespawnCategory.TRASH,
        min_seconds=1 * _M,
        max_seconds=15 * _M,
        default_seconds=10 * _M,        # doc: '10 minutes is the sweet spot'
        notes=("trash respawns 1-15 min depending on zone tier; "
                 "newbie leans 5, end-game leans 15"),
    ),
    RespawnCategory.NM_STANDARD: RespawnBand(
        category=RespawnCategory.NM_STANDARD,
        min_seconds=30 * _M,
        max_seconds=2 * _H,
        default_seconds=60 * _M,
        notes="30min-2hr standard NM respawn",
    ),
    RespawnCategory.NM_TOUGH: RespawnBand(
        category=RespawnCategory.NM_TOUGH,
        min_seconds=4 * _H,
        max_seconds=12 * _H,
        default_seconds=8 * _H,
        notes="4-12hr tougher NMs",
    ),
    RespawnCategory.HNM: RespawnBand(
        category=RespawnCategory.HNM,
        min_seconds=24 * _H,
        max_seconds=24 * _H,
        default_seconds=24 * _H,
        has_pop_condition=True,
        notes=("placeholder-chain NMs: 24hr base + PoP spawn condition "
                 "or trigger items, not pure timer"),
    ),
}


# Per-zone-tier trash respawn lean. Doc: 'newbie leans to 5,
# end-game leans to 15'. We anchor mid-tier and high-tier in
# between to make the curve sensible.
TRASH_RESPAWN_BY_ZONE_TIER: dict[ZoneTier, int] = {
    ZoneTier.NEWBIE:    5 * _M,
    ZoneTier.MID_TIER:  10 * _M,
    ZoneTier.HIGH_TIER: 12 * _M,
    ZoneTier.END_GAME:  15 * _M,
}


def get_band(category: RespawnCategory) -> RespawnBand:
    return RESPAWN_BANDS[category]


def trash_respawn_seconds(zone_tier: ZoneTier) -> int:
    """Per-zone-tier trash respawn lean."""
    return TRASH_RESPAWN_BY_ZONE_TIER[zone_tier]


def respawn_seconds_for(category: RespawnCategory,
                            *,
                            zone_tier: ZoneTier = ZoneTier.MID_TIER) -> int:
    """Resolve the default respawn time for this category.

    For TRASH the result is the per-zone-tier lean; everything else
    uses the band's `default_seconds`. Caller can ignore zone_tier
    for non-trash categories.
    """
    if category == RespawnCategory.TRASH:
        return trash_respawn_seconds(zone_tier)
    return get_band(category).default_seconds


def is_in_band(category: RespawnCategory, seconds: int) -> bool:
    """Diagnostic: does the configured respawn fall inside the doc's
    band?"""
    band = get_band(category)
    return band.min_seconds <= seconds <= band.max_seconds


def halve_og_respawn(seconds: int) -> int:
    """Build-order step 5: 'halve all spawn timers across the board'.

    Floors at the TRASH band's minimum (1 minute) so sub-minute values
    can't slip through and create the AoE-grinder problem the doc
    warns about.
    """
    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    halved = seconds // 2
    return max(RESPAWN_BANDS[RespawnCategory.TRASH].min_seconds, halved)
