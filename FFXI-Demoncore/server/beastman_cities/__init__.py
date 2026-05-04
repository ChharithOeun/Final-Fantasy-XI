"""Beastman cities — six city analogues mirroring canon nations.

Six cities: equivalents to San d'Oria, Bastok, Windurst, Jeuno,
Whitegate (Aht Urhgan), and Adoulin — but for the beastman
side. Each city is anchored by a beastman race (or by a mixed
council in the Jeuno-equivalent and Adoulin-equivalent), with
the same service slate (auction house, mog house, mission
giver, conquest tally) but with race-coded NPCs and dialogue.

Public surface
--------------
    CityRole enum
    CityServiceKind enum
    BeastmanCity dataclass
    BeastmanCities
        .register_city(city_id, role, anchor_race, label,
                       services, mission_npc_id)
        .has_service(city_id, service)
        .get(city_id)
        .cities_for_race(race)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class CityRole(str, enum.Enum):
    SAN_DORIA_PARALLEL = "san_doria_parallel"
    BASTOK_PARALLEL = "bastok_parallel"
    WINDURST_PARALLEL = "windurst_parallel"
    JEUNO_PARALLEL = "jeuno_parallel"
    WHITEGATE_PARALLEL = "whitegate_parallel"
    ADOULIN_PARALLEL = "adoulin_parallel"


class CityServiceKind(str, enum.Enum):
    AUCTION_HOUSE = "auction_house"
    MOG_HOUSE = "mog_house"
    MISSION_GIVER = "mission_giver"
    CONQUEST_TALLY = "conquest_tally"
    CRAFTING_GUILD = "crafting_guild"
    HOMEPOINT = "homepoint"
    BAZAAR_PLAZA = "bazaar_plaza"
    BLACK_MARKET = "black_market"
    LIBRARY = "library"
    BARRACKS = "barracks"


# Default service slate per role.
_DEFAULT_SERVICES_BY_ROLE: dict[
    CityRole, frozenset[CityServiceKind],
] = {
    CityRole.SAN_DORIA_PARALLEL: frozenset({
        CityServiceKind.AUCTION_HOUSE,
        CityServiceKind.MOG_HOUSE,
        CityServiceKind.MISSION_GIVER,
        CityServiceKind.CONQUEST_TALLY,
        CityServiceKind.HOMEPOINT,
        CityServiceKind.BARRACKS,
    }),
    CityRole.BASTOK_PARALLEL: frozenset({
        CityServiceKind.AUCTION_HOUSE,
        CityServiceKind.MOG_HOUSE,
        CityServiceKind.MISSION_GIVER,
        CityServiceKind.CONQUEST_TALLY,
        CityServiceKind.HOMEPOINT,
        CityServiceKind.CRAFTING_GUILD,
    }),
    CityRole.WINDURST_PARALLEL: frozenset({
        CityServiceKind.AUCTION_HOUSE,
        CityServiceKind.MOG_HOUSE,
        CityServiceKind.MISSION_GIVER,
        CityServiceKind.CONQUEST_TALLY,
        CityServiceKind.HOMEPOINT,
        CityServiceKind.LIBRARY,
    }),
    CityRole.JEUNO_PARALLEL: frozenset({
        CityServiceKind.AUCTION_HOUSE,
        CityServiceKind.MOG_HOUSE,
        CityServiceKind.MISSION_GIVER,
        CityServiceKind.HOMEPOINT,
        CityServiceKind.BAZAAR_PLAZA,
        CityServiceKind.CRAFTING_GUILD,
        CityServiceKind.LIBRARY,
    }),
    CityRole.WHITEGATE_PARALLEL: frozenset({
        CityServiceKind.AUCTION_HOUSE,
        CityServiceKind.MOG_HOUSE,
        CityServiceKind.MISSION_GIVER,
        CityServiceKind.HOMEPOINT,
        CityServiceKind.BAZAAR_PLAZA,
        CityServiceKind.BLACK_MARKET,
    }),
    CityRole.ADOULIN_PARALLEL: frozenset({
        CityServiceKind.AUCTION_HOUSE,
        CityServiceKind.MOG_HOUSE,
        CityServiceKind.MISSION_GIVER,
        CityServiceKind.HOMEPOINT,
        CityServiceKind.CRAFTING_GUILD,
        CityServiceKind.LIBRARY,
        CityServiceKind.BARRACKS,
    }),
}


@dataclasses.dataclass(frozen=True)
class BeastmanCity:
    city_id: str
    role: CityRole
    label: str
    anchor_race: t.Optional[BeastmanRace]    # None for mixed-council cities
    mission_npc_id: str
    services: frozenset[CityServiceKind]


@dataclasses.dataclass
class BeastmanCities:
    _cities: dict[str, BeastmanCity] = dataclasses.field(
        default_factory=dict,
    )

    def register_city(
        self, *, city_id: str, role: CityRole,
        label: str,
        anchor_race: t.Optional[BeastmanRace],
        mission_npc_id: str,
        services: t.Optional[
            frozenset[CityServiceKind]
        ] = None,
    ) -> t.Optional[BeastmanCity]:
        if city_id in self._cities:
            return None
        # Each role can only be claimed by one city
        for c in self._cities.values():
            if c.role == role:
                return None
        if not mission_npc_id:
            return None
        svc = (
            services
            if services is not None
            else _DEFAULT_SERVICES_BY_ROLE[role]
        )
        city = BeastmanCity(
            city_id=city_id, role=role, label=label,
            anchor_race=anchor_race,
            mission_npc_id=mission_npc_id,
            services=svc,
        )
        self._cities[city_id] = city
        return city

    def get(
        self, city_id: str,
    ) -> t.Optional[BeastmanCity]:
        return self._cities.get(city_id)

    def by_role(
        self, role: CityRole,
    ) -> t.Optional[BeastmanCity]:
        for c in self._cities.values():
            if c.role == role:
                return c
        return None

    def has_service(
        self, *, city_id: str,
        service: CityServiceKind,
    ) -> bool:
        c = self._cities.get(city_id)
        if c is None:
            return False
        return service in c.services

    def cities_for_race(
        self, race: BeastmanRace,
    ) -> tuple[BeastmanCity, ...]:
        return tuple(
            c for c in self._cities.values()
            if c.anchor_race == race
        )

    def total_cities(self) -> int:
        return len(self._cities)


__all__ = [
    "CityRole", "CityServiceKind",
    "BeastmanCity",
    "BeastmanCities",
]
