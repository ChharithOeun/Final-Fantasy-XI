"""Fomor strength under no-sunlight conditions.

Per the user direction: 'fomors are strong at night and in dungeons
where there is no sunlight'. Same logic applies to outlaw fomors —
they're also strong in dungeons. The multipliers stack onto whatever
their base level confers.

Daytime: 1.0 (baseline)
Dawn / dusk: 1.10 (transitional, slightly empowered)
Nighttime: 1.25
Dungeon (always sunless): 1.35
Eternal night (Dynamis / endgame zones): 1.50
"""
from __future__ import annotations

from .terrain import LightingState


# Base multipliers per lighting state.
NIGHT_FOMOR_MULTIPLIER = 1.25
DUNGEON_FOMOR_MULTIPLIER = 1.35
ETERNAL_NIGHT_FOMOR_MULTIPLIER = 1.50


def fomor_lighting_strength(lighting: LightingState) -> float:
    """Return the all-stats multiplier for a fomor under this lighting.

    Daytime is baseline 1.0. Dawn/dusk are slight transitional bumps.
    Nighttime fomors are 25% stronger; dungeon fomors 35%; eternal-
    night fomors 50% (Dynamis / Sky-of-Eternal-Twilight).
    """
    if lighting == LightingState.DAYTIME:
        return 1.0
    if lighting in (LightingState.DAWN, LightingState.DUSK):
        return 1.10
    if lighting == LightingState.NIGHTTIME:
        return NIGHT_FOMOR_MULTIPLIER
    if lighting == LightingState.DUNGEON:
        return DUNGEON_FOMOR_MULTIPLIER
    if lighting == LightingState.ETERNAL_NIGHT:
        return ETERNAL_NIGHT_FOMOR_MULTIPLIER
    return 1.0
