"""Homepoint warp system.

Touch a Home Point to register it. From anywhere you can warp
to any registered HP for a gil cost that scales with the
straight-line zone-distance between source and destination.

Public surface
--------------
    HomepointId
    HOMEPOINT_CATALOG
    PlayerHomepoints
        .register(hp_id, current_zone) -> bool
        .warp(target_hp_id, current_zone, gil_balance) -> WarpResult
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class Homepoint:
    hp_id: str
    label: str
    zone: str
    region: str         # 'sandy' | 'bastok' | 'windy' | 'jeuno' | 'outpost'


# Sample registry — a representative slice of FFXI HP locations.
# In production this would cover all canonical HPs.
HOMEPOINT_CATALOG: dict[str, Homepoint] = {
    "sandy_hp1": Homepoint(
        "sandy_hp1", "Sandoria HP #1", "northern_sandoria", "sandy",
    ),
    "bastok_hp1": Homepoint(
        "bastok_hp1", "Bastok HP #1", "bastok_markets", "bastok",
    ),
    "windy_hp1": Homepoint(
        "windy_hp1", "Windurst HP #1", "windurst_woods", "windy",
    ),
    "jeuno_hp1": Homepoint(
        "jeuno_hp1", "Lower Jeuno HP", "lower_jeuno", "jeuno",
    ),
    "selbina_hp": Homepoint(
        "selbina_hp", "Selbina HP", "selbina", "outpost",
    ),
    "mhaura_hp": Homepoint(
        "mhaura_hp", "Mhaura HP", "mhaura", "outpost",
    ),
    "rabao_hp": Homepoint(
        "rabao_hp", "Rabao HP", "rabao", "outpost",
    ),
    "kazham_hp": Homepoint(
        "kazham_hp", "Kazham HP", "kazham", "outpost",
    ),
    "norg_hp": Homepoint(
        "norg_hp", "Norg HP", "norg", "outpost",
    ),
}


# Base-cost lookup. Same-region: cheap. Cross-region: more.
_BASE_COST_SAME_REGION = 100
_BASE_COST_CROSS_NATION = 500
_BASE_COST_OUTPOST = 800


def _cost(*, source: Homepoint, dest: Homepoint) -> int:
    if source.hp_id == dest.hp_id:
        return 0  # warping to where you already are
    if source.region == dest.region:
        return _BASE_COST_SAME_REGION
    if dest.region == "outpost" or source.region == "outpost":
        return _BASE_COST_OUTPOST
    return _BASE_COST_CROSS_NATION


@dataclasses.dataclass(frozen=True)
class WarpResult:
    accepted: bool
    cost: int = 0
    new_zone: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerHomepoints:
    player_id: str
    _registered: set[str] = dataclasses.field(default_factory=set)

    @property
    def registered(self) -> frozenset[str]:
        return frozenset(self._registered)

    def register(self, *, hp_id: str, current_zone: str) -> bool:
        """Touching the HP registers it. Must be in its zone."""
        hp = HOMEPOINT_CATALOG.get(hp_id)
        if hp is None:
            return False
        if hp.zone != current_zone:
            return False
        self._registered.add(hp_id)
        return True

    def warp(self, *, target_hp_id: str, current_zone: str,
             gil_balance: int) -> WarpResult:
        target = HOMEPOINT_CATALOG.get(target_hp_id)
        if target is None:
            return WarpResult(False, reason="unknown homepoint")
        if target_hp_id not in self._registered:
            return WarpResult(False, reason="not registered")

        # Source = whichever registered HP is in the current zone,
        # else the home nation HP (cheapest non-outpost we own).
        source: t.Optional[Homepoint] = None
        for hid in self._registered:
            cand = HOMEPOINT_CATALOG[hid]
            if cand.zone == current_zone:
                source = cand
                break
        if source is None:
            # fall back to "warp anywhere" — pick cheapest registered
            # nation HP as source
            for hid in self._registered:
                cand = HOMEPOINT_CATALOG[hid]
                if cand.region != "outpost":
                    source = cand
                    break
            if source is None:
                # all registered are outposts; just pick any
                source = HOMEPOINT_CATALOG[next(iter(self._registered))]

        cost = _cost(source=source, dest=target)
        if gil_balance < cost:
            return WarpResult(False, reason="insufficient gil",
                              cost=cost)
        return WarpResult(
            accepted=True, cost=cost, new_zone=target.zone,
        )


__all__ = [
    "Homepoint",
    "HOMEPOINT_CATALOG",
    "WarpResult",
    "PlayerHomepoints",
]
