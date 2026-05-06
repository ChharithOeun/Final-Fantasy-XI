"""Trail marker — drop waypoints so the way home is findable.

A player wandering deep into a fogged wood can drop trail
markers behind them. Each marker is anchored at a (zone,
x, y) and described by what it's made of: a stone cairn
weathers slowly, a chalk blaze on bark fades fast, a
cloth ribbon survives until rain.

Markers belong to the player who placed them — other
players can see them too, but only the owner gets full
detail (custom note text). The system also exposes a
nearest-marker lookup so navigation aids can render an
arrow to the closest known waypoint.

Marker kinds and their natural decay rate (durability per
weather tick) are tuned so that a careful trail-layer
will rebuild markers regularly on a long expedition. A
cairn left for a year is *probably* still there; a ribbon
left in a rainforest probably isn't.

Public surface
--------------
    MarkerKind enum
    TrailMarker dataclass (mutable)
    TrailMarkerRegistry
        .place(marker_id, owner_id, kind, zone, x, y,
               note, placed_at) -> bool
        .erase(marker_id, by_owner_id) -> bool
        .weather_tick(weather_kind, dt_seconds) -> int
            (returns count of markers destroyed)
        .visible_in_zone(zone) -> list[TrailMarker]
        .nearest(zone, x, y) -> Optional[TrailMarker]
        .get(marker_id) -> Optional[TrailMarker]
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class MarkerKind(str, enum.Enum):
    STONE_CAIRN = "stone_cairn"   # nearly permanent
    WOOD_BLAZE = "wood_blaze"     # axe slash on a tree
    CHALK_MARK = "chalk_mark"     # bright but fragile
    CLOTH_RIBBON = "cloth_ribbon" # visible, weather-frail
    BONE_TOTEM = "bone_totem"     # ritual; resists most


# durability is opaque "marker hp"; weather subtracts from
# it, and the marker is destroyed at <= 0
_BASE_DURABILITY: dict[MarkerKind, int] = {
    MarkerKind.STONE_CAIRN: 1000,
    MarkerKind.WOOD_BLAZE: 200,
    MarkerKind.CHALK_MARK: 60,
    MarkerKind.CLOTH_RIBBON: 100,
    MarkerKind.BONE_TOTEM: 500,
}

# how much each weather kind subtracts from a marker's
# durability per second of exposure. 0 means immune.
_WEATHER_DAMAGE: dict[str, dict[MarkerKind, int]] = {
    "clear": {k: 0 for k in MarkerKind},
    "rain": {
        MarkerKind.STONE_CAIRN: 0,
        MarkerKind.WOOD_BLAZE: 0,
        MarkerKind.CHALK_MARK: 5,
        MarkerKind.CLOTH_RIBBON: 2,
        MarkerKind.BONE_TOTEM: 0,
    },
    "thunderstorm": {
        MarkerKind.STONE_CAIRN: 0,
        MarkerKind.WOOD_BLAZE: 1,
        MarkerKind.CHALK_MARK: 8,
        MarkerKind.CLOTH_RIBBON: 4,
        MarkerKind.BONE_TOTEM: 0,
    },
    "snow": {
        MarkerKind.STONE_CAIRN: 0,
        MarkerKind.WOOD_BLAZE: 0,
        MarkerKind.CHALK_MARK: 1,
        MarkerKind.CLOTH_RIBBON: 1,
        MarkerKind.BONE_TOTEM: 0,
    },
    "blizzard": {
        MarkerKind.STONE_CAIRN: 1,
        MarkerKind.WOOD_BLAZE: 2,
        MarkerKind.CHALK_MARK: 10,
        MarkerKind.CLOTH_RIBBON: 6,
        MarkerKind.BONE_TOTEM: 1,
    },
    "sandstorm": {
        MarkerKind.STONE_CAIRN: 1,
        MarkerKind.WOOD_BLAZE: 3,
        MarkerKind.CHALK_MARK: 10,
        MarkerKind.CLOTH_RIBBON: 4,
        MarkerKind.BONE_TOTEM: 1,
    },
}


@dataclasses.dataclass
class TrailMarker:
    marker_id: str
    owner_id: str
    kind: MarkerKind
    zone: str
    x: float
    y: float
    note: str
    placed_at: int
    durability: int


@dataclasses.dataclass
class TrailMarkerRegistry:
    _markers: dict[str, TrailMarker] = dataclasses.field(
        default_factory=dict,
    )

    def place(
        self, *, marker_id: str, owner_id: str,
        kind: MarkerKind, zone: str,
        x: float, y: float,
        note: str, placed_at: int,
    ) -> bool:
        if not marker_id or not owner_id or not zone:
            return False
        if marker_id in self._markers:
            return False
        self._markers[marker_id] = TrailMarker(
            marker_id=marker_id, owner_id=owner_id,
            kind=kind, zone=zone, x=x, y=y,
            note=note, placed_at=placed_at,
            durability=_BASE_DURABILITY[kind],
        )
        return True

    def erase(
        self, *, marker_id: str, by_owner_id: str,
    ) -> bool:
        m = self._markers.get(marker_id)
        if m is None:
            return False
        # only the owner can erase intentionally
        if m.owner_id != by_owner_id:
            return False
        del self._markers[marker_id]
        return True

    def weather_tick(
        self, *, weather_kind: str, dt_seconds: int,
        zone: t.Optional[str] = None,
    ) -> int:
        if dt_seconds <= 0:
            return 0
        wk = weather_kind.lower()
        damage_table = _WEATHER_DAMAGE.get(wk)
        if damage_table is None:
            return 0
        destroyed: list[str] = []
        for mid, m in self._markers.items():
            if zone is not None and m.zone != zone:
                continue
            d = damage_table.get(m.kind, 0)
            if d <= 0:
                continue
            m.durability -= d * dt_seconds
            if m.durability <= 0:
                destroyed.append(mid)
        for mid in destroyed:
            del self._markers[mid]
        return len(destroyed)

    def visible_in_zone(
        self, *, zone: str,
    ) -> list[TrailMarker]:
        return [
            m for m in self._markers.values()
            if m.zone == zone
        ]

    def nearest(
        self, *, zone: str, x: float, y: float,
    ) -> t.Optional[TrailMarker]:
        best: t.Optional[TrailMarker] = None
        best_d = math.inf
        for m in self._markers.values():
            if m.zone != zone:
                continue
            d = math.hypot(m.x - x, m.y - y)
            if d < best_d:
                best_d = d
                best = m
        return best

    def get(
        self, *, marker_id: str,
    ) -> t.Optional[TrailMarker]:
        return self._markers.get(marker_id)

    def total_markers(self) -> int:
        return len(self._markers)


__all__ = [
    "MarkerKind", "TrailMarker", "TrailMarkerRegistry",
]
