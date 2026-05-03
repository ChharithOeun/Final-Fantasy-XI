"""Wayfinder compass — 3D compass UI with pinned waypoints.

Sits next to the minimap. The compass shows direction +
distance to a player's pinned waypoints — a quest objective,
a party leader, a homepoint, a memorial site. Pins can be
private, party-shared, or linkshell-shared.

Each pin has a CATEGORY that drives icon color/style; the UI
renders them as floating glyphs around the compass ring with a
distance readout. Distance updates as the player moves. Pins
auto-expire when their target is reached or when they hit
expiry_at_seconds.

Public surface
--------------
    PinCategory enum
    Visibility enum
    Waypoint dataclass
    CompassReading dataclass
    WayfinderCompass
        .pin(player_id, label, zone, x, y, z, category, vis)
        .unpin(player_id, pin_id)
        .reading_for(player_id, x, y, z, zone) -> CompassReading
        .check_arrival(player_id, x, y, z, zone, radius)
        .pins_for(player_id, sharing_filter)
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Default arrival radius for auto-clear.
DEFAULT_ARRIVAL_RADIUS = 8.0


class PinCategory(str, enum.Enum):
    QUEST_OBJECTIVE = "quest_objective"
    PARTY_LEADER = "party_leader"
    HOMEPOINT = "homepoint"
    MEMORIAL = "memorial"
    NM_SIGHTING = "nm_sighting"
    HIDDEN_PATH = "hidden_path"
    GENERIC = "generic"


class Visibility(str, enum.Enum):
    PRIVATE = "private"
    PARTY = "party"
    LINKSHELL = "linkshell"


_PIN_COLOR: dict[PinCategory, str] = {
    PinCategory.QUEST_OBJECTIVE: "gold",
    PinCategory.PARTY_LEADER: "cyan",
    PinCategory.HOMEPOINT: "blue",
    PinCategory.MEMORIAL: "violet",
    PinCategory.NM_SIGHTING: "red",
    PinCategory.HIDDEN_PATH: "green",
    PinCategory.GENERIC: "white",
}


@dataclasses.dataclass
class Waypoint:
    pin_id: str
    owner_player_id: str
    label: str
    zone_id: str
    x: float
    y: float
    z: float
    category: PinCategory
    visibility: Visibility = Visibility.PRIVATE
    posted_at_seconds: float = 0.0
    expires_at_seconds: t.Optional[float] = None


@dataclasses.dataclass(frozen=True)
class CompassPinReading:
    pin_id: str
    label: str
    category: PinCategory
    color: str
    bearing_radians: float    # 0=north, +pi/2=east, etc.
    distance: float
    same_zone: bool


@dataclasses.dataclass(frozen=True)
class CompassReading:
    player_id: str
    zone_id: str
    pins: tuple[CompassPinReading, ...]


@dataclasses.dataclass
class WayfinderCompass:
    arrival_radius: float = DEFAULT_ARRIVAL_RADIUS
    _pins: dict[str, Waypoint] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def pin(
        self, *, owner_player_id: str, label: str,
        zone_id: str, x: float, y: float, z: float = 0.0,
        category: PinCategory = PinCategory.GENERIC,
        visibility: Visibility = Visibility.PRIVATE,
        now_seconds: float = 0.0,
        expires_at_seconds: t.Optional[float] = None,
    ) -> Waypoint:
        pid = f"pin_{self._next_id}"
        self._next_id += 1
        wp = Waypoint(
            pin_id=pid,
            owner_player_id=owner_player_id,
            label=label, zone_id=zone_id,
            x=x, y=y, z=z, category=category,
            visibility=visibility,
            posted_at_seconds=now_seconds,
            expires_at_seconds=expires_at_seconds,
        )
        self._pins[pid] = wp
        return wp

    def unpin(
        self, *, owner_player_id: str, pin_id: str,
    ) -> bool:
        wp = self._pins.get(pin_id)
        if wp is None:
            return False
        if wp.owner_player_id != owner_player_id:
            return False
        del self._pins[pin_id]
        return True

    def pins_for(
        self, *, owner_player_id: str,
    ) -> tuple[Waypoint, ...]:
        return tuple(
            wp for wp in self._pins.values()
            if wp.owner_player_id == owner_player_id
        )

    def reading_for(
        self, *, player_id: str, zone_id: str,
        x: float, y: float, z: float = 0.0,
    ) -> CompassReading:
        readings: list[CompassPinReading] = []
        for wp in self._pins.values():
            if wp.owner_player_id != player_id:
                continue
            same_zone = wp.zone_id == zone_id
            dx = wp.x - x
            dy = wp.y - y
            dz = wp.z - z
            distance = math.sqrt(
                dx * dx + dy * dy + dz * dz,
            )
            # Bearing — 0 rad = north (+y), measured clockwise
            bearing = math.atan2(dx, dy)
            readings.append(CompassPinReading(
                pin_id=wp.pin_id, label=wp.label,
                category=wp.category,
                color=_PIN_COLOR[wp.category],
                bearing_radians=bearing,
                distance=distance,
                same_zone=same_zone,
            ))
        # Sort closest first within same-zone, then far ones
        readings.sort(
            key=lambda r: (not r.same_zone, r.distance),
        )
        return CompassReading(
            player_id=player_id, zone_id=zone_id,
            pins=tuple(readings),
        )

    def check_arrival(
        self, *, player_id: str, zone_id: str,
        x: float, y: float, z: float = 0.0,
    ) -> tuple[str, ...]:
        """Auto-clears any pins owned by player inside arrival
        radius. Returns the cleared pin_ids."""
        cleared: list[str] = []
        for pid, wp in list(self._pins.items()):
            if wp.owner_player_id != player_id:
                continue
            if wp.zone_id != zone_id:
                continue
            dx = wp.x - x
            dy = wp.y - y
            dz = wp.z - z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist <= self.arrival_radius:
                del self._pins[pid]
                cleared.append(pid)
        return tuple(cleared)

    def expire_check(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for pid, wp in list(self._pins.items()):
            if wp.expires_at_seconds is None:
                continue
            if now_seconds >= wp.expires_at_seconds:
                del self._pins[pid]
                expired.append(pid)
        return tuple(expired)

    def total_pins(self) -> int:
        return len(self._pins)


__all__ = [
    "DEFAULT_ARRIVAL_RADIUS",
    "PinCategory", "Visibility",
    "Waypoint", "CompassPinReading", "CompassReading",
    "WayfinderCompass",
]
