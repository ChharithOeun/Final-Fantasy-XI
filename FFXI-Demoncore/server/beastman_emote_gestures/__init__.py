"""Beastman emote gestures — race-specific emotes & rituals.

Each beastman race has a CULTURAL emote roster — specific
gestures only available to characters of that race (yagudo
WING_FLARE, quadav STONE_BOW, lamia COIL_DANCE, orc ROAR_OF_KIN).
Plus a UNIVERSAL set of emotes (cheer, point, sleep, etc.) that
all races share.

Some race emotes have a RITUAL FLAG — when performed in a
specific zone or near a specific NPC, they may trigger a
secondary effect (a hidden quest cue, a small mood boost,
unlocking a dialogue option).

Public surface
--------------
    EmoteScope enum   UNIVERSAL / YAGUDO / QUADAV / LAMIA / ORC
    Emote dataclass
    BeastmanEmoteGestures
        .register_emote(emote_id, scope, ritual)
        .perform(player_id, race, emote_id, zone_id)
        .available_for(race)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class EmoteScope(str, enum.Enum):
    UNIVERSAL = "universal"
    YAGUDO = "yagudo"
    QUADAV = "quadav"
    LAMIA = "lamia"
    ORC = "orc"


_SCOPE_FOR_RACE: dict[BeastmanRace, EmoteScope] = {
    BeastmanRace.YAGUDO: EmoteScope.YAGUDO,
    BeastmanRace.QUADAV: EmoteScope.QUADAV,
    BeastmanRace.LAMIA: EmoteScope.LAMIA,
    BeastmanRace.ORC: EmoteScope.ORC,
}


@dataclasses.dataclass(frozen=True)
class Emote:
    emote_id: str
    scope: EmoteScope
    ritual_zone_id: t.Optional[str] = None
    ritual_payload: str = ""


@dataclasses.dataclass(frozen=True)
class PerformResult:
    accepted: bool
    emote_id: str
    triggered_ritual: bool = False
    ritual_payload: str = ""
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanEmoteGestures:
    _emotes: dict[str, Emote] = dataclasses.field(default_factory=dict)

    def register_emote(
        self, *, emote_id: str,
        scope: EmoteScope,
        ritual_zone_id: t.Optional[str] = None,
        ritual_payload: str = "",
    ) -> t.Optional[Emote]:
        if not emote_id:
            return None
        if emote_id in self._emotes:
            return None
        # ritual_payload only meaningful with a ritual_zone_id
        if ritual_payload and not ritual_zone_id:
            return None
        e = Emote(
            emote_id=emote_id,
            scope=scope,
            ritual_zone_id=ritual_zone_id,
            ritual_payload=ritual_payload,
        )
        self._emotes[emote_id] = e
        return e

    def perform(
        self, *, player_id: str,
        race: BeastmanRace,
        emote_id: str,
        zone_id: str,
    ) -> PerformResult:
        e = self._emotes.get(emote_id)
        if e is None:
            return PerformResult(
                False, emote_id, reason="unknown emote",
            )
        # Scope check
        if e.scope == EmoteScope.UNIVERSAL:
            allowed = True
        else:
            allowed = (
                _SCOPE_FOR_RACE.get(race) == e.scope
            )
        if not allowed:
            return PerformResult(
                False, emote_id, reason="race-locked emote",
            )
        triggered = (
            e.ritual_zone_id is not None
            and zone_id == e.ritual_zone_id
        )
        return PerformResult(
            accepted=True,
            emote_id=emote_id,
            triggered_ritual=triggered,
            ritual_payload=e.ritual_payload if triggered else "",
        )

    def available_for(
        self, *, race: BeastmanRace,
    ) -> tuple[Emote, ...]:
        race_scope = _SCOPE_FOR_RACE.get(race)
        return tuple(
            e for e in self._emotes.values()
            if e.scope == EmoteScope.UNIVERSAL or e.scope == race_scope
        )

    def total_emotes(self) -> int:
        return len(self._emotes)


__all__ = [
    "EmoteScope", "Emote", "PerformResult",
    "BeastmanEmoteGestures",
]
