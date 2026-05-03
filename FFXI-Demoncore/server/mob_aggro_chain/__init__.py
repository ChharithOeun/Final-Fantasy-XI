"""Mob aggro chain — same-family link-aggro.

When a goblin in a pack pulls aggro, the nearby goblins ALSO
charge. Aggro is a SOCIAL signal between same-family mobs, not
just a per-individual trigger. This module models the
chain-aggro propagation:

* When mob A aggros, scan nearby mobs of the same family.
* Each candidate within `link_range` rolls a chain-link check
  scaled by how mobs.LINK_AFFINITY (loyal mobs link more
  reliably; lone-wolf families don't link at all).
* Linked mobs aggro the same target, but each link costs a
  small "shout cooldown" so a mob can't trigger multiple chains
  in rapid succession.

LINK_AFFINITY tiers
-------------------
    PACK         (1.0)  — orcs, goblins, wild dogs: high link
    FAMILY       (0.7)  — yagudo, sahagin: same-tribe link
    OPPORTUNIST  (0.4)  — undead, demons: only link under stress
    LONE_WOLF    (0.0)  — bombs, dragons, dhalmel: never link

Public surface
--------------
    LinkAffinity enum
    MobLinkProfile dataclass — per-mob link config
    AggroChainEvent dataclass — original aggro
    ChainResult dataclass — list of mobs that joined
    MobAggroChainRegistry
        .register_mob(profile)
        .resolve_chain(aggro_event, candidates, rng)
            -> ChainResult
"""
from __future__ import annotations

import dataclasses
import enum
import math
import random
import typing as t


# Per-link shout cooldown — a mob can't kick off another chain
# within this window after participating in one.
DEFAULT_SHOUT_COOLDOWN_SECONDS = 30.0


class LinkAffinity(str, enum.Enum):
    PACK = "pack"
    FAMILY = "family"
    OPPORTUNIST = "opportunist"
    LONE_WOLF = "lone_wolf"


_AFFINITY_TO_PROBABILITY: dict[LinkAffinity, float] = {
    LinkAffinity.PACK: 1.0,
    LinkAffinity.FAMILY: 0.7,
    LinkAffinity.OPPORTUNIST: 0.4,
    LinkAffinity.LONE_WOLF: 0.0,
}


def affinity_probability(aff: LinkAffinity) -> float:
    return _AFFINITY_TO_PROBABILITY[aff]


@dataclasses.dataclass(frozen=True)
class MobLinkProfile:
    mob_id: str
    family_id: str
    position_tile: tuple[int, int]
    link_affinity: LinkAffinity = LinkAffinity.FAMILY
    link_range_tiles: int = 15
    is_alive: bool = True


@dataclasses.dataclass(frozen=True)
class AggroChainEvent:
    instigator_mob_id: str
    target_player_id: str
    occurred_at_seconds: float


@dataclasses.dataclass(frozen=True)
class ChainResult:
    instigator_mob_id: str
    target_player_id: str
    linked_mob_ids: tuple[str, ...]
    skipped_mob_ids: tuple[str, ...]
    notes: str = ""


@dataclasses.dataclass
class MobAggroChainRegistry:
    shout_cooldown_seconds: float = DEFAULT_SHOUT_COOLDOWN_SECONDS
    _profiles: dict[str, MobLinkProfile] = dataclasses.field(
        default_factory=dict,
    )
    _last_shout_at: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )

    def register_mob(
        self, profile: MobLinkProfile,
    ) -> MobLinkProfile:
        self._profiles[profile.mob_id] = profile
        return profile

    def get(self, mob_id: str) -> t.Optional[MobLinkProfile]:
        return self._profiles.get(mob_id)

    def kill_mob(self, *, mob_id: str) -> bool:
        p = self._profiles.get(mob_id)
        if p is None:
            return False
        self._profiles[mob_id] = dataclasses.replace(
            p, is_alive=False,
        )
        return True

    def _within_range(
        self, *, a: tuple[int, int], b: tuple[int, int],
        max_distance: int,
    ) -> bool:
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= max_distance

    def _under_cooldown(
        self, *, mob_id: str, now_seconds: float,
    ) -> bool:
        last = self._last_shout_at.get(mob_id)
        if last is None:
            return False
        return (now_seconds - last) < self.shout_cooldown_seconds

    def resolve_chain(
        self, *, aggro_event: AggroChainEvent,
        rng: t.Optional[random.Random] = None,
    ) -> ChainResult:
        rng = rng or random.Random()
        instigator = self._profiles.get(
            aggro_event.instigator_mob_id,
        )
        if instigator is None:
            return ChainResult(
                instigator_mob_id=aggro_event.instigator_mob_id,
                target_player_id=aggro_event.target_player_id,
                linked_mob_ids=(), skipped_mob_ids=(),
                notes="instigator unknown",
            )
        # Lone wolf can't kick off chains — but its OWN aggro is
        # still recorded.
        if instigator.link_affinity == LinkAffinity.LONE_WOLF:
            self._last_shout_at[
                aggro_event.instigator_mob_id
            ] = aggro_event.occurred_at_seconds
            return ChainResult(
                instigator_mob_id=aggro_event.instigator_mob_id,
                target_player_id=aggro_event.target_player_id,
                linked_mob_ids=(), skipped_mob_ids=(),
                notes="lone wolf — no chain",
            )
        # Already shouted recently — chain blocked
        if self._under_cooldown(
            mob_id=aggro_event.instigator_mob_id,
            now_seconds=aggro_event.occurred_at_seconds,
        ):
            return ChainResult(
                instigator_mob_id=aggro_event.instigator_mob_id,
                target_player_id=aggro_event.target_player_id,
                linked_mob_ids=(), skipped_mob_ids=(),
                notes="instigator on shout cooldown",
            )
        linked: list[str] = []
        skipped: list[str] = []
        # Walk all alive same-family mobs within range
        for mob_id, profile in self._profiles.items():
            if mob_id == instigator.mob_id:
                continue
            if not profile.is_alive:
                continue
            if profile.family_id != instigator.family_id:
                continue
            if profile.link_affinity == LinkAffinity.LONE_WOLF:
                skipped.append(mob_id)
                continue
            distance = math.hypot(
                profile.position_tile[0]
                - instigator.position_tile[0],
                profile.position_tile[1]
                - instigator.position_tile[1],
            )
            if distance > min(
                instigator.link_range_tiles,
                profile.link_range_tiles,
            ):
                skipped.append(mob_id)
                continue
            if self._under_cooldown(
                mob_id=mob_id,
                now_seconds=aggro_event.occurred_at_seconds,
            ):
                skipped.append(mob_id)
                continue
            # Probability check — use the LOWER of the two
            # affinities (the cautious mob in the link)
            prob = min(
                affinity_probability(instigator.link_affinity),
                affinity_probability(profile.link_affinity),
            )
            if rng.random() <= prob:
                linked.append(mob_id)
                self._last_shout_at[
                    mob_id
                ] = aggro_event.occurred_at_seconds
            else:
                skipped.append(mob_id)
        # Mark instigator on cooldown
        self._last_shout_at[
            aggro_event.instigator_mob_id
        ] = aggro_event.occurred_at_seconds
        return ChainResult(
            instigator_mob_id=aggro_event.instigator_mob_id,
            target_player_id=aggro_event.target_player_id,
            linked_mob_ids=tuple(linked),
            skipped_mob_ids=tuple(skipped),
        )

    def total_mobs(self) -> int:
        return len(self._profiles)


__all__ = [
    "DEFAULT_SHOUT_COOLDOWN_SECONDS",
    "LinkAffinity", "affinity_probability",
    "MobLinkProfile", "AggroChainEvent", "ChainResult",
    "MobAggroChainRegistry",
]
