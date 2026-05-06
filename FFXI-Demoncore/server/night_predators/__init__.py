"""Night predators — nocturnal mob spawn engine.

Some creatures only walk after dark. Others stalk only
under the new moon. The night_predators module computes
which mobs in a zone are eligible to spawn given the
current time of day and moon phase, and produces a
ranked spawn list.

Activity windows (per mob profile):
    DIURNAL       awake during the day, asleep at night
    NOCTURNAL     awake at night, asleep during the day
    CREPUSCULAR   active at dusk + dawn only
    LUNAR_FULL    only when moon is FULL
    LUNAR_NEW     only when moon is NEW
    ALWAYS        ignores time/phase

Public surface
--------------
    ActivityKind enum
    TimeOfDay enum (NIGHT/DAY/DUSK/DAWN)
    MoonPhase enum (NEW/WAXING/FULL/WANING)
    NightPredatorProfile dataclass (frozen)
    NightPredatorRegistry
        .register_predator(predator_id, zone_id, kind,
                           weight) -> bool
        .eligible_in(zone_id, time_of_day, moon_phase)
            -> tuple[NightPredatorProfile, ...]
        .ranked_pool(zone_id, time_of_day, moon_phase)
            -> tuple[tuple[NightPredatorProfile, int], ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TimeOfDay(str, enum.Enum):
    NIGHT = "night"
    DAY = "day"
    DUSK = "dusk"
    DAWN = "dawn"


class MoonPhase(str, enum.Enum):
    NEW = "new"
    WAXING = "waxing"
    FULL = "full"
    WANING = "waning"


class ActivityKind(str, enum.Enum):
    DIURNAL = "diurnal"
    NOCTURNAL = "nocturnal"
    CREPUSCULAR = "crepuscular"
    LUNAR_FULL = "lunar_full"
    LUNAR_NEW = "lunar_new"
    ALWAYS = "always"


@dataclasses.dataclass(frozen=True)
class NightPredatorProfile:
    predator_id: str
    zone_id: str
    kind: ActivityKind
    weight: int


def _is_eligible(
    kind: ActivityKind,
    tod: TimeOfDay, moon: MoonPhase,
) -> bool:
    if kind == ActivityKind.ALWAYS:
        return True
    if kind == ActivityKind.DIURNAL:
        return tod == TimeOfDay.DAY
    if kind == ActivityKind.NOCTURNAL:
        return tod == TimeOfDay.NIGHT
    if kind == ActivityKind.CREPUSCULAR:
        return tod in (TimeOfDay.DUSK, TimeOfDay.DAWN)
    if kind == ActivityKind.LUNAR_FULL:
        return moon == MoonPhase.FULL and (
            tod == TimeOfDay.NIGHT
        )
    if kind == ActivityKind.LUNAR_NEW:
        return moon == MoonPhase.NEW and (
            tod == TimeOfDay.NIGHT
        )
    return False


@dataclasses.dataclass
class NightPredatorRegistry:
    _predators: list[NightPredatorProfile] = dataclasses.field(
        default_factory=list,
    )
    _by_id: set[str] = dataclasses.field(default_factory=set)

    def register_predator(
        self, *, predator_id: str, zone_id: str,
        kind: ActivityKind, weight: int = 1,
    ) -> bool:
        if not predator_id or not zone_id:
            return False
        if weight <= 0:
            return False
        if predator_id in self._by_id:
            return False
        self._by_id.add(predator_id)
        self._predators.append(NightPredatorProfile(
            predator_id=predator_id, zone_id=zone_id,
            kind=kind, weight=weight,
        ))
        return True

    def eligible_in(
        self, *, zone_id: str,
        time_of_day: TimeOfDay,
        moon_phase: MoonPhase,
    ) -> tuple[NightPredatorProfile, ...]:
        return tuple(
            p for p in self._predators
            if p.zone_id == zone_id
            and _is_eligible(p.kind, time_of_day, moon_phase)
        )

    def ranked_pool(
        self, *, zone_id: str,
        time_of_day: TimeOfDay,
        moon_phase: MoonPhase,
    ) -> tuple[tuple[NightPredatorProfile, int], ...]:
        elig = self.eligible_in(
            zone_id=zone_id,
            time_of_day=time_of_day,
            moon_phase=moon_phase,
        )
        # sorted descending by weight, stable
        ranked = sorted(elig, key=lambda p: -p.weight)
        return tuple((p, p.weight) for p in ranked)

    def total_predators(self) -> int:
        return len(self._predators)


__all__ = [
    "TimeOfDay", "MoonPhase", "ActivityKind",
    "NightPredatorProfile", "NightPredatorRegistry",
]
