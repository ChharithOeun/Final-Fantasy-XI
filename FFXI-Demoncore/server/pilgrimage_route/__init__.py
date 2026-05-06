"""Pilgrimage route — chains of monuments forming pilgrim paths.

A pilgrimage stitches together places that matter. Visit
each monument in order, and at the end you receive a
key item, a title, or a quiet exp bonus that doesn't
break the world but feels earned.

A Route has:
    waypoints : ordered tuple of (zone_id, monument_id)
                (or arbitrary landmark refs)
    completion_reward : opaque payload string for the
                        reward system to consume
    optional ordered: True means must visit in sequence
                      (default); False means any order

Each player's progress is tracked: which waypoints they've
struck off. Re-traversal is not double-counted; the route
becomes a pilgrim badge once cleared.

Public surface
--------------
    Waypoint dataclass (frozen)
    PilgrimageRoute dataclass (frozen seed)
    PilgrimProgress dataclass (mutable)
    PilgrimageRouteRegistry
        .define_route(route_id, waypoints, ordered,
                      completion_reward, name) -> bool
        .visit_waypoint(player_id, route_id,
                        zone_id, monument_id, visited_at)
            -> VisitOutcome
        .progress_for(player_id, route_id)
            -> Optional[PilgrimProgress]
        .completed_routes_for(player_id) -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class VisitOutcomeKind(str, enum.Enum):
    PROGRESSED = "progressed"
    COMPLETED = "completed"
    OUT_OF_ORDER = "out_of_order"
    DUPLICATE = "duplicate"
    UNKNOWN_WAYPOINT = "unknown_waypoint"
    UNKNOWN_ROUTE = "unknown_route"


@dataclasses.dataclass(frozen=True)
class Waypoint:
    zone_id: str
    monument_id: str    # any landmark ref, not strictly a monument


@dataclasses.dataclass(frozen=True)
class PilgrimageRoute:
    route_id: str
    name: str
    waypoints: tuple[Waypoint, ...]
    ordered: bool
    completion_reward: str


@dataclasses.dataclass
class PilgrimProgress:
    player_id: str
    route_id: str
    visited_indexes: tuple[int, ...] = ()
    completed: bool = False
    completed_at: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class VisitOutcome:
    kind: VisitOutcomeKind
    progress_count: int
    total_waypoints: int
    completion_reward: t.Optional[str] = None


@dataclasses.dataclass
class PilgrimageRouteRegistry:
    _routes: dict[str, PilgrimageRoute] = dataclasses.field(
        default_factory=dict,
    )
    _progress: dict[
        tuple[str, str], PilgrimProgress,
    ] = dataclasses.field(default_factory=dict)

    def define_route(
        self, *, route_id: str, name: str,
        waypoints: t.Iterable[Waypoint],
        ordered: bool = True, completion_reward: str = "",
    ) -> bool:
        if not route_id or not name:
            return False
        wp = tuple(waypoints)
        if not wp:
            return False
        if route_id in self._routes:
            return False
        self._routes[route_id] = PilgrimageRoute(
            route_id=route_id, name=name,
            waypoints=wp, ordered=ordered,
            completion_reward=completion_reward,
        )
        return True

    def get_route(
        self, *, route_id: str,
    ) -> t.Optional[PilgrimageRoute]:
        return self._routes.get(route_id)

    def visit_waypoint(
        self, *, player_id: str, route_id: str,
        zone_id: str, monument_id: str,
        visited_at: int,
    ) -> VisitOutcome:
        route = self._routes.get(route_id)
        if route is None:
            return VisitOutcome(
                kind=VisitOutcomeKind.UNKNOWN_ROUTE,
                progress_count=0, total_waypoints=0,
            )
        if not player_id:
            return VisitOutcome(
                kind=VisitOutcomeKind.UNKNOWN_WAYPOINT,
                progress_count=0,
                total_waypoints=len(route.waypoints),
            )

        # find the waypoint index
        idx = -1
        for i, wp in enumerate(route.waypoints):
            if (wp.zone_id == zone_id
                    and wp.monument_id == monument_id):
                idx = i
                break
        if idx < 0:
            return VisitOutcome(
                kind=VisitOutcomeKind.UNKNOWN_WAYPOINT,
                progress_count=0,
                total_waypoints=len(route.waypoints),
            )

        key = (player_id, route_id)
        prog = self._progress.get(key)
        if prog is None:
            prog = PilgrimProgress(
                player_id=player_id, route_id=route_id,
            )
            self._progress[key] = prog
        if prog.completed:
            return VisitOutcome(
                kind=VisitOutcomeKind.DUPLICATE,
                progress_count=len(prog.visited_indexes),
                total_waypoints=len(route.waypoints),
            )
        if idx in prog.visited_indexes:
            return VisitOutcome(
                kind=VisitOutcomeKind.DUPLICATE,
                progress_count=len(prog.visited_indexes),
                total_waypoints=len(route.waypoints),
            )

        # ordered: must visit in sequence
        if route.ordered and idx != len(prog.visited_indexes):
            return VisitOutcome(
                kind=VisitOutcomeKind.OUT_OF_ORDER,
                progress_count=len(prog.visited_indexes),
                total_waypoints=len(route.waypoints),
            )

        prog.visited_indexes = prog.visited_indexes + (idx,)
        if len(prog.visited_indexes) >= len(route.waypoints):
            prog.completed = True
            prog.completed_at = visited_at
            return VisitOutcome(
                kind=VisitOutcomeKind.COMPLETED,
                progress_count=len(prog.visited_indexes),
                total_waypoints=len(route.waypoints),
                completion_reward=route.completion_reward,
            )
        return VisitOutcome(
            kind=VisitOutcomeKind.PROGRESSED,
            progress_count=len(prog.visited_indexes),
            total_waypoints=len(route.waypoints),
        )

    def progress_for(
        self, *, player_id: str, route_id: str,
    ) -> t.Optional[PilgrimProgress]:
        return self._progress.get((player_id, route_id))

    def completed_routes_for(
        self, *, player_id: str,
    ) -> tuple[str, ...]:
        out: list[str] = []
        for (pid, rid), prog in self._progress.items():
            if pid == player_id and prog.completed:
                out.append(rid)
        return tuple(sorted(out))


__all__ = [
    "VisitOutcomeKind", "Waypoint", "PilgrimageRoute",
    "PilgrimProgress", "VisitOutcome",
    "PilgrimageRouteRegistry",
]
