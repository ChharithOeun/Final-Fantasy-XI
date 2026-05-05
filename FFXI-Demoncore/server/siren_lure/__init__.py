"""Siren lure — mermaid NPC song system that pulls ships off lane.

Sirens (the SILMARIL_SIRENHALL mermaid NPCs and their renegade
splinter cells) sing across the surface and divert hapless
crews into pirate ambush zones — most commonly into the
WRECKAGE_GRAVEYARD where SUNKEN_CROWN pirates are waiting.

This module models the SONG → LURE_ROLL → DIVERT pipeline:

    1. A siren CASTS a song along a naval lane (zone -> zone).
    2. Each ship that crosses the lane during the song window
       rolls a LURE check (resist_score vs siren_power).
    3. A failed roll means the ship is DIVERTED to the lure's
       trap_zone instead of the destination. The diverted ship
       can then be picked up by sea_pirate_factions for an
       encounter — that's the "missing ship" loop.

The song has POWER tiers (whisper / chord / hymn / requiem)
and a CHARM_DURATION; sirens can hold a song open for a
limited time before exhaustion. Each siren has a personal
SIREN_LIBRARY of songs already learned.

Public surface
--------------
    SongPower enum     WHISPER / CHORD / HYMN / REQUIEM
    LureKind enum      DIVERT / BECALM / SHIPWRECK
    SongProfile dataclass
    LureCast dataclass
    LureResult dataclass
    SirenLureSystem
        .cast_song(siren_id, song, lane_zone_id, trap_zone_id,
                   now_seconds)
        .resolve_ship_passage(siren_id, ship_resist, lure_roll,
                              now_seconds)
        .active_songs(siren_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SongPower(str, enum.Enum):
    WHISPER = "whisper"
    CHORD = "chord"
    HYMN = "hymn"
    REQUIEM = "requiem"


class LureKind(str, enum.Enum):
    DIVERT = "divert"
    BECALM = "becalm"
    SHIPWRECK = "shipwreck"


@dataclasses.dataclass(frozen=True)
class SongProfile:
    power: SongPower
    base_strength: int       # used vs ship_resist
    duration_seconds: int    # how long one cast holds
    cooldown_seconds: int    # before the same siren can recast
    typical_lure: LureKind


_SONGS: dict[SongPower, SongProfile] = {
    SongPower.WHISPER: SongProfile(
        power=SongPower.WHISPER,
        base_strength=20,
        duration_seconds=120,
        cooldown_seconds=60,
        typical_lure=LureKind.DIVERT,
    ),
    SongPower.CHORD: SongProfile(
        power=SongPower.CHORD,
        base_strength=45,
        duration_seconds=300,
        cooldown_seconds=180,
        typical_lure=LureKind.DIVERT,
    ),
    SongPower.HYMN: SongProfile(
        power=SongPower.HYMN,
        base_strength=80,
        duration_seconds=600,
        cooldown_seconds=900,
        typical_lure=LureKind.BECALM,
    ),
    SongPower.REQUIEM: SongProfile(
        power=SongPower.REQUIEM,
        base_strength=140,
        duration_seconds=900,
        cooldown_seconds=3_600,
        typical_lure=LureKind.SHIPWRECK,
    ),
}


@dataclasses.dataclass
class LureCast:
    siren_id: str
    power: SongPower
    lane_zone_id: str
    trap_zone_id: str
    started_at: int
    expires_at: int


@dataclasses.dataclass(frozen=True)
class LureResult:
    accepted: bool
    diverted: bool = False
    trap_zone_id: t.Optional[str] = None
    lure_kind: t.Optional[LureKind] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SirenLureSystem:
    _casts: dict[str, list[LureCast]] = dataclasses.field(default_factory=dict)
    _last_cast_end: dict[str, int] = dataclasses.field(default_factory=dict)

    def song_profile(self, *, power: SongPower) -> t.Optional[SongProfile]:
        return _SONGS.get(power)

    def cast_song(
        self, *, siren_id: str,
        power: SongPower,
        lane_zone_id: str,
        trap_zone_id: str,
        now_seconds: int,
    ) -> bool:
        prof = _SONGS.get(power)
        if prof is None or not siren_id:
            return False
        if not lane_zone_id or not trap_zone_id:
            return False
        if lane_zone_id == trap_zone_id:
            return False
        # cooldown: cannot recast while previous song or cooldown is alive
        if siren_id in self._last_cast_end:
            last_end = self._last_cast_end[siren_id]
            if now_seconds < last_end + prof.cooldown_seconds:
                return False
        cast = LureCast(
            siren_id=siren_id,
            power=power,
            lane_zone_id=lane_zone_id,
            trap_zone_id=trap_zone_id,
            started_at=now_seconds,
            expires_at=now_seconds + prof.duration_seconds,
        )
        self._casts.setdefault(siren_id, []).append(cast)
        self._last_cast_end[siren_id] = cast.expires_at
        return True

    def active_songs(
        self, *, siren_id: str, now_seconds: int,
    ) -> tuple[LureCast, ...]:
        casts = self._casts.get(siren_id, [])
        return tuple(c for c in casts if c.expires_at > now_seconds)

    def resolve_ship_passage(
        self, *, siren_id: str,
        ship_resist: int,
        lure_roll: int,
        now_seconds: int,
    ) -> LureResult:
        if ship_resist < 0 or lure_roll < 0:
            return LureResult(False, reason="invalid ship metrics")
        active = self.active_songs(
            siren_id=siren_id, now_seconds=now_seconds,
        )
        if not active:
            return LureResult(False, reason="no active song")
        # use the strongest active song
        cast = max(active, key=lambda c: _SONGS[c.power].base_strength)
        prof = _SONGS[cast.power]
        # if siren_power + lure_roll <= ship_resist => ship slips by
        if prof.base_strength + lure_roll <= ship_resist:
            return LureResult(accepted=True, diverted=False)
        return LureResult(
            accepted=True,
            diverted=True,
            trap_zone_id=cast.trap_zone_id,
            lure_kind=prof.typical_lure,
        )

    def total_song_powers(self) -> int:
        return len(_SONGS)


__all__ = [
    "SongPower", "LureKind", "SongProfile",
    "LureCast", "LureResult",
    "SirenLureSystem",
]
