"""Entity gossip propagation — hobby observations spread.

When players witness an entity at a hobby, that knowledge
starts as a private discovery. Over time, observations
propagate through the NPC gossip network — innkeepers and
moogle dispatchers act as gossip_hubs that accelerate the
spread. After enough total observations of a (entity, hobby)
pair, the knowledge becomes public and any NPC will
acknowledge it in dialog.

This is the back-end of "the world has weekends": eventually
everyone in town knows that Volker fishes Tuesday mornings,
and they'll bring it up if a player asks about him.

Public surface
--------------
    GossipTier enum
    GossipFact dataclass (frozen)
    EntityGossipPropagationSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.entity_hobbies import HobbyKind


_TIER_THRESHOLDS = (
    (0, "private"),
    (5, "neighborhood"),
    (20, "town"),
    (50, "regional"),
    (150, "famous"),
)
_HUB_BOOST = 5


class GossipTier(str, enum.Enum):
    PRIVATE = "private"
    NEIGHBORHOOD = "neighborhood"
    TOWN = "town"
    REGIONAL = "regional"
    FAMOUS = "famous"


@dataclasses.dataclass(frozen=True)
class GossipFact:
    fact_id: str
    entity_id: str
    hobby: HobbyKind
    spread_score: int
    distinct_witnesses: int


def _tier_for_score(score: int) -> GossipTier:
    label = "private"
    for thresh, name in _TIER_THRESHOLDS:
        if score >= thresh:
            label = name
    return GossipTier(label)


@dataclasses.dataclass
class EntityGossipPropagationSystem:
    _facts: dict[tuple[str, str], GossipFact] = (
        dataclasses.field(default_factory=dict)
    )
    _witnesses: dict[
        tuple[str, str], set[str]
    ] = dataclasses.field(default_factory=dict)
    _gossip_hubs: set[str] = dataclasses.field(
        default_factory=set,
    )
    _next: int = 1

    def register_gossip_hub(
        self, *, npc_id: str,
    ) -> bool:
        if not npc_id:
            return False
        if npc_id in self._gossip_hubs:
            return False
        self._gossip_hubs.add(npc_id)
        return True

    def record_observation(
        self, *, entity_id: str, hobby: HobbyKind,
        witness_id: str, propagator_npc_id: str = "",
    ) -> bool:
        """Record a witness event. propagator_npc_id
        is the NPC who first heard about it (if not
        empty, and they're a registered hub, gossip
        propagation gets a boost).
        """
        if not entity_id or not witness_id:
            return False
        key = (entity_id, hobby.value)
        wkey = key
        if wkey not in self._witnesses:
            self._witnesses[wkey] = set()
        is_new_witness = (
            witness_id not in self._witnesses[wkey]
        )
        self._witnesses[wkey].add(witness_id)
        cur = self._facts.get(key)
        delta = 1
        if (
            propagator_npc_id
            and propagator_npc_id in self._gossip_hubs
        ):
            delta += _HUB_BOOST
        if cur is None:
            self._facts[key] = GossipFact(
                fact_id=f"fact_{self._next}",
                entity_id=entity_id, hobby=hobby,
                spread_score=delta,
                distinct_witnesses=(
                    1 if is_new_witness else 0
                ),
            )
            self._next += 1
        else:
            self._facts[key] = dataclasses.replace(
                cur, spread_score=(
                    cur.spread_score + delta
                ),
                distinct_witnesses=(
                    cur.distinct_witnesses
                    + (1 if is_new_witness else 0)
                ),
            )
        return True

    def fact(
        self, *, entity_id: str, hobby: HobbyKind,
    ) -> t.Optional[GossipFact]:
        return self._facts.get(
            (entity_id, hobby.value),
        )

    def tier(
        self, *, entity_id: str, hobby: HobbyKind,
    ) -> GossipTier:
        f = self.fact(
            entity_id=entity_id, hobby=hobby,
        )
        if f is None:
            return GossipTier.PRIVATE
        return _tier_for_score(f.spread_score)

    def is_public_knowledge(
        self, *, entity_id: str, hobby: HobbyKind,
    ) -> bool:
        """At TOWN tier or higher, NPCs will mention
        the fact in dialog without prompting.
        """
        tier_ = self.tier(
            entity_id=entity_id, hobby=hobby,
        )
        return tier_ in (
            GossipTier.TOWN, GossipTier.REGIONAL,
            GossipTier.FAMOUS,
        )

    def is_gossip_hub(
        self, *, npc_id: str,
    ) -> bool:
        return npc_id in self._gossip_hubs

    def known_facts_about(
        self, *, entity_id: str,
    ) -> list[GossipFact]:
        return [
            f for f in self._facts.values()
            if f.entity_id == entity_id
        ]


__all__ = [
    "GossipTier", "GossipFact",
    "EntityGossipPropagationSystem",
]
