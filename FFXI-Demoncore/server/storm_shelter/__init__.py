"""Storm shelter — NPCs flee to cover when storms intensify.

Civilian NPCs head for shelter when intensity ≥ a per-NPC
threshold. Some NPCs are storm-fearless (sailors, hunters).
Mob populations may also scatter — wild beasts retreat to
dens during blizzards and thunderstorms. This module
computes shelter intent given current weather, but doesn't
move entities itself.

Public surface
--------------
    ShelterIntent enum
    NpcStormProfile dataclass (frozen)
    StormShelterEngine
        .register_npc(npc_id, fear_threshold, fearless,
                      preferred_shelter_id) -> bool
        .check_npc(npc_id, current_intensity, weather_kind)
            -> ShelterIntent
        .npcs_at_shelter(shelter_id) -> tuple[str, ...]
        .clear_shelter(npc_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ShelterIntent(str, enum.Enum):
    NONE = "none"               # no fear, stay outside
    SEEK_SHELTER = "seek_shelter"
    AT_SHELTER = "at_shelter"
    UNKNOWN_NPC = "unknown_npc"


# only these weather kinds drive shelter behavior
_SHELTER_WORTHY = {
    "thunderstorm", "blizzard", "sandstorm",
}


@dataclasses.dataclass(frozen=True)
class NpcStormProfile:
    npc_id: str
    fear_threshold: int      # 0..100; storms ≥ this trigger flight
    fearless: bool
    preferred_shelter_id: str


@dataclasses.dataclass
class StormShelterEngine:
    _profiles: dict[str, NpcStormProfile] = dataclasses.field(
        default_factory=dict,
    )
    # npc_id -> shelter_id when at shelter
    _at_shelter: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def register_npc(
        self, *, npc_id: str, fear_threshold: int,
        fearless: bool = False,
        preferred_shelter_id: str = "",
    ) -> bool:
        if not npc_id:
            return False
        if fear_threshold < 0 or fear_threshold > 100:
            return False
        if npc_id in self._profiles:
            return False
        self._profiles[npc_id] = NpcStormProfile(
            npc_id=npc_id, fear_threshold=fear_threshold,
            fearless=fearless,
            preferred_shelter_id=preferred_shelter_id,
        )
        return True

    def check_npc(
        self, *, npc_id: str, current_intensity: int,
        weather_kind: str,
    ) -> ShelterIntent:
        prof = self._profiles.get(npc_id)
        if prof is None:
            return ShelterIntent.UNKNOWN_NPC
        if prof.fearless:
            return ShelterIntent.NONE
        if weather_kind not in _SHELTER_WORTHY:
            # weather not threatening — leave shelter if at one
            if npc_id in self._at_shelter:
                del self._at_shelter[npc_id]
            return ShelterIntent.NONE
        if current_intensity < prof.fear_threshold:
            if npc_id in self._at_shelter:
                del self._at_shelter[npc_id]
            return ShelterIntent.NONE
        # storm is bad enough → flee
        if npc_id in self._at_shelter:
            return ShelterIntent.AT_SHELTER
        # mark them as at shelter (flow-state simplification)
        if prof.preferred_shelter_id:
            self._at_shelter[npc_id] = prof.preferred_shelter_id
            return ShelterIntent.AT_SHELTER
        return ShelterIntent.SEEK_SHELTER

    def npcs_at_shelter(
        self, *, shelter_id: str,
    ) -> tuple[str, ...]:
        return tuple(sorted(
            npc for npc, sh in self._at_shelter.items()
            if sh == shelter_id
        ))

    def clear_shelter(self, *, npc_id: str) -> bool:
        if npc_id in self._at_shelter:
            del self._at_shelter[npc_id]
            return True
        return False

    def total_npcs(self) -> int:
        return len(self._profiles)


__all__ = [
    "ShelterIntent", "NpcStormProfile", "StormShelterEngine",
]
