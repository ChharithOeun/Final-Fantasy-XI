"""Beastman jukebox — beastman lair music selector.

Per-player music catalog, with TRACKS unlocked through gameplay
events (raid first-clears, season closes, festival rewards).
Each lair has ONE active track at a time. Tracks have a RACE
TINT — preferring tracks of your own race triggers a small +1%
mood bonus while in the lair.

Public surface
--------------
    TrackTint enum   YAGUDO / QUADAV / LAMIA / ORC / NEUTRAL
    Track dataclass
    BeastmanJukebox
        .register_track(track_id, name, tint)
        .unlock(player_id, track_id)
        .set_active(player_id, track_id)
        .active_for(player_id)
        .unlocked_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TrackTint(str, enum.Enum):
    YAGUDO = "yagudo"
    QUADAV = "quadav"
    LAMIA = "lamia"
    ORC = "orc"
    NEUTRAL = "neutral"


@dataclasses.dataclass(frozen=True)
class Track:
    track_id: str
    name: str
    tint: TrackTint


@dataclasses.dataclass(frozen=True)
class SetActiveResult:
    accepted: bool
    track_id: str = ""
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanJukebox:
    _catalog: dict[str, Track] = dataclasses.field(default_factory=dict)
    _unlocked: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    _active: dict[str, str] = dataclasses.field(default_factory=dict)

    def register_track(
        self, *, track_id: str, name: str, tint: TrackTint,
    ) -> t.Optional[Track]:
        if track_id in self._catalog:
            return None
        if not track_id or not name:
            return None
        t_obj = Track(track_id=track_id, name=name, tint=tint)
        self._catalog[track_id] = t_obj
        return t_obj

    def unlock(
        self, *, player_id: str, track_id: str,
    ) -> bool:
        if track_id not in self._catalog:
            return False
        roster = self._unlocked.setdefault(player_id, set())
        if track_id in roster:
            return False
        roster.add(track_id)
        return True

    def is_unlocked(
        self, *, player_id: str, track_id: str,
    ) -> bool:
        return track_id in self._unlocked.get(player_id, set())

    def set_active(
        self, *, player_id: str, track_id: str,
    ) -> SetActiveResult:
        if track_id not in self._catalog:
            return SetActiveResult(
                False, reason="unknown track",
            )
        if not self.is_unlocked(
            player_id=player_id, track_id=track_id,
        ):
            return SetActiveResult(
                False, track_id, reason="not unlocked",
            )
        self._active[player_id] = track_id
        return SetActiveResult(accepted=True, track_id=track_id)

    def active_for(
        self, *, player_id: str,
    ) -> t.Optional[Track]:
        tid = self._active.get(player_id)
        if tid is None:
            return None
        return self._catalog.get(tid)

    def unlocked_for(
        self, *, player_id: str,
    ) -> tuple[Track, ...]:
        roster = self._unlocked.get(player_id, set())
        return tuple(
            self._catalog[t] for t in sorted(roster)
            if t in self._catalog
        )

    def total_tracks(self) -> int:
        return len(self._catalog)


__all__ = [
    "TrackTint", "Track", "SetActiveResult",
    "BeastmanJukebox",
]
