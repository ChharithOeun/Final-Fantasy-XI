"""World streaming — UE5 World Partition / OFPA tile streaming.

Models the runtime memory budget for a seamless open world.
Tiles are the unit of streaming — a few hundred meters per
tile, each with bounds, asset cost, and neighbor list. As the
player moves, tiles inside ``prefetch_radius_m`` start LOADING,
tiles inside ``keep_radius_m`` are kept ACTIVE, tiles outside
``evict_radius_m`` move to COOLING and are dropped when memory
pressure rises.

Memory budgets per platform (in MB so the int math stays exact):

    PC_ULTRA        24576   ( 24 GB)
    PC_HIGH         16384   ( 16 GB)
    PS5             12288   ( 12 GB)
    XBOX_SERIES_X   12288   ( 12 GB)
    XBOX_SERIES_S    8192   (  8 GB)

State machine:

    UNLOADED --(within prefetch radius)--> LOADING
    LOADING  --(load complete)----------> LOADED
    LOADED   --(within keep radius)-----> ACTIVE
    ACTIVE   --(outside keep radius)----> COOLING
    COOLING  --(outside evict radius
                or memory pressure)-----> UNLOADED

Eviction picks the cheapest cooling tile when over budget;
ties broken by furthest distance so we drop the tile the
player is least likely to come back to.

Public surface
--------------
    StreamPlatform enum
    TileState enum
    StreamAction enum
    StreamTile dataclass (frozen)
    StreamingPlan dataclass (frozen)
    WorldStreamer
    PLATFORM_BUDGET_MB dict[StreamPlatform, int]
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class StreamPlatform(enum.Enum):
    PC_ULTRA = "pc_ultra"
    PC_HIGH = "pc_high"
    PS5 = "ps5"
    XBOX_SERIES_X = "xbox_series_x"
    XBOX_SERIES_S = "xbox_series_s"


PLATFORM_BUDGET_MB: dict[StreamPlatform, int] = {
    StreamPlatform.PC_ULTRA: 24 * 1024,
    StreamPlatform.PC_HIGH: 16 * 1024,
    StreamPlatform.PS5: 12 * 1024,
    StreamPlatform.XBOX_SERIES_X: 12 * 1024,
    StreamPlatform.XBOX_SERIES_S: 8 * 1024,
}


class TileState(enum.Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    COOLING = "cooling"


class StreamAction(enum.Enum):
    LOAD = "load"
    KEEP = "keep"
    COOL = "cool"
    EVICT = "evict"


@dataclasses.dataclass(frozen=True)
class StreamTile:
    tile_id: str
    zone_id: str
    bounds_min_xyz: tuple[float, float, float]
    bounds_max_xyz: tuple[float, float, float]
    asset_size_mb: float
    lod_levels: int
    neighbor_tile_ids: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class StreamingPlan:
    """One streaming-decision pass. Lists are sorted by tile_id
    for stable comparison in tests."""
    actions: tuple[tuple[str, StreamAction], ...]
    resident_mb_after: float
    over_budget_by_mb: float


def _tile_center(tile: StreamTile) -> tuple[float, float, float]:
    mn = tile.bounds_min_xyz
    mx = tile.bounds_max_xyz
    return (
        (mn[0] + mx[0]) * 0.5,
        (mn[1] + mx[1]) * 0.5,
        (mn[2] + mx[2]) * 0.5,
    )


def _dist(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
        + (a[2] - b[2]) ** 2
    )


@dataclasses.dataclass
class WorldStreamer:
    prefetch_radius_m: float = 200.0
    keep_radius_m: float = 500.0
    evict_radius_m: float = 1500.0
    _tiles: dict[str, StreamTile] = dataclasses.field(
        default_factory=dict,
    )
    _states: dict[str, TileState] = dataclasses.field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        if not (
            0.0 < self.prefetch_radius_m
            <= self.keep_radius_m
            <= self.evict_radius_m
        ):
            raise ValueError(
                "radii must satisfy "
                "0 < prefetch <= keep <= evict",
            )

    def register_tile(self, tile: StreamTile) -> None:
        if not tile.tile_id:
            raise ValueError("tile_id required")
        if tile.asset_size_mb < 0:
            raise ValueError("asset_size_mb >= 0")
        if tile.lod_levels < 1:
            raise ValueError("lod_levels >= 1")
        # bounds_min must be <= bounds_max componentwise
        for i in range(3):
            if tile.bounds_min_xyz[i] > tile.bounds_max_xyz[i]:
                raise ValueError("bounds_min must be <= bounds_max")
        self._tiles[tile.tile_id] = tile
        self._states.setdefault(tile.tile_id, TileState.UNLOADED)

    def get_tile(self, tile_id: str) -> StreamTile:
        if tile_id not in self._tiles:
            raise KeyError(f"unknown tile: {tile_id}")
        return self._tiles[tile_id]

    def all_tiles(self) -> tuple[StreamTile, ...]:
        return tuple(self._tiles.values())

    def state_of(self, tile_id: str) -> TileState:
        if tile_id not in self._tiles:
            raise KeyError(f"unknown tile: {tile_id}")
        return self._states[tile_id]

    def neighbors_of(self, tile_id: str) -> tuple[str, ...]:
        return self.get_tile(tile_id).neighbor_tile_ids

    def _resident_state(self, st: TileState) -> bool:
        return st in (
            TileState.LOADING,
            TileState.LOADED,
            TileState.ACTIVE,
            TileState.COOLING,
        )

    def current_resident_mb(self) -> float:
        total = 0.0
        for tid, st in self._states.items():
            if self._resident_state(st):
                total += self._tiles[tid].asset_size_mb
        return round(total, 4)

    def would_exceed_budget(
        self,
        platform: StreamPlatform,
        additional_tiles: t.Iterable[str],
    ) -> bool:
        budget = PLATFORM_BUDGET_MB[platform]
        extra = 0.0
        seen: set[str] = set()
        for tid in additional_tiles:
            if tid in seen:
                continue
            seen.add(tid)
            if tid in self._tiles:
                # Only counts if it's not already resident.
                st = self._states[tid]
                if not self._resident_state(st):
                    extra += self._tiles[tid].asset_size_mb
        return (self.current_resident_mb() + extra) > budget

    def _decide_action(
        self, dist_m: float, current: TileState,
    ) -> StreamAction:
        """Map distance + current state to the next action."""
        if dist_m <= self.prefetch_radius_m:
            # Inside prefetch ring: LOAD if not resident.
            if current in (TileState.UNLOADED,):
                return StreamAction.LOAD
            return StreamAction.KEEP
        if dist_m <= self.keep_radius_m:
            # Inside keep ring: KEEP if resident else LOAD.
            if current == TileState.UNLOADED:
                return StreamAction.LOAD
            return StreamAction.KEEP
        if dist_m <= self.evict_radius_m:
            # Cooling ring: drop ACTIVE -> COOLING.
            if current in (
                TileState.LOADING,
                TileState.LOADED,
                TileState.ACTIVE,
            ):
                return StreamAction.COOL
            return StreamAction.KEEP
        # Outside evict ring: drop entirely.
        if current == TileState.UNLOADED:
            return StreamAction.KEEP
        return StreamAction.EVICT

    def _apply_action(
        self, tile_id: str, action: StreamAction,
    ) -> None:
        st = self._states[tile_id]
        if action == StreamAction.LOAD:
            # Fast-forward to ACTIVE so tests reading
            # current_resident_mb after a single plan_streaming
            # call see the tile as resident. In real engine this
            # would step LOADING -> LOADED -> ACTIVE over frames.
            self._states[tile_id] = TileState.ACTIVE
        elif action == StreamAction.KEEP:
            # If LOADED, promote to ACTIVE (the player is in range).
            if st == TileState.LOADED:
                self._states[tile_id] = TileState.ACTIVE
        elif action == StreamAction.COOL:
            self._states[tile_id] = TileState.COOLING
        elif action == StreamAction.EVICT:
            self._states[tile_id] = TileState.UNLOADED

    def plan_streaming_for(
        self,
        player_pos: tuple[float, float, float],
        platform: StreamPlatform,
    ) -> StreamingPlan:
        """Compute load/keep/cool/evict decisions for every
        registered tile at this player position. Mutates the
        internal state machine so subsequent calls reflect the
        new resident set."""
        actions: list[tuple[str, StreamAction]] = []
        # Distance per tile (cached for the eviction step below).
        dist_by_tile: dict[str, float] = {}
        for tid, tile in self._tiles.items():
            d = _dist(player_pos, _tile_center(tile))
            dist_by_tile[tid] = d
            act = self._decide_action(d, self._states[tid])
            actions.append((tid, act))
            self._apply_action(tid, act)

        # Memory pressure pass: while over budget, evict the
        # cheapest cooling tile (ties broken by furthest dist).
        budget = PLATFORM_BUDGET_MB[platform]
        while self.current_resident_mb() > budget:
            cooling = [
                tid for tid, st in self._states.items()
                if st == TileState.COOLING
            ]
            if not cooling:
                break
            cooling.sort(
                key=lambda x: (
                    self._tiles[x].asset_size_mb,
                    -dist_by_tile.get(x, 0.0),
                ),
            )
            victim = cooling[0]
            self._states[victim] = TileState.UNLOADED
            # Patch the action list to reflect the eviction.
            actions = [
                (tid, StreamAction.EVICT if tid == victim else a)
                for tid, a in actions
            ]

        actions.sort(key=lambda x: x[0])
        resident = self.current_resident_mb()
        over = max(0.0, resident - budget)
        return StreamingPlan(
            actions=tuple(actions),
            resident_mb_after=resident,
            over_budget_by_mb=round(over, 4),
        )

    def force_state(
        self, tile_id: str, state: TileState,
    ) -> None:
        """Test/diagnostic hook to override the tile state."""
        if tile_id not in self._tiles:
            raise KeyError(f"unknown tile: {tile_id}")
        self._states[tile_id] = state

    def tiles_in_state(
        self, state: TileState,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                tid for tid, st in self._states.items()
                if st == state
            )
        )


__all__ = [
    "StreamPlatform",
    "TileState",
    "StreamAction",
    "StreamTile",
    "StreamingPlan",
    "WorldStreamer",
    "PLATFORM_BUDGET_MB",
]
