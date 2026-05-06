"""Habitat disturbance — adversaries swoop in when the
environment breaks open.

Big battles tear holes in the world. A breach in the north
wall doesn't just give the boss room more square footage;
it exposes whatever was on the OTHER side of that wall.
A flooded chamber suddenly disgorges the creatures that
lived in the dam reservoir. A collapsed ceiling drops
roosting bats into the fight. A hull breach lets the kraken
the ship had been outrunning slip a tentacle in.

This module is a habitat-graph + spawn dispatcher:

    register_habitat(habitat_id, creatures, ambush_chance,
                     biome_tags)
    register_arena_habitat_link(arena_id, feature_id,
                                habitat_id, disturbance_threshold)
    on_feature_break(arena_id, feature_id) -> tuple[Spawn]

When a feature breaks, we look up which habitats are
linked to it. Each habitat has a `disturbance_threshold`
(damage required to actually wake them up) and an
ambush_chance — once awoken, an RNG roll decides whether
they actually attack THIS round.

Each habitat has a CREATURE POOL — not a single mob, but
a list of weighted candidates. The disturbance picks
1..max_swoop creatures and emits Spawn records the
encounter system uses.

The disturbance score is cumulative: every TIME the
linked feature takes damage, the habitat accumulates
agitation. The first time accum >= threshold, the
ambush rolls. Subsequent damage cooldowns to prevent
infinite spawns from the same habitat.

Public surface
--------------
    HabitatBiome enum
    Habitat dataclass (frozen)
    Spawn dataclass (frozen)
    HabitatDisturbance
        .register_habitat(habitat_id, ...)
        .link_habitat_to_feature(arena_id, feature_id,
                                 habitat_id, threshold)
        .accumulate_damage(arena_id, feature_id, amount, now_seconds)
            -> tuple[Spawn, ...]
        .reset(arena_id)
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


class HabitatBiome(str, enum.Enum):
    UNDERSEA = "undersea"
    KELP_FOREST = "kelp_forest"
    CAVE = "cave"
    SHIPWRECK = "shipwreck"
    SKY_NEST = "sky_nest"
    FROZEN_DEEP = "frozen_deep"
    LAVA_VENT = "lava_vent"
    JUNGLE_CANOPY = "jungle_canopy"


# Once an ambush has fired from a habitat, it can't fire again
# for this many seconds (per habitat per arena).
HABITAT_REARM_SECONDS = 120


@dataclasses.dataclass(frozen=True)
class Habitat:
    habitat_id: str
    biome: HabitatBiome
    # weighted creature pool: {creature_id: weight}
    creatures: dict[str, int]
    max_swoop: int = 3
    ambush_chance_pct: int = 60   # 0..100


@dataclasses.dataclass(frozen=True)
class Spawn:
    habitat_id: str
    creature_id: str
    arena_id: str
    feature_id: str
    biome: HabitatBiome
    spawned_at: int


@dataclasses.dataclass
class _HabitatLink:
    habitat_id: str
    threshold: int
    accumulated: int = 0
    fired: bool = False
    last_fired_at: int = -10_000_000


@dataclasses.dataclass
class HabitatDisturbance:
    rng_seed: int = 0
    _habitats: dict[str, Habitat] = dataclasses.field(default_factory=dict)
    _links: dict[tuple[str, str], list[_HabitatLink]] = dataclasses.field(
        default_factory=dict,
    )
    _rng: random.Random = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.rng_seed)

    def register_habitat(
        self, *, habitat_id: str,
        biome: HabitatBiome,
        creatures: dict[str, int],
        max_swoop: int = 3,
        ambush_chance_pct: int = 60,
    ) -> bool:
        if not habitat_id or habitat_id in self._habitats:
            return False
        if not creatures:
            return False
        if any(w <= 0 for w in creatures.values()):
            return False
        if max_swoop < 1:
            return False
        if not (0 <= ambush_chance_pct <= 100):
            return False
        self._habitats[habitat_id] = Habitat(
            habitat_id=habitat_id, biome=biome,
            creatures=dict(creatures),
            max_swoop=max_swoop,
            ambush_chance_pct=ambush_chance_pct,
        )
        return True

    def link_habitat_to_feature(
        self, *, arena_id: str, feature_id: str,
        habitat_id: str, threshold: int,
    ) -> bool:
        if habitat_id not in self._habitats:
            return False
        if threshold <= 0:
            return False
        key = (arena_id, feature_id)
        bag = self._links.setdefault(key, [])
        # don't double-link
        if any(L.habitat_id == habitat_id for L in bag):
            return False
        bag.append(_HabitatLink(habitat_id=habitat_id, threshold=threshold))
        return True

    def accumulate_damage(
        self, *, arena_id: str, feature_id: str,
        amount: int, now_seconds: int,
    ) -> tuple[Spawn, ...]:
        if amount <= 0:
            return ()
        bag = self._links.get((arena_id, feature_id))
        if not bag:
            return ()
        out: list[Spawn] = []
        for L in bag:
            if L.fired and (now_seconds - L.last_fired_at) < HABITAT_REARM_SECONDS:
                continue
            if L.fired and (now_seconds - L.last_fired_at) >= HABITAT_REARM_SECONDS:
                # rearm — reset accumulator
                L.fired = False
                L.accumulated = 0
            L.accumulated += amount
            if L.accumulated < L.threshold:
                continue
            # roll for ambush
            hab = self._habitats[L.habitat_id]
            if self._rng.randint(1, 100) > hab.ambush_chance_pct:
                # missed roll — still consume the threshold so the
                # next damage tick can roll again
                L.accumulated = 0
                continue
            # ambush fires
            L.fired = True
            L.last_fired_at = now_seconds
            count = self._rng.randint(1, hab.max_swoop)
            picks = self._weighted_picks(hab.creatures, count)
            for cid in picks:
                out.append(Spawn(
                    habitat_id=hab.habitat_id,
                    creature_id=cid,
                    arena_id=arena_id,
                    feature_id=feature_id,
                    biome=hab.biome,
                    spawned_at=now_seconds,
                ))
        return tuple(out)

    def _weighted_picks(
        self, pool: dict[str, int], count: int,
    ) -> list[str]:
        ids = list(pool.keys())
        weights = [pool[c] for c in ids]
        # WITH replacement — same creature can swoop in multiples
        return self._rng.choices(ids, weights=weights, k=count)

    def reset(self, *, arena_id: str) -> bool:
        any_reset = False
        for (aid, _fid), bag in self._links.items():
            if aid != arena_id:
                continue
            for L in bag:
                L.accumulated = 0
                L.fired = False
                L.last_fired_at = -10_000_000
            any_reset = True
        return any_reset


__all__ = [
    "HabitatBiome", "Habitat", "Spawn",
    "HabitatDisturbance",
    "HABITAT_REARM_SECONDS",
]
