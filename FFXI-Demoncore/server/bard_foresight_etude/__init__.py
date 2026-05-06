"""Bard Foresight Etude — a BRD song granting telegraph visibility.

A new song joining the BRD song catalog. Like other BRD
songs, it consumes a SONG SLOT (max 2 base, +1 with
Soul Voice / Troubadour gear), follows the song-recast
rules, and lasts the standard song duration. The
distinct effect: every party member who hears the song
gains BARD_FORESIGHT visibility — they see boss
telegraphs as long as the song is up.

There are TWO versions of the song:
    SCHERZO_OF_FORESIGHT  short, 60-second song,
                          radius 16 yalms (party only)
    BALLAD_OF_FORESIGHT   long, 180-second song,
                          radius 20 yalms (alliance,
                          but consumes 2 song slots)

Casting respects standard BRD rules:
    - Bard's job required (subjob 50% effect, but full
      duration)
    - Mandatory recast 8s between any songs
    - Existing copy of same song refreshes (doesn't take
      a new slot)
    - Singing while moving uses standard Mobile Casting
      rules

This module owns the active-song ledger and ticks the
visibility grants. Other modules can call
on_song_dispelled() when the song is silenced.

Public surface
--------------
    EtudeKind enum
    EtudeSong dataclass (mutable)
    SingResult dataclass (frozen)
    BardForesightEtude
        .sing(bard_id, kind, now_seconds, has_subjob_only=False)
            -> SingResult
        .tick(song_id, now_seconds,
              listeners_in_radius, gate)
        .dispel(song_id, reason)
        .active_songs(bard_id) -> tuple[EtudeSong, ...]
        .listener_count(song_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.telegraph_visibility_gate import (
    TelegraphVisibilityGate, VisibilitySource,
)


class EtudeKind(str, enum.Enum):
    SCHERZO_OF_FORESIGHT = "scherzo_of_foresight"
    BALLAD_OF_FORESIGHT = "ballad_of_foresight"


# Profile per kind: (duration_seconds, radius, slots_consumed,
#                    base_grant_per_tick_seconds)
@dataclasses.dataclass(frozen=True)
class _Profile:
    duration_seconds: int
    radius_yalms: int
    slots_consumed: int
    grant_extension_seconds: int


_PROFILES: dict[EtudeKind, _Profile] = {
    EtudeKind.SCHERZO_OF_FORESIGHT: _Profile(
        duration_seconds=60, radius_yalms=16,
        slots_consumed=1, grant_extension_seconds=4,
    ),
    EtudeKind.BALLAD_OF_FORESIGHT: _Profile(
        duration_seconds=180, radius_yalms=20,
        slots_consumed=2, grant_extension_seconds=4,
    ),
}


SONG_RECAST_SECONDS = 8
MAX_SONG_SLOTS = 2
SUBJOB_DURATION_PCT = 50   # subjob BRD has 50% song slot weight


@dataclasses.dataclass
class EtudeSong:
    song_id: str
    bard_id: str
    kind: EtudeKind
    started_at: int
    expires_at: int
    slots_used: int
    dispelled: bool = False
    dispel_reason: t.Optional[str] = None
    listener_ids: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass(frozen=True)
class SingResult:
    accepted: bool
    song_id: str = ""
    kind: t.Optional[EtudeKind] = None
    expires_at: int = 0
    next_song_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BardForesightEtude:
    _songs: dict[str, EtudeSong] = dataclasses.field(
        default_factory=dict,
    )
    _by_bard: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )
    _last_song_at: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def _active_for_bard(
        self, *, bard_id: str, now_seconds: int,
    ) -> list[EtudeSong]:
        ids = self._by_bard.get(bard_id, [])
        out: list[EtudeSong] = []
        for sid in ids:
            s = self._songs.get(sid)
            if s is None:
                continue
            if s.dispelled or now_seconds >= s.expires_at:
                continue
            out.append(s)
        return out

    def sing(
        self, *, bard_id: str, kind: EtudeKind, now_seconds: int,
        has_subjob_only: bool = False,
    ) -> SingResult:
        if not bard_id:
            return SingResult(False, reason="blank bard")
        # recast cooldown
        last = self._last_song_at.get(bard_id, -10**9)
        if (now_seconds - last) < SONG_RECAST_SECONDS:
            return SingResult(
                False, reason="recast",
                next_song_at=last + SONG_RECAST_SECONDS,
            )
        prof = _PROFILES[kind]
        # Check existing same-kind song for refresh
        active = self._active_for_bard(
            bard_id=bard_id, now_seconds=now_seconds,
        )
        for s in active:
            if s.kind == kind:
                # refresh duration
                s.expires_at = now_seconds + prof.duration_seconds
                self._last_song_at[bard_id] = now_seconds
                return SingResult(
                    accepted=True, song_id=s.song_id, kind=kind,
                    expires_at=s.expires_at,
                    next_song_at=now_seconds + SONG_RECAST_SECONDS,
                )
        # Check slot availability
        slots_in_use = sum(s.slots_used for s in active)
        cap = MAX_SONG_SLOTS
        if slots_in_use + prof.slots_consumed > cap:
            return SingResult(
                False, reason="slot cap reached",
            )
        # Sing it
        self._next_id += 1
        sid = f"etude_{self._next_id}"
        duration = prof.duration_seconds
        if has_subjob_only:
            duration = duration * SUBJOB_DURATION_PCT // 100
        s = EtudeSong(
            song_id=sid, bard_id=bard_id, kind=kind,
            started_at=now_seconds,
            expires_at=now_seconds + duration,
            slots_used=prof.slots_consumed,
        )
        self._songs[sid] = s
        self._by_bard.setdefault(bard_id, []).append(sid)
        self._last_song_at[bard_id] = now_seconds
        return SingResult(
            accepted=True, song_id=sid, kind=kind,
            expires_at=s.expires_at,
            next_song_at=now_seconds + SONG_RECAST_SECONDS,
        )

    def tick(
        self, *, song_id: str, now_seconds: int,
        listeners_in_radius: t.Iterable[str],
        gate: TelegraphVisibilityGate,
    ) -> int:
        s = self._songs.get(song_id)
        if s is None or s.dispelled:
            return 0
        if now_seconds >= s.expires_at:
            self._dispel(s, reason="duration_expired")
            return 0
        prof = _PROFILES[s.kind]
        granted = 0
        s.listener_ids.clear()
        for listener in listeners_in_radius:
            if not listener:
                continue
            ok = gate.grant_visibility(
                player_id=listener,
                source=VisibilitySource.BARD_FORESIGHT,
                granted_at=now_seconds,
                expires_at=(
                    now_seconds + prof.grant_extension_seconds
                ),
                granted_by=s.bard_id,
            )
            if ok:
                granted += 1
            s.listener_ids.add(listener)
        return granted

    def _dispel(self, s: EtudeSong, *, reason: str) -> None:
        s.dispelled = True
        s.dispel_reason = reason

    def dispel(
        self, *, song_id: str, reason: str = "manual",
    ) -> bool:
        s = self._songs.get(song_id)
        if s is None or s.dispelled:
            return False
        self._dispel(s, reason=reason)
        return True

    def active_songs(
        self, *, bard_id: str, now_seconds: int = 0,
    ) -> tuple[EtudeSong, ...]:
        return tuple(self._active_for_bard(
            bard_id=bard_id, now_seconds=now_seconds,
        ))

    def listener_count(self, *, song_id: str) -> int:
        s = self._songs.get(song_id)
        return len(s.listener_ids) if s else 0


__all__ = [
    "EtudeKind", "EtudeSong", "SingResult",
    "BardForesightEtude",
    "SONG_RECAST_SECONDS", "MAX_SONG_SLOTS",
    "SUBJOB_DURATION_PCT",
]
