"""Cross-biome trade routes — caravans + ships + airships as one network.

trade_routes covered surface caravans. Once you've got
naval and aerial transport, the merchant economy spans
all three biomes — but a route only works if the carrier
type fits the leg. A caravan can't cross open sea. An
airship can't dock at a sub bay.

Each Route consists of LEGS, each leg specifying:
    carrier  - CARAVAN / SHIP / SUBMARINE / AIRSHIP
    biome    - which biome the leg traverses
    capacity - cargo units the leg can carry
    duration - seconds end-to-end

A route's total capacity is the MIN over its legs (the
bottleneck), and total duration is the SUM. Disruptions
on a leg (faction blockade, storm front, etc.) flip the
leg's healthy flag; the route is healthy only when every
leg is healthy.

Public surface
--------------
    Carrier enum
    RouteLeg dataclass (frozen)
    Route dataclass (frozen)
    CrossBiomeTradeRoutes
        .register_route(route_id, name, legs)
        .set_leg_healthy(route_id, leg_index, healthy)
        .route_capacity(route_id) -> int
        .route_duration(route_id) -> int
        .is_healthy(route_id) -> bool
        .routes_using_carrier(carrier) -> tuple[Route, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Carrier(str, enum.Enum):
    CARAVAN = "caravan"
    SHIP = "ship"
    SUBMARINE = "submarine"
    AIRSHIP = "airship"


@dataclasses.dataclass(frozen=True)
class RouteLeg:
    from_node: str
    to_node: str
    carrier: Carrier
    biome: str
    capacity: int
    duration_seconds: int


@dataclasses.dataclass
class _RouteState:
    route_id: str
    name: str
    legs: list[RouteLeg]
    healthy: list[bool]


@dataclasses.dataclass(frozen=True)
class Route:
    route_id: str
    name: str
    legs: tuple[RouteLeg, ...]
    healthy_per_leg: tuple[bool, ...]


@dataclasses.dataclass
class CrossBiomeTradeRoutes:
    _routes: dict[str, _RouteState] = dataclasses.field(default_factory=dict)

    def register_route(
        self, *, route_id: str, name: str,
        legs: t.Iterable[RouteLeg],
    ) -> bool:
        if not route_id or not name or route_id in self._routes:
            return False
        leg_list = list(legs)
        if not leg_list:
            return False
        # validate that legs chain
        for i in range(len(leg_list) - 1):
            if leg_list[i].to_node != leg_list[i + 1].from_node:
                return False
        # validate per-leg fields
        for leg in leg_list:
            if (
                leg.capacity <= 0
                or leg.duration_seconds <= 0
                or not leg.from_node or not leg.to_node
            ):
                return False
        self._routes[route_id] = _RouteState(
            route_id=route_id, name=name,
            legs=leg_list,
            healthy=[True] * len(leg_list),
        )
        return True

    def set_leg_healthy(
        self, *, route_id: str, leg_index: int, healthy: bool,
    ) -> bool:
        r = self._routes.get(route_id)
        if r is None:
            return False
        if leg_index < 0 or leg_index >= len(r.legs):
            return False
        r.healthy[leg_index] = healthy
        return True

    def route_capacity(self, *, route_id: str) -> int:
        r = self._routes.get(route_id)
        if r is None:
            return 0
        return min(leg.capacity for leg in r.legs)

    def route_duration(self, *, route_id: str) -> int:
        r = self._routes.get(route_id)
        if r is None:
            return 0
        return sum(leg.duration_seconds for leg in r.legs)

    def is_healthy(self, *, route_id: str) -> bool:
        r = self._routes.get(route_id)
        if r is None:
            return False
        return all(r.healthy)

    def routes_using_carrier(
        self, *, carrier: Carrier,
    ) -> tuple[Route, ...]:
        out: list[Route] = []
        for r in self._routes.values():
            if any(leg.carrier == carrier for leg in r.legs):
                out.append(Route(
                    route_id=r.route_id, name=r.name,
                    legs=tuple(r.legs),
                    healthy_per_leg=tuple(r.healthy),
                ))
        return tuple(out)


__all__ = [
    "Carrier", "RouteLeg", "Route",
    "CrossBiomeTradeRoutes",
]
