"""Seafloor landmarks — discoverable underwater POIs.

Surface FFXI shows you everything on the map. Underwater
the world is hidden by default; you have to swim through it.
Landmarks (wrecks, vents, kelp, ruins, abyss spires) only
appear on a player's underwater minimap once they've been
within DISCOVERY_RADIUS of the actual landmark. After that
they stay visible forever, with the lore_blurb available
on hover.

This is the "fog of war" mechanic for the deep — exploration
has lasting value because the map you build is a *trophy
case* of where you've actually been.

Public surface
--------------
    LandmarkKind enum
    Landmark dataclass (frozen)
    SeafloorLandmarks
        .register(landmark_id, name, kind, x, y, band, lore_blurb)
        .check_discovery(player_id, x, y, band, now_seconds)
            -> tuple of newly discovered landmarks
        .discovered_for(player_id) -> tuple[Landmark, ...]
        .is_discovered(player_id, landmark_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class LandmarkKind(str, enum.Enum):
    WRECK = "wreck"
    HYDROTHERMAL_VENT = "hydrothermal_vent"
    KELP_FOREST = "kelp_forest"
    RUIN = "ruin"
    ABYSS_SPIRE = "abyss_spire"


# horizontal-units; band must match for discovery
DISCOVERY_RADIUS = 50.0


@dataclasses.dataclass(frozen=True)
class Landmark:
    landmark_id: str
    name: str
    kind: LandmarkKind
    x: float
    y: float
    band: int
    lore_blurb: str


@dataclasses.dataclass
class SeafloorLandmarks:
    _landmarks: dict[str, Landmark] = dataclasses.field(default_factory=dict)
    # player_id -> {landmark_id: discovered_at_seconds}
    _discoveries: dict[str, dict[str, int]] = dataclasses.field(
        default_factory=dict,
    )

    def register(
        self, *, landmark_id: str,
        name: str,
        kind: LandmarkKind,
        x: float, y: float, band: int,
        lore_blurb: str = "",
    ) -> bool:
        if not landmark_id or not name:
            return False
        self._landmarks[landmark_id] = Landmark(
            landmark_id=landmark_id, name=name,
            kind=kind, x=x, y=y, band=band,
            lore_blurb=lore_blurb,
        )
        return True

    def check_discovery(
        self, *, player_id: str,
        x: float, y: float, band: int,
        now_seconds: int,
    ) -> tuple[Landmark, ...]:
        discovered = self._discoveries.setdefault(player_id, {})
        newly: list[Landmark] = []
        for lm in self._landmarks.values():
            if lm.landmark_id in discovered:
                continue
            if lm.band != band:
                continue
            d = math.sqrt(
                (lm.x - x) ** 2 + (lm.y - y) ** 2,
            )
            if d <= DISCOVERY_RADIUS:
                discovered[lm.landmark_id] = now_seconds
                newly.append(lm)
        return tuple(newly)

    def discovered_for(
        self, *, player_id: str,
    ) -> tuple[Landmark, ...]:
        ids = self._discoveries.get(player_id, {})
        out = [
            self._landmarks[lid]
            for lid in ids
            if lid in self._landmarks
        ]
        return tuple(out)

    def is_discovered(
        self, *, player_id: str, landmark_id: str,
    ) -> bool:
        return landmark_id in self._discoveries.get(player_id, {})


__all__ = [
    "LandmarkKind", "Landmark", "SeafloorLandmarks",
    "DISCOVERY_RADIUS",
]
