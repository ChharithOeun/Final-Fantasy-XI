"""Cloud landmarks — discoverable aerial POIs.

Mirrors seafloor_landmarks but in the sky. Once a player
flies within DISCOVERY_RADIUS at the matching altitude
band, the landmark joins their personal aerial map.

LandmarkKind:
    CLOUD_CITY      — floating city ruins / sky port
    SKY_SHRINE      — vana'diel god monument
    FLOATING_RUIN   — ancient dragon-clan ruin
    WEATHER_PILLAR  — magic spire that anchors weather
    JET_GATE        — entrance to a STRATOSPHERE jet stream

Public surface
--------------
    LandmarkKind enum
    Landmark dataclass (frozen)
    CloudLandmarks
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
    CLOUD_CITY = "cloud_city"
    SKY_SHRINE = "sky_shrine"
    FLOATING_RUIN = "floating_ruin"
    WEATHER_PILLAR = "weather_pillar"
    JET_GATE = "jet_gate"


# horizontal-units; band must match for discovery
DISCOVERY_RADIUS = 80.0


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
class CloudLandmarks:
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
    "LandmarkKind", "Landmark", "CloudLandmarks",
    "DISCOVERY_RADIUS",
]
