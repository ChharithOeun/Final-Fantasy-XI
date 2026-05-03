"""AI patrol coordination — guard routes + alert chains.

Town and outpost guard NPCs walk fixed PATROL ROUTES and back
each other up. Each guard belongs to a SQUAD with a fixed
ROUTE — a list of waypoints they cycle through. When a guard
spots a crime, hostile mob, or outlaw, they raise an ALERT.
The alert cascades to all squad-mates within ALERT_REACH and
optionally to the town crier and bounty system.

Distinct from squadron_system (player-led mercs) and
beastmen_factions (whole-faction AI). This is the LOCAL
defensive AI layer.

Public surface
--------------
    AlertKind enum
    PatrolRoute dataclass
    GuardNPC dataclass
    Alert dataclass
    AIPatrolCoordination
        .register_route(route_id, zone_id, waypoints)
        .assign_guard(guard_id, route_id, squad_id)
        .step_patrol(now_seconds) — advances all guards one
        .raise_alert(reporter_id, kind, x, y, z) -> Alert
        .alerts_for_squad(squad_id)
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Default reach within which an alert propagates.
DEFAULT_ALERT_REACH = 60.0
DEFAULT_PATROL_STEP_SPEED = 5.0   # game units per second


class AlertKind(str, enum.Enum):
    HOSTILE_MOB = "hostile_mob"
    PLAYER_CRIME = "player_crime"
    OUTLAW_SPOTTED = "outlaw_spotted"
    BEASTMAN_RAID = "beastman_raid"
    FIRE_OR_DAMAGE = "fire_or_damage"
    WANTED_PERSON = "wanted_person"


@dataclasses.dataclass(frozen=True)
class Waypoint:
    x: float
    y: float
    z: float = 0.0
    pause_seconds: float = 0.0


@dataclasses.dataclass
class PatrolRoute:
    route_id: str
    zone_id: str
    waypoints: tuple[Waypoint, ...]


@dataclasses.dataclass
class GuardNPC:
    guard_id: str
    route_id: str
    squad_id: str
    waypoint_index: int = 0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    last_step_at_seconds: float = 0.0
    on_alert: bool = False


@dataclasses.dataclass
class Alert:
    alert_id: str
    reporter_id: str
    kind: AlertKind
    zone_id: str
    x: float
    y: float
    z: float
    raised_at_seconds: float
    responding_squads: tuple[str, ...] = ()


@dataclasses.dataclass
class AIPatrolCoordination:
    alert_reach: float = DEFAULT_ALERT_REACH
    patrol_speed: float = DEFAULT_PATROL_STEP_SPEED
    _routes: dict[str, PatrolRoute] = dataclasses.field(
        default_factory=dict,
    )
    _guards: dict[str, GuardNPC] = dataclasses.field(
        default_factory=dict,
    )
    _alerts: dict[str, Alert] = dataclasses.field(
        default_factory=dict,
    )
    _next_alert_id: int = 0

    def register_route(
        self, *, route_id: str, zone_id: str,
        waypoints: tuple[Waypoint, ...],
    ) -> t.Optional[PatrolRoute]:
        if route_id in self._routes:
            return None
        if len(waypoints) < 2:
            return None
        route = PatrolRoute(
            route_id=route_id, zone_id=zone_id,
            waypoints=waypoints,
        )
        self._routes[route_id] = route
        return route

    def assign_guard(
        self, *, guard_id: str, route_id: str,
        squad_id: str,
    ) -> bool:
        if guard_id in self._guards:
            return False
        route = self._routes.get(route_id)
        if route is None:
            return False
        first = route.waypoints[0]
        self._guards[guard_id] = GuardNPC(
            guard_id=guard_id, route_id=route_id,
            squad_id=squad_id,
            x=first.x, y=first.y, z=first.z,
        )
        return True

    def guard(self, guard_id: str) -> t.Optional[GuardNPC]:
        return self._guards.get(guard_id)

    def step_patrol(
        self, *, elapsed_seconds: float,
    ) -> int:
        if elapsed_seconds <= 0:
            return 0
        moved = 0
        step_dist = self.patrol_speed * elapsed_seconds
        for g in self._guards.values():
            if g.on_alert:
                continue       # stay put while responding
            route = self._routes.get(g.route_id)
            if route is None:
                continue
            target = route.waypoints[
                (g.waypoint_index + 1) % len(route.waypoints)
            ]
            dx = target.x - g.x
            dy = target.y - g.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= step_dist:
                # Arrive
                g.x = target.x
                g.y = target.y
                g.z = target.z
                g.waypoint_index = (
                    g.waypoint_index + 1
                ) % len(route.waypoints)
            else:
                ratio = step_dist / dist
                g.x += dx * ratio
                g.y += dy * ratio
            g.last_step_at_seconds += elapsed_seconds
            moved += 1
        return moved

    def raise_alert(
        self, *, reporter_id: str, kind: AlertKind,
        zone_id: str, x: float, y: float, z: float = 0.0,
        now_seconds: float = 0.0,
    ) -> Alert:
        aid = f"alert_{self._next_alert_id}"
        self._next_alert_id += 1
        # Find squads with at least one guard within reach in zone
        responding: set[str] = set()
        for g in self._guards.values():
            route = self._routes.get(g.route_id)
            if route is None or route.zone_id != zone_id:
                continue
            dx = g.x - x
            dy = g.y - y
            dz = g.z - z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist <= self.alert_reach:
                responding.add(g.squad_id)
                g.on_alert = True
        alert = Alert(
            alert_id=aid, reporter_id=reporter_id,
            kind=kind, zone_id=zone_id,
            x=x, y=y, z=z,
            raised_at_seconds=now_seconds,
            responding_squads=tuple(sorted(responding)),
        )
        self._alerts[aid] = alert
        return alert

    def stand_down_squad(
        self, *, squad_id: str,
    ) -> int:
        cleared = 0
        for g in self._guards.values():
            if g.squad_id == squad_id and g.on_alert:
                g.on_alert = False
                cleared += 1
        return cleared

    def alerts_for_squad(
        self, squad_id: str,
    ) -> tuple[Alert, ...]:
        return tuple(
            a for a in self._alerts.values()
            if squad_id in a.responding_squads
        )

    def total_routes(self) -> int:
        return len(self._routes)

    def total_guards(self) -> int:
        return len(self._guards)

    def total_alerts(self) -> int:
        return len(self._alerts)


__all__ = [
    "DEFAULT_ALERT_REACH", "DEFAULT_PATROL_STEP_SPEED",
    "AlertKind",
    "Waypoint", "PatrolRoute", "GuardNPC", "Alert",
    "AIPatrolCoordination",
]
