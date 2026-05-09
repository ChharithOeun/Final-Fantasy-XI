"""Entity hobbies — every NPC and monster carries hobby tags.

Each registered entity has a hobby_set (1..3 HobbyKind tags).
Schedules say which hobby is active in which time-of-day slot
on which day-of-week (DOW). When players pass by an entity
during its hobby slot, observation is possible (handled in
entity_hobby_observation/). Combat or business hours suppress
hobby activity — the current_activity goes to NONE.

Volker might have hobbies {FISHING, DRINKING}: fishes Tuesday
mornings off the Bastok docks, drinks at the Steaming Sheep on
Saturday nights. The Goblin Smithy NM has {METALWORK,
GAMBLING}: at the forge most days, but Sunday nights he's at
the dice tables. Rare hobbies — a Galka WHM doing CALLIGRAPHY,
a Tarutaru WAR doing WEIGHTLIFTING — are quest-unlock-tier
sightings.

Public surface
--------------
    HobbyKind enum
    TimeSlot enum
    Hobby dataclass (frozen)
    HobbySchedule dataclass (frozen)
    EntityHobbiesSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_DAYS_PER_WEEK = 7


class HobbyKind(str, enum.Enum):
    FISHING = "fishing"
    DRINKING = "drinking"
    PAINTING = "painting"
    METALWORK = "metalwork"
    READING = "reading"
    GAMBLING = "gambling"
    GARDENING = "gardening"
    MEDITATION = "meditation"
    SINGING = "singing"
    WEIGHTLIFTING = "weightlifting"
    CALLIGRAPHY = "calligraphy"
    BIRDWATCHING = "birdwatching"


class TimeSlot(str, enum.Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


@dataclasses.dataclass(frozen=True)
class HobbySchedule:
    hobby: HobbyKind
    day_of_week: int    # 0..6
    time_slot: TimeSlot
    zone_id: str


@dataclasses.dataclass(frozen=True)
class Hobby:
    entity_id: str
    hobby_set: tuple[HobbyKind, ...]
    schedules: tuple[HobbySchedule, ...]
    in_combat: bool
    rare_for_class: bool


@dataclasses.dataclass
class EntityHobbiesSystem:
    _entities: dict[str, Hobby] = dataclasses.field(
        default_factory=dict,
    )

    def register_entity(
        self, *, entity_id: str,
        hobby_set: tuple[HobbyKind, ...],
        rare_for_class: bool = False,
    ) -> bool:
        if not entity_id or entity_id in self._entities:
            return False
        if not hobby_set or len(hobby_set) > 3:
            return False
        if len(set(hobby_set)) != len(hobby_set):
            return False
        self._entities[entity_id] = Hobby(
            entity_id=entity_id,
            hobby_set=hobby_set, schedules=(),
            in_combat=False,
            rare_for_class=rare_for_class,
        )
        return True

    def add_schedule(
        self, *, entity_id: str, hobby: HobbyKind,
        day_of_week: int, time_slot: TimeSlot,
        zone_id: str,
    ) -> bool:
        if entity_id not in self._entities:
            return False
        e = self._entities[entity_id]
        if hobby not in e.hobby_set:
            return False
        if not 0 <= day_of_week < _DAYS_PER_WEEK:
            return False
        if not zone_id:
            return False
        for s in e.schedules:
            if (
                s.day_of_week == day_of_week
                and s.time_slot == time_slot
            ):
                return False  # slot already filled
        new_sched = HobbySchedule(
            hobby=hobby, day_of_week=day_of_week,
            time_slot=time_slot, zone_id=zone_id,
        )
        self._entities[entity_id] = dataclasses.replace(
            e, schedules=e.schedules + (new_sched,),
        )
        return True

    def set_combat_state(
        self, *, entity_id: str, in_combat: bool,
    ) -> bool:
        if entity_id not in self._entities:
            return False
        e = self._entities[entity_id]
        self._entities[entity_id] = dataclasses.replace(
            e, in_combat=in_combat,
        )
        return True

    def current_activity(
        self, *, entity_id: str, day: int,
        time_slot: TimeSlot,
    ) -> t.Optional[HobbySchedule]:
        """Returns the hobby schedule active right
        now, or None if entity is in combat / has
        no schedule for this slot.
        """
        if entity_id not in self._entities:
            return None
        e = self._entities[entity_id]
        if e.in_combat:
            return None
        dow = day % _DAYS_PER_WEEK
        for s in e.schedules:
            if (
                s.day_of_week == dow
                and s.time_slot == time_slot
            ):
                return s
        return None

    def hobby(
        self, *, entity_id: str,
    ) -> t.Optional[Hobby]:
        return self._entities.get(entity_id)

    def entities_practicing(
        self, *, hobby: HobbyKind, day: int,
        time_slot: TimeSlot,
    ) -> list[str]:
        """Which registered entities are currently
        engaged in `hobby` right now."""
        out: list[str] = []
        dow = day % _DAYS_PER_WEEK
        for eid, e in self._entities.items():
            if e.in_combat:
                continue
            for s in e.schedules:
                if (
                    s.hobby == hobby
                    and s.day_of_week == dow
                    and s.time_slot == time_slot
                ):
                    out.append(eid)
                    break
        return out

    def is_rare_pairing(
        self, *, entity_id: str,
    ) -> bool:
        """True if this entity's hobby is unusual
        for its class — a quest-unlock-tier
        sighting."""
        e = self._entities.get(entity_id)
        if e is None:
            return False
        return e.rare_for_class


__all__ = [
    "HobbyKind", "TimeSlot", "Hobby",
    "HobbySchedule", "EntityHobbiesSystem",
]
