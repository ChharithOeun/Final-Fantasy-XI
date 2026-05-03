"""Treasure map — discoverable treasure maps with X marks.

Mobs, chests, and NMs occasionally drop a TreasureMap. The map
points to a hidden DIG_SITE in another zone — the player has
to physically walk there, find the X area, and dig (or
interact). On success, a treasure cache opens. Maps degrade
through resolution attempts: a wrong-zone dig wastes one of the
map's three USES, then it crumbles.

Map quality is rolled at drop-time:
  WORN     1 use, low-tier loot
  DECENT   2 uses, mid-tier
  PRISTINE 3 uses, high-tier (+ chance of NM marker)

Public surface
--------------
    MapQuality enum
    TreasureCacheTier enum
    TreasureMap dataclass
    DigResult dataclass
    TreasureMapRegistry
        .mint_map(zone_id, x, y, quality, ...) -> TreasureMap
        .grant_to_player(map_id, player_id) -> bool
        .dig(player_id, map_id, zone_id, x, y, tolerance) -> DigResult
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Default dig tolerance — player must be within this radius of X.
DEFAULT_DIG_RADIUS = 10.0


class MapQuality(str, enum.Enum):
    WORN = "worn"
    DECENT = "decent"
    PRISTINE = "pristine"


_USES_BY_QUALITY: dict[MapQuality, int] = {
    MapQuality.WORN: 1,
    MapQuality.DECENT: 2,
    MapQuality.PRISTINE: 3,
}


class TreasureCacheTier(str, enum.Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    NM_MARKED = "nm_marked"     # high quality + special


@dataclasses.dataclass
class TreasureMap:
    map_id: str
    zone_id: str
    x: float
    y: float
    quality: MapQuality
    cache_tier: TreasureCacheTier
    uses_remaining: int
    holder_player_id: t.Optional[str] = None
    minted_at_seconds: float = 0.0
    consumed: bool = False


@dataclasses.dataclass(frozen=True)
class DigResult:
    accepted: bool
    cache_tier: t.Optional[TreasureCacheTier] = None
    map_consumed: bool = False
    distance_to_x: float = 0.0
    uses_remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class TreasureMapRegistry:
    dig_radius: float = DEFAULT_DIG_RADIUS
    _maps: dict[str, TreasureMap] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def mint_map(
        self, *, zone_id: str, x: float, y: float,
        quality: MapQuality,
        cache_tier: t.Optional[TreasureCacheTier] = None,
        now_seconds: float = 0.0,
    ) -> TreasureMap:
        # Default cache_tier follows quality if unspecified
        if cache_tier is None:
            cache_tier = {
                MapQuality.WORN: TreasureCacheTier.LOW,
                MapQuality.DECENT: TreasureCacheTier.MID,
                MapQuality.PRISTINE: TreasureCacheTier.HIGH,
            }[quality]
        mid = f"map_{self._next_id}"
        self._next_id += 1
        m = TreasureMap(
            map_id=mid, zone_id=zone_id,
            x=x, y=y, quality=quality,
            cache_tier=cache_tier,
            uses_remaining=_USES_BY_QUALITY[quality],
            minted_at_seconds=now_seconds,
        )
        self._maps[mid] = m
        return m

    def map_for(
        self, map_id: str,
    ) -> t.Optional[TreasureMap]:
        return self._maps.get(map_id)

    def grant_to_player(
        self, *, map_id: str, player_id: str,
    ) -> bool:
        m = self._maps.get(map_id)
        if m is None or m.consumed:
            return False
        if m.holder_player_id is not None:
            return False
        m.holder_player_id = player_id
        return True

    def dig(
        self, *, player_id: str, map_id: str,
        zone_id: str, x: float, y: float,
    ) -> DigResult:
        m = self._maps.get(map_id)
        if m is None:
            return DigResult(
                False, reason="no such map",
            )
        if m.consumed:
            return DigResult(
                False, reason="map already consumed",
            )
        if m.holder_player_id != player_id:
            return DigResult(
                False, reason="not the holder",
            )
        # Wrong zone burns a use, no payout
        if m.zone_id != zone_id:
            m.uses_remaining -= 1
            if m.uses_remaining <= 0:
                m.consumed = True
            return DigResult(
                False,
                map_consumed=m.consumed,
                uses_remaining=max(0, m.uses_remaining),
                reason="wrong zone",
            )
        # Compute distance
        dx = x - m.x
        dy = y - m.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > self.dig_radius:
            m.uses_remaining -= 1
            if m.uses_remaining <= 0:
                m.consumed = True
            return DigResult(
                False,
                map_consumed=m.consumed,
                distance_to_x=dist,
                uses_remaining=max(0, m.uses_remaining),
                reason="too far from X",
            )
        # Hit — payout and consume map fully
        m.consumed = True
        m.uses_remaining = 0
        return DigResult(
            accepted=True,
            cache_tier=m.cache_tier,
            map_consumed=True,
            distance_to_x=dist,
            uses_remaining=0,
        )

    def total_maps(self) -> int:
        return len(self._maps)


__all__ = [
    "DEFAULT_DIG_RADIUS",
    "MapQuality", "TreasureCacheTier",
    "TreasureMap", "DigResult",
    "TreasureMapRegistry",
]
