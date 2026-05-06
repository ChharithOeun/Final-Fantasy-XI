"""Game tracking — reading the wilderness like a book.

A footprint in mud, a tuft of fur on a thorn bush, a
pile of scat — to a trained hunter these are sentences.
This module turns environmental signs into a perception
mini-game: spot a sign, roll your tracking skill, learn
something useful about the quarry.

Sign categories
---------------
    PAW_PRINT      tracks pressed into ground
    SCAT           droppings (age + diet readable)
    BLOOD_SPOT     wounded prey trail
    FUR_TUFT       caught on branch / brush
    DISTURBED_BRUSH bent grass / broken twigs
    KILL_SITE      previous kill remnants

Each sign carries an opaque quarry_id (which species), a
freshness_seconds (how long ago the animal passed), and
a difficulty (how hard to read). Calling read(sign_id,
tracker_skill) returns a TrackingReading with the bits
the hunter manages to glean — better skill reveals more
fields, weak skill might reveal nothing or even mislead
on direction.

This is intentionally a pure-data engine — caller is
responsible for converting "I learned that a tarutaru-sized
animal passed here heading north 4 minutes ago" into a UI
hint or NPC dialogue.

Public surface
--------------
    SignKind enum
    Sign dataclass (mutable — freshness ages)
    TrackingReading dataclass (frozen)
    GameTrackingRegistry
        .place_sign(sign_id, kind, zone, x, y,
                    quarry_id, freshness_seconds,
                    difficulty, direction_bearing) -> bool
        .age_signs(dt_seconds) -> int  (count of expired)
        .signs_in_zone(zone) -> list[Sign]
        .read(sign_id, tracker_skill) -> Optional[TrackingReading]
        .remove(sign_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SignKind(str, enum.Enum):
    PAW_PRINT = "paw_print"
    SCAT = "scat"
    BLOOD_SPOT = "blood_spot"
    FUR_TUFT = "fur_tuft"
    DISTURBED_BRUSH = "disturbed_brush"
    KILL_SITE = "kill_site"


# A sign that ages past this is too old to read at all.
_MAX_AGE_SECONDS = 3 * 24 * 3600   # 3 days


@dataclasses.dataclass
class Sign:
    sign_id: str
    kind: SignKind
    zone: str
    x: float
    y: float
    quarry_id: str
    freshness_seconds: int
    difficulty: int       # 0..100, higher = harder
    direction_bearing: int  # 0..359 degrees compass


@dataclasses.dataclass(frozen=True)
class TrackingReading:
    sign_id: str
    quarry_revealed: bool       # got the species
    freshness_revealed: bool    # got how long ago
    direction_revealed: bool    # got which way they went
    direction_misled: bool      # off-by-180 false positive


@dataclasses.dataclass
class GameTrackingRegistry:
    _signs: dict[str, Sign] = dataclasses.field(
        default_factory=dict,
    )

    def place_sign(
        self, *, sign_id: str, kind: SignKind,
        zone: str, x: float, y: float,
        quarry_id: str, freshness_seconds: int,
        difficulty: int, direction_bearing: int,
    ) -> bool:
        if not sign_id or not zone or not quarry_id:
            return False
        if sign_id in self._signs:
            return False
        if difficulty < 0 or difficulty > 100:
            return False
        if freshness_seconds < 0:
            return False
        bearing = direction_bearing % 360
        self._signs[sign_id] = Sign(
            sign_id=sign_id, kind=kind, zone=zone,
            x=x, y=y, quarry_id=quarry_id,
            freshness_seconds=freshness_seconds,
            difficulty=difficulty,
            direction_bearing=bearing,
        )
        return True

    def age_signs(self, *, dt_seconds: int) -> int:
        if dt_seconds <= 0:
            return 0
        expired: list[str] = []
        for sid, s in self._signs.items():
            s.freshness_seconds += dt_seconds
            if s.freshness_seconds >= _MAX_AGE_SECONDS:
                expired.append(sid)
        for sid in expired:
            del self._signs[sid]
        return len(expired)

    def signs_in_zone(self, *, zone: str) -> list[Sign]:
        return [s for s in self._signs.values() if s.zone == zone]

    def read(
        self, *, sign_id: str, tracker_skill: int,
    ) -> t.Optional[TrackingReading]:
        s = self._signs.get(sign_id)
        if s is None:
            return None
        # margin = how much your skill exceeds the difficulty
        margin = tracker_skill - s.difficulty
        # quarry species: easiest to determine
        quarry_ok = margin >= -10
        # freshness: middle difficulty
        fresh_ok = margin >= 0
        # direction: hardest, and risk of misleading
        dir_ok = margin >= 15
        misled = (margin < -10) and not dir_ok
        return TrackingReading(
            sign_id=sign_id,
            quarry_revealed=quarry_ok,
            freshness_revealed=fresh_ok,
            direction_revealed=dir_ok,
            direction_misled=misled,
        )

    def remove(self, *, sign_id: str) -> bool:
        if sign_id not in self._signs:
            return False
        del self._signs[sign_id]
        return True

    def total_signs(self) -> int:
        return len(self._signs)


__all__ = [
    "SignKind", "Sign", "TrackingReading",
    "GameTrackingRegistry",
]
