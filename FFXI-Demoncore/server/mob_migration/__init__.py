"""Mob migration — populations move between zones.

Mobs aren't fixed to a zone — they MIGRATE. Triggers:
* SEASONAL — winter Tigers move down from snowy peaks to forests
* CONQUEST — beastmen tribes shift territory after a faction loss
* PREDATOR_PRESSURE — too many wyverns; sheep flee to safer zones
* WEATHER_DRIVEN — sandstorm forces antlions deeper underground
* HARVEST_FOLLOW — gigas follow ore veins; goblins chase camps
* PLAYER_PRESSURE — heavily farmed mob class empties zone

Each migration moves a population fragment from a source zone to
a destination zone; the source population drops, destination
rises. Spawn pools recompute next tick.

Public surface
--------------
    MigrationTrigger enum
    MobPopulation dataclass
    MigrationEvent dataclass
    MigrationPlan dataclass
    MobMigrationRegistry
        .seed_population(zone_id, mob_kind, headcount)
        .observe(trigger, source_zone, dest_zone, mob_kind, ...)
        .plan_for_tick(now_seconds) -> tuple[MigrationPlan, ...]
        .apply_plan(plan)
        .population(zone_id, mob_kind)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default per-tick migration cap (we don't move more than this
# fraction of source population in one event).
DEFAULT_MAX_MIGRATION_FRACTION = 0.4


class MigrationTrigger(str, enum.Enum):
    SEASONAL = "seasonal"
    CONQUEST = "conquest"
    PREDATOR_PRESSURE = "predator_pressure"
    WEATHER_DRIVEN = "weather_driven"
    HARVEST_FOLLOW = "harvest_follow"
    PLAYER_PRESSURE = "player_pressure"


# How urgent each trigger is — higher fires first.
_TRIGGER_PRIORITY: dict[MigrationTrigger, int] = {
    MigrationTrigger.PLAYER_PRESSURE: 0,    # urgent: empty zone
    MigrationTrigger.WEATHER_DRIVEN: 1,
    MigrationTrigger.PREDATOR_PRESSURE: 2,
    MigrationTrigger.CONQUEST: 3,
    MigrationTrigger.HARVEST_FOLLOW: 4,
    MigrationTrigger.SEASONAL: 5,
}


@dataclasses.dataclass
class MobPopulation:
    zone_id: str
    mob_kind: str
    headcount: int = 0
    last_changed_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class MigrationEvent:
    """Caller-supplied: a reason mobs WANT to move."""
    trigger: MigrationTrigger
    mob_kind: str
    source_zone_id: str
    destination_zone_id: str
    fraction_of_source: float = 0.25
    note: str = ""
    observed_at_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class MigrationPlan:
    """Concrete migration that's about to be applied."""
    trigger: MigrationTrigger
    mob_kind: str
    source_zone_id: str
    destination_zone_id: str
    headcount_moved: int
    note: str = ""


@dataclasses.dataclass
class MobMigrationRegistry:
    max_migration_fraction: float = DEFAULT_MAX_MIGRATION_FRACTION
    _populations: dict[
        tuple[str, str], MobPopulation,
    ] = dataclasses.field(default_factory=dict)
    _pending_events: list[MigrationEvent] = dataclasses.field(
        default_factory=list,
    )

    def seed_population(
        self, *, zone_id: str, mob_kind: str,
        headcount: int, now_seconds: float = 0.0,
    ) -> None:
        key = (zone_id, mob_kind)
        self._populations[key] = MobPopulation(
            zone_id=zone_id, mob_kind=mob_kind,
            headcount=headcount,
            last_changed_seconds=now_seconds,
        )

    def population(
        self, *, zone_id: str, mob_kind: str,
    ) -> int:
        key = (zone_id, mob_kind)
        pop = self._populations.get(key)
        return pop.headcount if pop else 0

    def observe(self, *, event: MigrationEvent) -> None:
        self._pending_events.append(event)

    def plan_for_tick(
        self, *, now_seconds: float = 0.0,
    ) -> tuple[MigrationPlan, ...]:
        # Sort pending events by trigger priority
        events = sorted(
            self._pending_events,
            key=lambda e: _TRIGGER_PRIORITY[e.trigger],
        )
        plans: list[MigrationPlan] = []
        for ev in events:
            src_pop = self._populations.get(
                (ev.source_zone_id, ev.mob_kind),
            )
            if src_pop is None or src_pop.headcount <= 0:
                continue
            # Cap fraction
            effective_fraction = min(
                ev.fraction_of_source,
                self.max_migration_fraction,
            )
            moved = int(src_pop.headcount * effective_fraction)
            if moved <= 0:
                continue
            plans.append(MigrationPlan(
                trigger=ev.trigger, mob_kind=ev.mob_kind,
                source_zone_id=ev.source_zone_id,
                destination_zone_id=ev.destination_zone_id,
                headcount_moved=moved,
                note=ev.note,
            ))
        # Clear queue
        self._pending_events.clear()
        return tuple(plans)

    def apply_plan(
        self, *, plan: MigrationPlan,
        now_seconds: float = 0.0,
    ) -> bool:
        src_key = (plan.source_zone_id, plan.mob_kind)
        dst_key = (plan.destination_zone_id, plan.mob_kind)
        src = self._populations.get(src_key)
        if src is None:
            return False
        if src.headcount < plan.headcount_moved:
            return False
        src.headcount -= plan.headcount_moved
        src.last_changed_seconds = now_seconds
        dst = self._populations.setdefault(
            dst_key,
            MobPopulation(
                zone_id=plan.destination_zone_id,
                mob_kind=plan.mob_kind,
            ),
        )
        dst.headcount += plan.headcount_moved
        dst.last_changed_seconds = now_seconds
        return True

    def total_zones(self) -> int:
        return len({z for z, _ in self._populations})

    def total_pending(self) -> int:
        return len(self._pending_events)


__all__ = [
    "DEFAULT_MAX_MIGRATION_FRACTION",
    "MigrationTrigger",
    "MobPopulation", "MigrationEvent", "MigrationPlan",
    "MobMigrationRegistry",
]
