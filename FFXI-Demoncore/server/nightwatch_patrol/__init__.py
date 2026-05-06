"""Nightwatch patrol — guards walk routes after dark.

Day-time guards stand at posts. Night-time, they walk
patrol routes — the world feels different at 02:00.
The patrol module advances each guard's position along
their assigned route on each tick. Routes are looping.

A guard has:
    - guard_id, zone_id
    - route: tuple of waypoint positions
    - speed_yalms_per_sec
    - active_at_night_only flag

Per tick (provided dt + time_of_day):
    if active_at_night_only AND it's not night → idle
    else advance position toward next waypoint;
        upon reaching, advance index (loop at end)

Public surface
--------------
    PatrolStatus enum
    Guard dataclass (mutable)
    NightwatchPatrol
        .register_guard(guard_id, zone_id, route, speed,
                        active_at_night_only) -> bool
        .tick(dt_seconds, time_of_day) -> tuple[Guard, ...]
        .position_of(guard_id) -> Optional[tuple[float, float]]
        .status_of(guard_id) -> PatrolStatus
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class PatrolStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    IDLE = "idle"
    PATROLLING = "patrolling"


@dataclasses.dataclass
class Guard:
    guard_id: str
    zone_id: str
    route: tuple[tuple[float, float], ...]
    speed_yalms_per_sec: float
    active_at_night_only: bool
    current_idx: int = 0
    position: tuple[float, float] = (0.0, 0.0)
    status: PatrolStatus = PatrolStatus.IDLE


@dataclasses.dataclass
class NightwatchPatrol:
    _guards: dict[str, Guard] = dataclasses.field(
        default_factory=dict,
    )

    def register_guard(
        self, *, guard_id: str, zone_id: str,
        route: t.Iterable[tuple[float, float]],
        speed_yalms_per_sec: float,
        active_at_night_only: bool = True,
    ) -> bool:
        if not guard_id or not zone_id:
            return False
        rt = tuple(route)
        if len(rt) < 2:
            return False
        if speed_yalms_per_sec <= 0:
            return False
        if guard_id in self._guards:
            return False
        self._guards[guard_id] = Guard(
            guard_id=guard_id, zone_id=zone_id, route=rt,
            speed_yalms_per_sec=speed_yalms_per_sec,
            active_at_night_only=active_at_night_only,
            current_idx=0, position=rt[0],
        )
        return True

    def tick(
        self, *, dt_seconds: float, time_of_day: str,
    ) -> tuple[Guard, ...]:
        is_night = (time_of_day == "night")
        out: list[Guard] = []
        for g in self._guards.values():
            if g.active_at_night_only and not is_night:
                g.status = PatrolStatus.IDLE
                continue
            travel = g.speed_yalms_per_sec * dt_seconds
            # consume travel across as many segments as needed
            safety = 0
            while travel > 0 and safety < 1000:
                safety += 1
                target_idx = (g.current_idx + 1) % len(g.route)
                target = g.route[target_idx]
                dx = target[0] - g.position[0]
                dy = target[1] - g.position[1]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= 0:
                    g.current_idx = target_idx
                    continue
                if travel >= dist:
                    g.position = target
                    g.current_idx = target_idx
                    travel -= dist
                else:
                    g.position = (
                        g.position[0] + dx * (travel / dist),
                        g.position[1] + dy * (travel / dist),
                    )
                    travel = 0
            g.status = PatrolStatus.PATROLLING
            out.append(g)
        return tuple(out)

    def position_of(
        self, *, guard_id: str,
    ) -> t.Optional[tuple[float, float]]:
        g = self._guards.get(guard_id)
        return g.position if g else None

    def status_of(
        self, *, guard_id: str,
    ) -> PatrolStatus:
        g = self._guards.get(guard_id)
        if g is None:
            return PatrolStatus.UNKNOWN
        return g.status

    def total_guards(self) -> int:
        return len(self._guards)


__all__ = [
    "PatrolStatus", "Guard", "NightwatchPatrol",
]
