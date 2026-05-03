"""Rumor propagation — gossip across the NPC network.

Significant events become rumors. Rumors hop NPC-to-NPC along
a "social adjacency" graph (NPCs in the same tavern share gossip;
caravan masters carry news between cities; linkshell members
relay news to faraway NPCs of the same affinity). After a few
days of game-time the news reaches a town three zones away —
NPCs there react to the player even though they've never met.

The system is deliberately STATE-MACHINE-shaped, not LLM-driven.
The orchestrator can layer flavor on the rumor when it's spoken
aloud to the player, but the SPREAD is deterministic so testing
and balance work. AI agents observing rumors can discount or
amplify based on their personality (a CUNNING NPC trusts rumors
less; a LOYAL NPC believes them more).

Rumor model
-----------
A `Rumor` is an event that happened to a SPECIFIC SUBJECT (a
player, an NM, a faction, a town). It has:
* an id (rumor_id)
* a tag (RumorKind: PLAYER_KILLED_NM, PLAYER_BETRAYED_NATION,
  PLAYER_HEALED_REFUGEES, NM_RAMPAGE, etc.)
* a subject_id (who the rumor is about)
* an origin_npc_id (who first witnessed)
* a salience [0..100] — how juicy the gossip is
* a fidelity [0..100] — how accurate the retelling is. Decays
  as the rumor passes through nodes.

Spread model
------------
The graph is a directed multigraph where each edge has a
"transmission strength" (0.0..1.0). Each game-tick the rumor
propagation engine:
1) For every (rumor x node it has reached) pair, picks adjacent
   nodes the rumor hasn't reached and rolls a copy with reduced
   fidelity = parent_fidelity * edge_strength.
2) Drops nodes whose fidelity has decayed below a floor.
3) Ages every rumor's salience using exponential decay.

Public surface
--------------
    RumorKind enum
    Rumor dataclass — frozen, the gossip atom
    NodeKind enum (NPC / FACTION / SETTLEMENT)
    SocialEdge dataclass
    SocialGraph
        .add_node / .add_edge
        .neighbors(node_id)
    RumorPropagationEngine
        .seed(rumor, origin_npc_id)
        .tick(now_seconds, rng)
        .rumors_at(node_id) -> list[(Rumor, fidelity)]
        .reach_of(rumor_id) -> set of node ids
        .compact_old(now_seconds, max_age_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


# Default tunables.
FIDELITY_FLOOR = 5
RUMOR_DEFAULT_SALIENCE = 50
RUMOR_DEFAULT_FIDELITY = 100
SALIENCE_DECAY_PER_TICK = 2     # subtractive, per tick of propagation


class RumorKind(str, enum.Enum):
    PLAYER_KILLED_NM = "player_killed_nm"
    PLAYER_KILLED_BOSS = "player_killed_boss"
    PLAYER_BETRAYED_NATION = "player_betrayed_nation"
    PLAYER_PARDONED_BY_NATION = "player_pardoned_by_nation"
    PLAYER_HEALED_REFUGEES = "player_healed_refugees"
    PLAYER_BECAME_OUTLAW = "player_became_outlaw"
    PLAYER_FREED_PRISONER = "player_freed_prisoner"
    NM_RAMPAGE = "nm_rampage"
    BEASTMEN_RAID = "beastmen_raid"
    NATION_DECLARED_WAR = "nation_declared_war"
    SHOP_OPENED = "shop_opened"
    SETTLEMENT_BURNED = "settlement_burned"
    HERO_RETURNED = "hero_returned"


class NodeKind(str, enum.Enum):
    NPC = "npc"
    FACTION = "faction"           # entire tribe / nation / guild
    SETTLEMENT = "settlement"     # a town's "general gossip" sink


@dataclasses.dataclass(frozen=True)
class Rumor:
    rumor_id: str
    kind: RumorKind
    subject_id: str
    origin_npc_id: str
    salience: int = RUMOR_DEFAULT_SALIENCE
    fidelity: int = RUMOR_DEFAULT_FIDELITY
    created_at_seconds: float = 0.0
    summary: str = ""

    def with_fidelity(self, new_fidelity: int) -> "Rumor":
        return dataclasses.replace(self, fidelity=new_fidelity)


@dataclasses.dataclass(frozen=True)
class SocialEdge:
    """Directed edge in the gossip graph."""
    src_node_id: str
    dst_node_id: str
    transmission_strength: float    # 0.0..1.0


@dataclasses.dataclass
class SocialGraph:
    _nodes: dict[str, NodeKind] = dataclasses.field(
        default_factory=dict,
    )
    _edges: list[SocialEdge] = dataclasses.field(default_factory=list)

    def add_node(self, *, node_id: str, kind: NodeKind) -> None:
        self._nodes[node_id] = kind

    def add_edge(
        self, *, src: str, dst: str, strength: float = 0.5,
        bidirectional: bool = True,
    ) -> None:
        if not (0.0 <= strength <= 1.0):
            raise ValueError(
                f"strength {strength} out of 0.0-1.0 range",
            )
        # Auto-create endpoint nodes if absent
        for nid in (src, dst):
            if nid not in self._nodes:
                self._nodes[nid] = NodeKind.NPC
        self._edges.append(
            SocialEdge(src_node_id=src, dst_node_id=dst,
                        transmission_strength=strength),
        )
        if bidirectional and src != dst:
            self._edges.append(
                SocialEdge(src_node_id=dst, dst_node_id=src,
                            transmission_strength=strength),
            )

    def neighbors(
        self, node_id: str,
    ) -> tuple[SocialEdge, ...]:
        return tuple(
            e for e in self._edges if e.src_node_id == node_id
        )

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    @property
    def total_nodes(self) -> int:
        return len(self._nodes)


@dataclasses.dataclass
class RumorPropagationEngine:
    graph: SocialGraph = dataclasses.field(default_factory=SocialGraph)
    fidelity_floor: int = FIDELITY_FLOOR
    # Mapping: node_id -> {rumor_id -> Rumor (with current fidelity)}
    _node_to_rumors: dict[
        str, dict[str, Rumor]
    ] = dataclasses.field(default_factory=dict)
    # Master rumor index for compaction & queries
    _rumor_master: dict[str, Rumor] = dataclasses.field(
        default_factory=dict,
    )

    def seed(
        self, *, rumor: Rumor, origin_node_id: str,
    ) -> None:
        """Plant the rumor at its origin node."""
        if not self.graph.has_node(origin_node_id):
            self.graph.add_node(
                node_id=origin_node_id, kind=NodeKind.NPC,
            )
        self._node_to_rumors.setdefault(
            origin_node_id, {},
        )[rumor.rumor_id] = rumor
        self._rumor_master[rumor.rumor_id] = rumor

    def rumors_at(
        self, node_id: str,
    ) -> tuple[tuple[Rumor, int], ...]:
        bucket = self._node_to_rumors.get(node_id, {})
        return tuple(
            (r, r.fidelity) for r in bucket.values()
        )

    def reach_of(self, rumor_id: str) -> frozenset[str]:
        return frozenset(
            node_id for node_id, bucket
            in self._node_to_rumors.items()
            if rumor_id in bucket
        )

    def tick(
        self, *, rng: t.Optional[random.Random] = None,
    ) -> int:
        """Advance one propagation tick. Returns the count of
        new (node, rumor) pairs created this tick."""
        rng = rng or random.Random()
        new_count = 0
        # Build a snapshot to avoid mutating during iteration
        snapshot: list[tuple[str, Rumor]] = []
        for node_id, bucket in self._node_to_rumors.items():
            for r in bucket.values():
                snapshot.append((node_id, r))

        for src_node, rumor in snapshot:
            for edge in self.graph.neighbors(src_node):
                dst = edge.dst_node_id
                # Already has the rumor? Skip.
                if dst in self._node_to_rumors and (
                    rumor.rumor_id in self._node_to_rumors[dst]
                ):
                    continue
                new_fidelity = int(round(
                    rumor.fidelity * edge.transmission_strength,
                ))
                if new_fidelity < self.fidelity_floor:
                    continue
                # Roll for transmission — strength as probability
                if rng.random() > edge.transmission_strength:
                    continue
                copy = rumor.with_fidelity(new_fidelity)
                self._node_to_rumors.setdefault(
                    dst, {},
                )[rumor.rumor_id] = copy
                new_count += 1
        # Salience decay on all rumors held everywhere
        for bucket in self._node_to_rumors.values():
            for rid, r in list(bucket.items()):
                bucket[rid] = dataclasses.replace(
                    r,
                    salience=max(
                        0, r.salience - SALIENCE_DECAY_PER_TICK,
                    ),
                )
        return new_count

    def settle(
        self, *, max_ticks: int = 50,
        rng: t.Optional[random.Random] = None,
    ) -> int:
        """Run propagation until no more spread or max_ticks reached.
        Returns the total spread delta. Useful for tests."""
        total = 0
        for _ in range(max_ticks):
            n = self.tick(rng=rng)
            total += n
            if n == 0:
                break
        return total

    def compact_old(
        self, *, now_seconds: float, max_age_seconds: float,
    ) -> int:
        """Drop rumors older than max_age. Returns count dropped."""
        cutoff = now_seconds - max_age_seconds
        dropped = 0
        for node_id, bucket in list(self._node_to_rumors.items()):
            for rid, r in list(bucket.items()):
                if r.created_at_seconds < cutoff:
                    del bucket[rid]
                    dropped += 1
            if not bucket:
                del self._node_to_rumors[node_id]
        for rid in list(self._rumor_master):
            if self._rumor_master[rid].created_at_seconds < cutoff:
                del self._rumor_master[rid]
        return dropped

    def total_active_rumors(self) -> int:
        return len(self._rumor_master)


__all__ = [
    "FIDELITY_FLOOR", "RUMOR_DEFAULT_SALIENCE",
    "RUMOR_DEFAULT_FIDELITY", "SALIENCE_DECAY_PER_TICK",
    "RumorKind", "Rumor", "NodeKind", "SocialEdge",
    "SocialGraph", "RumorPropagationEngine",
]
