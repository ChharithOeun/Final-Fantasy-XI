"""Altitude bands — five-layer vertical grammar for the sky.

The sky is the third theatre after surface land and the deep
underwater. The same five-band approach the deep uses applies
upward: GROUND (sailing/chocobos), LOW (skiff height), MID
(airship cruise), HIGH (military zeppelins), STRATOSPHERE
(jet-stream / dragon territory). Same fade rules as
underwater_minimap so the same client UI renders both.

Public surface
--------------
    AltitudeBand int enum
    AltitudeContact dataclass (frozen)
    AerialMinimap (band-aware visibility)
        .register(entity_id, band, x, y, kind)
        .update_position(entity_id, band, x, y)
        .remove(entity_id)
        .visible_to(player_band) -> tuple[AltitudeContact, ...]
        .altitude_of(entity_id) -> AltitudeBand or None
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AltitudeBand(int, enum.Enum):
    GROUND = 0
    LOW = 1
    MID = 2
    HIGH = 3
    STRATOSPHERE = 4


ADJACENT_BAND_FADE = 0.5
SAME_BAND_OPACITY = 1.0


# canonical altitudes (meters above ground) per band
BAND_ALTITUDE_M: dict[int, float] = {
    0: 0.0,        # GROUND
    1: 80.0,       # LOW (skiff)
    2: 400.0,      # MID (airship cruise)
    3: 1500.0,     # HIGH (military zeppelin)
    4: 8000.0,     # STRATOSPHERE (dragons / jet stream)
}


@dataclasses.dataclass(frozen=True)
class _Entity:
    entity_id: str
    band: AltitudeBand
    x: float
    y: float
    kind: str


@dataclasses.dataclass(frozen=True)
class AltitudeContact:
    entity_id: str
    band: AltitudeBand
    x: float
    y: float
    kind: str
    fade_factor: float


@dataclasses.dataclass
class AerialMinimap:
    _entities: dict[str, _Entity] = dataclasses.field(default_factory=dict)

    def register(
        self, *, entity_id: str,
        band: AltitudeBand,
        x: float, y: float, kind: str,
    ) -> bool:
        if not entity_id:
            return False
        self._entities[entity_id] = _Entity(
            entity_id=entity_id, band=band, x=x, y=y, kind=kind,
        )
        return True

    def update_position(
        self, *, entity_id: str,
        band: AltitudeBand,
        x: float, y: float,
    ) -> bool:
        existing = self._entities.get(entity_id)
        if existing is None:
            return False
        self._entities[entity_id] = dataclasses.replace(
            existing, band=band, x=x, y=y,
        )
        return True

    def remove(self, *, entity_id: str) -> bool:
        return self._entities.pop(entity_id, None) is not None

    def visible_to(
        self, *, player_band: AltitudeBand,
    ) -> tuple[AltitudeContact, ...]:
        out: list[AltitudeContact] = []
        for ent in self._entities.values():
            band_gap = abs(int(ent.band) - int(player_band))
            if band_gap == 0:
                fade = SAME_BAND_OPACITY
            elif band_gap == 1:
                fade = ADJACENT_BAND_FADE
            else:
                continue
            out.append(AltitudeContact(
                entity_id=ent.entity_id, band=ent.band,
                x=ent.x, y=ent.y, kind=ent.kind,
                fade_factor=fade,
            ))
        return tuple(out)

    def altitude_of(
        self, *, entity_id: str,
    ) -> t.Optional[AltitudeBand]:
        ent = self._entities.get(entity_id)
        return ent.band if ent else None


__all__ = [
    "AltitudeBand", "AltitudeContact", "AerialMinimap",
    "ADJACENT_BAND_FADE", "SAME_BAND_OPACITY",
    "BAND_ALTITUDE_M",
]
