"""Mog Tablet — Mog Garden entrance + plot scaling.

The Mog Tablet placed in your Mog House is the entrance to your
Mog Garden. Garden plot capacity grows with rank/level milestones.
Each tablet placement opens a teleport doorway from Mog House.

Public surface
--------------
    TabletState dataclass
    plot_capacity_for(rank, level) - rule for how many pots
    place_tablet / use_tablet flow
"""
from __future__ import annotations

import dataclasses
import typing as t


# Plot capacity rules — rank gates the base, level fine-tunes.
BASE_PLOT_CAPACITY_BY_RANK: dict[int, int] = {
    1: 4,
    2: 5,
    3: 6,
    4: 7,
    5: 8,
}
BASE_PLOT_CAPACITY_OVER_5 = 8     # ranks 6+ all start at 8


# Level gives bonus plots above rank baseline
def _level_plot_bonus(level: int) -> int:
    if level < 30:
        return 0
    if level < 60:
        return 1
    if level < 90:
        return 2
    return 3


MAX_PLOTS_HARD_CAP = 12


def plot_capacity_for(*, rank: int, level: int) -> int:
    """Number of garden plots this player can use."""
    if rank <= 0 or level <= 0:
        return 0
    base = BASE_PLOT_CAPACITY_BY_RANK.get(
        rank, BASE_PLOT_CAPACITY_OVER_5,
    )
    bonus = _level_plot_bonus(level)
    return min(MAX_PLOTS_HARD_CAP, base + bonus)


# Minimum requirements to even place a tablet at all.
MIN_RANK_FOR_TABLET = 1
MIN_LEVEL_FOR_TABLET = 1


@dataclasses.dataclass(frozen=True)
class PlaceResult:
    accepted: bool
    plot_capacity: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class TabletState:
    player_id: str
    placed: bool = False
    plot_capacity: int = 0


def place_tablet(
    *,
    state: TabletState,
    rank: int, level: int,
) -> PlaceResult:
    if state.placed:
        return PlaceResult(False, reason="already placed")
    if rank < MIN_RANK_FOR_TABLET:
        return PlaceResult(False, reason="need nation rank 1+")
    if level < MIN_LEVEL_FOR_TABLET:
        return PlaceResult(False, reason="need character level 1+")
    state.placed = True
    cap = plot_capacity_for(rank=rank, level=level)
    state.plot_capacity = cap
    return PlaceResult(accepted=True, plot_capacity=cap)


def refresh_plot_capacity(
    *, state: TabletState, rank: int, level: int,
) -> int:
    """Recompute plot capacity after a rank/level change.
    Returns the new capacity. Tablet must be placed."""
    if not state.placed:
        return 0
    state.plot_capacity = plot_capacity_for(
        rank=rank, level=level,
    )
    return state.plot_capacity


def can_enter_garden(state: TabletState) -> bool:
    return state.placed


__all__ = [
    "BASE_PLOT_CAPACITY_BY_RANK", "MAX_PLOTS_HARD_CAP",
    "MIN_RANK_FOR_TABLET", "MIN_LEVEL_FOR_TABLET",
    "plot_capacity_for",
    "PlaceResult", "TabletState",
    "place_tablet", "refresh_plot_capacity", "can_enter_garden",
]
