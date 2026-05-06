"""Biome simultaneous events — coordinated cross-biome triggers.

When something big happens in one biome, the others should
react. A beastmen siege on Bastok shouldn't be a quiet
moment for the navy — naval blockades and aerial raids
should fire at the same time, so players who don't want
to defend the gates can find equally meaningful work in
the other theatres.

An EventChain has:
    primary  - the trigger event (siege start, etc.)
    facets   - other-biome events that fire on activation
    duration - how long the chain stays active
    decay    - per-second contribution decay (so getting
               there late is less rewarding)

Each facet has its own (biome, event_kind) and accumulates
contribution_points from participants. start() activates
the chain; end() resolves and snapshots the final
contribution table for downstream loot/honor systems.

Public surface
--------------
    EventBiome enum
    EventKind enum
    EventFacet dataclass (frozen)
    SimultaneousEvent
    BiomeSimultaneousEvents
        .register_chain(chain_id, primary_biome, primary_kind,
                        facets, duration_seconds)
        .start(chain_id, now_seconds)
        .contribute(chain_id, player_id, biome, points,
                    now_seconds)
        .end(chain_id, now_seconds)
        .contributions(chain_id) -> dict[str, int]
        .is_active(chain_id, now_seconds) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EventBiome(str, enum.Enum):
    SURFACE = "surface"
    DEEP = "deep"
    SKY = "sky"


class EventKind(str, enum.Enum):
    SIEGE = "siege"
    NAVAL_BLOCKADE = "naval_blockade"
    SUB_INCURSION = "sub_incursion"
    AERIAL_RAID = "aerial_raid"
    DRAGON_DESCENT = "dragon_descent"
    KRAKEN_SURFACING = "kraken_surfacing"


# contributions earned more than this many seconds after the
# event started decay each second by DECAY_PER_SECOND
# (so showing up at minute 1 vs minute 30 matters)
DECAY_AFTER_SECONDS = 60
DECAY_PER_SECOND = 0.01  # multiplicative; 1% off per sec late


@dataclasses.dataclass(frozen=True)
class EventFacet:
    biome: EventBiome
    kind: EventKind


@dataclasses.dataclass
class _ChainState:
    chain_id: str
    primary: EventFacet
    facets: list[EventFacet]
    duration_seconds: int
    started_at: t.Optional[int] = None
    ended_at: t.Optional[int] = None
    # player_id -> accumulated points (already decay-adjusted)
    contributions: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass(frozen=True)
class SimultaneousEvent:
    chain_id: str
    primary: EventFacet
    facets: tuple[EventFacet, ...]
    duration_seconds: int


@dataclasses.dataclass
class BiomeSimultaneousEvents:
    _chains: dict[str, _ChainState] = dataclasses.field(default_factory=dict)

    def register_chain(
        self, *, chain_id: str,
        primary_biome: EventBiome,
        primary_kind: EventKind,
        facets: t.Iterable[EventFacet],
        duration_seconds: int,
    ) -> bool:
        if not chain_id or chain_id in self._chains:
            return False
        if duration_seconds <= 0:
            return False
        self._chains[chain_id] = _ChainState(
            chain_id=chain_id,
            primary=EventFacet(biome=primary_biome, kind=primary_kind),
            facets=list(facets),
            duration_seconds=duration_seconds,
        )
        return True

    def start(
        self, *, chain_id: str, now_seconds: int,
    ) -> bool:
        c = self._chains.get(chain_id)
        if c is None or c.started_at is not None:
            return False
        c.started_at = now_seconds
        return True

    def contribute(
        self, *, chain_id: str, player_id: str,
        biome: EventBiome, points: int,
        now_seconds: int,
    ) -> bool:
        c = self._chains.get(chain_id)
        if c is None or c.started_at is None or c.ended_at is not None:
            return False
        # contributions only count if the biome matches primary or a facet
        valid_biomes = {c.primary.biome} | {f.biome for f in c.facets}
        if biome not in valid_biomes:
            return False
        # event has expired?
        if (now_seconds - c.started_at) >= c.duration_seconds:
            return False
        # decay: contributions made > DECAY_AFTER_SECONDS in are docked
        elapsed_into = max(0, now_seconds - c.started_at)
        if elapsed_into > DECAY_AFTER_SECONDS:
            late_seconds = elapsed_into - DECAY_AFTER_SECONDS
            multiplier = max(0.0, 1.0 - DECAY_PER_SECOND * late_seconds)
        else:
            multiplier = 1.0
        adjusted = points * multiplier
        c.contributions[player_id] = (
            c.contributions.get(player_id, 0.0) + adjusted
        )
        return True

    def end(
        self, *, chain_id: str, now_seconds: int,
    ) -> bool:
        c = self._chains.get(chain_id)
        if c is None or c.started_at is None or c.ended_at is not None:
            return False
        c.ended_at = now_seconds
        return True

    def contributions(
        self, *, chain_id: str,
    ) -> dict[str, int]:
        c = self._chains.get(chain_id)
        if c is None:
            return {}
        return {p: int(v) for p, v in c.contributions.items()}

    def is_active(
        self, *, chain_id: str, now_seconds: int,
    ) -> bool:
        c = self._chains.get(chain_id)
        if c is None or c.started_at is None:
            return False
        if c.ended_at is not None:
            return False
        return (now_seconds - c.started_at) < c.duration_seconds


__all__ = [
    "EventBiome", "EventKind", "EventFacet",
    "SimultaneousEvent", "BiomeSimultaneousEvents",
    "DECAY_AFTER_SECONDS", "DECAY_PER_SECOND",
]
