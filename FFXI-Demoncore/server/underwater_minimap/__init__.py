"""Underwater minimap — 3D-aware minimap for submerged zones.

Surface minimaps are 2D; underwater they fail you because
half the threats are *above* or *below* you. This module
layers entities into five depth bands and serves a
band-aware view: same band = full opacity, adjacent band =
faded silhouette, two+ bands away = hidden.

The bands intentionally don't try to be metric (every dive
sim that does this becomes unreadable). They map to the
five biome layers a player actually feels:

    SURFACE   - 0m, sailing
    SHALLOW   - 0-30m, light, kelp, reef
    MID       - 30-100m, twilight, schools
    DEEP      - 100-300m, no light, big quiet things
    ABYSSAL   - 300m+, the bottom

A player on a sub at MID can see other MID contacts
clearly. SHALLOW + DEEP show as faded silhouettes
(adjacent). SURFACE and ABYSSAL are hidden — too far
vertically to matter on a tactical minimap.

Public surface
--------------
    DepthBand enum
    UnderwaterEntity dataclass (frozen)
    VisibleContact dataclass (frozen) - has fade_factor
    UnderwaterMinimap
        .register(entity_id, band, x, y, kind)
        .update_position(entity_id, band, x, y)
        .remove(entity_id)
        .visible_to(player_band) -> tuple[VisibleContact, ...]
        .depth_of(entity_id) -> DepthBand or None
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DepthBand(int, enum.Enum):
    SURFACE = 0
    SHALLOW = 1
    MID = 2
    DEEP = 3
    ABYSSAL = 4


# bands within 1 = visible-but-faded; >= 2 = hidden
ADJACENT_BAND_FADE = 0.5
SAME_BAND_OPACITY = 1.0


@dataclasses.dataclass(frozen=True)
class UnderwaterEntity:
    entity_id: str
    band: DepthBand
    x: float
    y: float
    kind: str   # "sub", "ship", "wreck", "kraken", etc


@dataclasses.dataclass(frozen=True)
class VisibleContact:
    entity_id: str
    band: DepthBand
    x: float
    y: float
    kind: str
    fade_factor: float


@dataclasses.dataclass
class UnderwaterMinimap:
    _entities: dict[str, UnderwaterEntity] = dataclasses.field(
        default_factory=dict,
    )

    def register(
        self, *, entity_id: str,
        band: DepthBand,
        x: float, y: float,
        kind: str,
    ) -> bool:
        if not entity_id:
            return False
        self._entities[entity_id] = UnderwaterEntity(
            entity_id=entity_id, band=band, x=x, y=y, kind=kind,
        )
        return True

    def update_position(
        self, *, entity_id: str,
        band: DepthBand,
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
        self, *, player_band: DepthBand,
    ) -> tuple[VisibleContact, ...]:
        out: list[VisibleContact] = []
        for ent in self._entities.values():
            band_gap = abs(int(ent.band) - int(player_band))
            if band_gap == 0:
                fade = SAME_BAND_OPACITY
            elif band_gap == 1:
                fade = ADJACENT_BAND_FADE
            else:
                continue
            out.append(VisibleContact(
                entity_id=ent.entity_id,
                band=ent.band,
                x=ent.x, y=ent.y,
                kind=ent.kind,
                fade_factor=fade,
            ))
        return tuple(out)

    def depth_of(
        self, *, entity_id: str,
    ) -> t.Optional[DepthBand]:
        ent = self._entities.get(entity_id)
        return ent.band if ent else None


__all__ = [
    "DepthBand", "UnderwaterEntity", "VisibleContact",
    "UnderwaterMinimap",
    "ADJACENT_BAND_FADE", "SAME_BAND_OPACITY",
]
