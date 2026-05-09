"""Beastman officer roster — RoTK officer layer for beastman races.

Mirrors nation_officer_roster but for beastman cities
(Yhoator, Pso'Xja, Davoi, etc.). Beastman races have
the same five stats — martial / intellect / leadership
/ charisma / loyalty — but each race carries a RACIAL
TRAIT modifier the caller can apply to derived rolls.

Beastman officers can be recruited by HUME nations and
vice-versa, with a cross-faction friction multiplier
that penalizes loyalty drift the longer they're out
of their racial home (delegated; this module exposes
race + days_in_foreign_service so the caller can
compute the penalty).

Public surface
--------------
    BeastmanRace enum (8 canonical races)
    Trait enum (innate racial bias)
    BeastmanStatus enum
    BeastmanStats dataclass (frozen)
    BeastmanOfficer dataclass (frozen)
    BeastmanOfficerRosterSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BeastmanRace(str, enum.Enum):
    ORC = "orc"
    QUADAV = "quadav"
    YAGUDO = "yagudo"
    GOBLIN = "goblin"
    KINDRED = "kindred"
    SAHAGIN = "sahagin"
    TONBERRY = "tonberry"
    MOBLIN = "moblin"


class Trait(str, enum.Enum):
    BERSERKER = "berserker"      # +martial, -intellect
    SHAMAN = "shaman"            # +intellect, -martial
    WARLORD = "warlord"          # +leadership
    ZEALOT = "zealot"            # +loyalty
    TRADER = "trader"            # +charisma
    ASSASSIN = "assassin"        # +intellect+martial
    HONORBOUND = "honorbound"    # +loyalty++
    OUTCAST = "outcast"          # -loyalty


class BeastmanStatus(str, enum.Enum):
    ACTIVE = "active"
    CAPTURED = "captured"
    EXILED = "exiled"
    DECEASED = "deceased"


@dataclasses.dataclass(frozen=True)
class BeastmanStats:
    martial: int
    intellect: int
    leadership: int
    charisma: int
    loyalty: int


@dataclasses.dataclass(frozen=True)
class BeastmanOfficer:
    officer_id: str
    name: str
    race: BeastmanRace
    home_city: str
    serving_faction: str  # current nation_id
    stats: BeastmanStats
    trait: Trait
    age: int
    enlisted_day: int
    relocated_day: t.Optional[int]
    status: BeastmanStatus


def _validate_stat(v: int) -> bool:
    return 1 <= v <= 100


@dataclasses.dataclass
class BeastmanOfficerRosterSystem:
    _officers: dict[str, BeastmanOfficer] = (
        dataclasses.field(default_factory=dict)
    )

    def enlist(
        self, *, officer_id: str, name: str,
        race: BeastmanRace, home_city: str,
        stats: BeastmanStats, trait: Trait,
        age: int, enlisted_day: int,
    ) -> bool:
        if not officer_id or not name:
            return False
        if not home_city:
            return False
        if age < 1 or enlisted_day < 0:
            return False
        for v in (
            stats.martial, stats.intellect,
            stats.leadership, stats.charisma,
            stats.loyalty,
        ):
            if not _validate_stat(v):
                return False
        if officer_id in self._officers:
            return False
        # serving_faction starts at home_city by
        # convention — caller may transfer.
        self._officers[officer_id] = BeastmanOfficer(
            officer_id=officer_id, name=name,
            race=race, home_city=home_city,
            serving_faction=home_city, stats=stats,
            trait=trait, age=age,
            enlisted_day=enlisted_day,
            relocated_day=None,
            status=BeastmanStatus.ACTIVE,
        )
        return True

    def transfer_faction(
        self, *, officer_id: str,
        new_faction: str, now_day: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        if not new_faction:
            return False
        o = self._officers[officer_id]
        if o.status != BeastmanStatus.ACTIVE:
            return False
        if o.serving_faction == new_faction:
            return False
        self._officers[officer_id] = (
            dataclasses.replace(
                o, serving_faction=new_faction,
                relocated_day=now_day,
            )
        )
        return True

    def days_in_foreign_service(
        self, *, officer_id: str, now_day: int,
    ) -> int:
        if officer_id not in self._officers:
            return 0
        o = self._officers[officer_id]
        if o.serving_faction == o.home_city:
            return 0
        if o.relocated_day is None:
            return 0
        return max(0, now_day - o.relocated_day)

    def is_in_foreign_service(
        self, *, officer_id: str,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        return o.serving_faction != o.home_city

    def adjust_loyalty(
        self, *, officer_id: str, delta: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status != BeastmanStatus.ACTIVE:
            return False
        new_loy = max(
            1, min(100, o.stats.loyalty + delta),
        )
        new_stats = dataclasses.replace(
            o.stats, loyalty=new_loy,
        )
        self._officers[officer_id] = (
            dataclasses.replace(o, stats=new_stats)
        )
        return True

    def capture(
        self, *, officer_id: str, now_day: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status != BeastmanStatus.ACTIVE:
            return False
        self._officers[officer_id] = (
            dataclasses.replace(
                o, status=BeastmanStatus.CAPTURED,
            )
        )
        return True

    def exile(
        self, *, officer_id: str, now_day: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status not in (
            BeastmanStatus.ACTIVE,
            BeastmanStatus.CAPTURED,
        ):
            return False
        self._officers[officer_id] = (
            dataclasses.replace(
                o, status=BeastmanStatus.EXILED,
            )
        )
        return True

    def kill(
        self, *, officer_id: str, now_day: int,
    ) -> bool:
        if officer_id not in self._officers:
            return False
        o = self._officers[officer_id]
        if o.status == BeastmanStatus.DECEASED:
            return False
        self._officers[officer_id] = (
            dataclasses.replace(
                o, status=BeastmanStatus.DECEASED,
            )
        )
        return True

    def officer(
        self, *, officer_id: str,
    ) -> t.Optional[BeastmanOfficer]:
        return self._officers.get(officer_id)

    def serving_in(
        self, *, faction: str,
    ) -> list[BeastmanOfficer]:
        return [
            o for o in self._officers.values()
            if (o.serving_faction == faction
                and o.status
                == BeastmanStatus.ACTIVE)
        ]

    def by_race(
        self, *, race: BeastmanRace,
    ) -> list[BeastmanOfficer]:
        return [
            o for o in self._officers.values()
            if o.race == race
        ]

    def expatriates(self) -> list[BeastmanOfficer]:
        return [
            o for o in self._officers.values()
            if (o.serving_faction != o.home_city
                and o.status
                == BeastmanStatus.ACTIVE)
        ]


__all__ = [
    "BeastmanRace", "Trait", "BeastmanStatus",
    "BeastmanStats", "BeastmanOfficer",
    "BeastmanOfficerRosterSystem",
]
