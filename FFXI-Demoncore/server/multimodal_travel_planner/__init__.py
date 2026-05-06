"""Multimodal travel planner — pick a route across biomes.

Given a start (zone, biome) and end (zone, biome), produce a
sequence of LEGS that move the player through surface roads,
sea lanes, sub paths, or airship routes — whatever stitches
together. Each leg has a TravelMode and an estimated cost
in seconds; the planner picks the lowest-cost path.

This is a thin coordination layer; underneath it leans on
the biome-specific atlases (zone_atlas for surface,
depth_band_atlas for the deep, an analogous structure for
the sky) plus biome_transition_zones to switch modes.
For the first cut, we don't introspect those atlases —
callers register simple "leg" graph edges (from_node ->
to_node, mode, cost) and the planner runs Dijkstra over
them. That keeps this module dependency-free and testable
in isolation.

Public surface
--------------
    TravelMode enum
    TravelLeg dataclass (frozen)
    Route dataclass (frozen)
    MultimodalTravelPlanner
        .add_leg(from_node, to_node, mode, cost_seconds)
        .plan(start_node, end_node, allowed_modes=None)
            -> Optional[Route]
"""
from __future__ import annotations

import dataclasses
import enum
import heapq
import typing as t


class TravelMode(str, enum.Enum):
    WALK = "walk"
    CHOCOBO = "chocobo"
    SHIP = "ship"
    SUBMARINE = "submarine"
    AIRSHIP = "airship"
    TELEPORT = "teleport"
    HOMEPOINT = "homepoint"


@dataclasses.dataclass(frozen=True)
class TravelLeg:
    from_node: str
    to_node: str
    mode: TravelMode
    cost_seconds: int


@dataclasses.dataclass(frozen=True)
class Route:
    legs: tuple[TravelLeg, ...]
    total_cost_seconds: int
    modes_used: frozenset[TravelMode]


@dataclasses.dataclass
class MultimodalTravelPlanner:
    _edges: dict[str, list[TravelLeg]] = dataclasses.field(
        default_factory=dict,
    )

    def add_leg(
        self, *, from_node: str, to_node: str,
        mode: TravelMode, cost_seconds: int,
    ) -> bool:
        if not from_node or not to_node:
            return False
        if from_node == to_node:
            return False
        if cost_seconds < 0:
            return False
        leg = TravelLeg(
            from_node=from_node, to_node=to_node,
            mode=mode, cost_seconds=cost_seconds,
        )
        self._edges.setdefault(from_node, []).append(leg)
        return True

    def plan(
        self, *, start_node: str, end_node: str,
        allowed_modes: t.Optional[t.Iterable[TravelMode]] = None,
    ) -> t.Optional[Route]:
        if start_node == end_node:
            return Route(legs=(), total_cost_seconds=0, modes_used=frozenset())
        modes_filter: t.Optional[set[TravelMode]] = (
            set(allowed_modes) if allowed_modes is not None else None
        )
        # Dijkstra
        dist: dict[str, int] = {start_node: 0}
        prev: dict[str, TravelLeg] = {}
        # priority queue of (cost, counter, node)
        # counter avoids comparing strings on cost ties
        counter = 0
        pq: list[tuple[int, int, str]] = [(0, 0, start_node)]
        while pq:
            cost, _, cur = heapq.heappop(pq)
            if cur == end_node:
                # reconstruct
                legs: list[TravelLeg] = []
                node = cur
                while node in prev:
                    leg = prev[node]
                    legs.append(leg)
                    node = leg.from_node
                legs.reverse()
                return Route(
                    legs=tuple(legs),
                    total_cost_seconds=cost,
                    modes_used=frozenset(l.mode for l in legs),
                )
            if cost > dist.get(cur, cost):
                continue
            for leg in self._edges.get(cur, []):
                if modes_filter is not None and leg.mode not in modes_filter:
                    continue
                ncost = cost + leg.cost_seconds
                if ncost < dist.get(leg.to_node, 10**18):
                    dist[leg.to_node] = ncost
                    prev[leg.to_node] = leg
                    counter += 1
                    heapq.heappush(pq, (ncost, counter, leg.to_node))
        return None


__all__ = [
    "TravelMode", "TravelLeg", "Route",
    "MultimodalTravelPlanner",
]
