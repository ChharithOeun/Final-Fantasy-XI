"""Player birdwatching — life-list of species spotted across zones.

Birdwatchers spot bird species in specific zones at specific
times of day. Each species has a rarity tier (1 common .. 5
legendary). Spotting a new species adds it to the player's
life-list; duplicate sightings accumulate observation_hours
but don't grow the list. Life-list size + rarity-weighted
total drives birdwatcher fame.

Lifecycle (per sighting)
    sighting recorded -> life-list updated if new

Public surface
--------------
    Rarity enum
    TimeOfDay enum
    Species dataclass (frozen)
    Sighting dataclass (frozen)
    PlayerBirdwatchingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_RARITY_FAME_VALUE = {
    1: 1,    # common
    2: 3,
    3: 7,
    4: 15,
    5: 40,   # legendary
}


class Rarity(int, enum.Enum):
    COMMON = 1
    UNCOMMON = 2
    RARE = 3
    VERY_RARE = 4
    LEGENDARY = 5


class TimeOfDay(str, enum.Enum):
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"


@dataclasses.dataclass(frozen=True)
class Species:
    species_id: str
    common_name: str
    rarity: Rarity
    preferred_zones: tuple[str, ...]
    active_times: tuple[TimeOfDay, ...]


@dataclasses.dataclass(frozen=True)
class Sighting:
    sighting_id: str
    watcher_id: str
    species_id: str
    zone_id: str
    time_of_day: TimeOfDay
    observed_day: int


@dataclasses.dataclass
class _WState:
    life_list: set[str] = dataclasses.field(
        default_factory=set,
    )
    observation_hours: int = 0


@dataclasses.dataclass
class PlayerBirdwatchingSystem:
    _species: dict[str, Species] = dataclasses.field(
        default_factory=dict,
    )
    _sightings: dict[str, Sighting] = dataclasses.field(
        default_factory=dict,
    )
    _watchers: dict[str, _WState] = dataclasses.field(
        default_factory=dict,
    )
    _next_sighting: int = 1

    def register_species(
        self, *, species_id: str, common_name: str,
        rarity: Rarity,
        preferred_zones: tuple[str, ...],
        active_times: tuple[TimeOfDay, ...],
    ) -> bool:
        if not species_id or species_id in self._species:
            return False
        if not common_name:
            return False
        if not preferred_zones or not active_times:
            return False
        self._species[species_id] = Species(
            species_id=species_id,
            common_name=common_name, rarity=rarity,
            preferred_zones=preferred_zones,
            active_times=active_times,
        )
        return True

    def spot_bird(
        self, *, watcher_id: str, species_id: str,
        zone_id: str, time_of_day: TimeOfDay,
        observed_day: int,
    ) -> t.Optional[str]:
        """Record a sighting. Must match species'
        zone+time biology — out-of-context sightings
        are rejected as misidentifications.
        """
        if not watcher_id:
            return None
        if species_id not in self._species:
            return None
        if observed_day < 0:
            return None
        sp = self._species[species_id]
        if zone_id not in sp.preferred_zones:
            return None
        if time_of_day not in sp.active_times:
            return None
        sid = f"sight_{self._next_sighting}"
        self._next_sighting += 1
        self._sightings[sid] = Sighting(
            sighting_id=sid, watcher_id=watcher_id,
            species_id=species_id, zone_id=zone_id,
            time_of_day=time_of_day,
            observed_day=observed_day,
        )
        if watcher_id not in self._watchers:
            self._watchers[watcher_id] = _WState()
        st = self._watchers[watcher_id]
        st.life_list.add(species_id)
        st.observation_hours += 1
        return sid

    def life_list(
        self, *, watcher_id: str,
    ) -> list[str]:
        st = self._watchers.get(watcher_id)
        if st is None:
            return []
        return sorted(st.life_list)

    def fame_score(
        self, *, watcher_id: str,
    ) -> int:
        st = self._watchers.get(watcher_id)
        if st is None:
            return 0
        return sum(
            _RARITY_FAME_VALUE[
                self._species[sp_id].rarity.value
            ]
            for sp_id in st.life_list
        )

    def observation_hours(
        self, *, watcher_id: str,
    ) -> int:
        st = self._watchers.get(watcher_id)
        return 0 if st is None else st.observation_hours

    def species(
        self, *, species_id: str,
    ) -> t.Optional[Species]:
        return self._species.get(species_id)

    def sightings_by_watcher(
        self, *, watcher_id: str,
    ) -> list[Sighting]:
        return [
            s for s in self._sightings.values()
            if s.watcher_id == watcher_id
        ]


__all__ = [
    "Rarity", "TimeOfDay", "Species", "Sighting",
    "PlayerBirdwatchingSystem",
]
