"""Harvest competitor AI — NPC harvesters compete with players.

In retail FFXI, mining/logging/harvesting points respawn on a
fixed timer regardless of how many people are using them. In
Demoncore, AI-driven NPC harvesters work the same nodes. They
compete with players for limited resources, and their output
flows into economy_supply_index.

This means:

* A famous fishing spot has 5 NPC fishermen who fish there
  every day. If you show up, you have to wait or fish a less
  busy hole.
* A copper vein in Palborough Mines has Quadav harvesters that
  work it; clearing the Quadav opens up the node briefly.
* Crystal-rich zones are crowded — being able to "claim" a
  node by getting there first matters.

Node lifecycle
--------------
A `HarvestNode` has a `capacity` (max units before depletion)
and a `regen_rate` (units per game-hour). Each NPC harvester
working it consumes at their own rate. Players join the queue.
When a node hits capacity 0, it goes DEPLETED and stops
producing until regen_rate refills it.

Harvest output flows into economy_supply_index as
`MOB_DROP_EXPECTED` (the most generic supply source — the
regulator doesn't need to distinguish NPC vs. player harvest).

Public surface
--------------
    NodeKind enum (MINING / LOGGING / FISHING / HARVESTING /
                    EXCAVATION / GARDENING)
    NodeStatus enum (HEALTHY / STRAINED / DEPLETED)
    HarvestNode dataclass
    NPCHarvester dataclass
    HarvestEvent dataclass
    HarvestCompetitorRegistry
        .register_node(...)
        .add_npc_harvester(node_id, harvester)
        .tick(now_seconds) — runs the simulation
        .player_harvest(player_id, node_id, units)
        .node_status(node_id) -> NodeStatus
        .output_for(node_id) -> total units extracted
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


HEALTHY_THRESHOLD = 0.6      # >60% capacity = healthy
DEPLETED_THRESHOLD = 0.0     # 0 = depleted


class NodeKind(str, enum.Enum):
    MINING = "mining"
    LOGGING = "logging"
    FISHING = "fishing"
    HARVESTING = "harvesting"
    EXCAVATION = "excavation"
    GARDENING = "gardening"


class NodeStatus(str, enum.Enum):
    HEALTHY = "healthy"
    STRAINED = "strained"
    DEPLETED = "depleted"


@dataclasses.dataclass
class HarvestNode:
    node_id: str
    kind: NodeKind
    item_id: str
    zone_id: str
    capacity_max: int
    capacity_current: int
    # Per-game-hour regeneration in units; nodes "fill" toward
    # capacity_max.
    regen_rate_per_hour: float = 5.0
    # When the node hit capacity 0, when does it COME BACK?
    last_tick_at_seconds: float = 0.0
    last_depleted_at_seconds: t.Optional[float] = None
    output_units_lifetime: int = 0

    def status(self) -> NodeStatus:
        if self.capacity_current <= DEPLETED_THRESHOLD:
            return NodeStatus.DEPLETED
        ratio = self.capacity_current / max(1, self.capacity_max)
        if ratio >= HEALTHY_THRESHOLD:
            return NodeStatus.HEALTHY
        return NodeStatus.STRAINED


@dataclasses.dataclass
class NPCHarvester:
    npc_id: str
    units_per_hour: float
    last_acted_at_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class HarvestEvent:
    node_id: str
    actor_id: str         # npc or player
    units: int
    at_seconds: float


@dataclasses.dataclass(frozen=True)
class HarvestResult:
    accepted: bool
    units: int = 0
    new_capacity: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class HarvestCompetitorRegistry:
    _nodes: dict[str, HarvestNode] = dataclasses.field(
        default_factory=dict,
    )
    _harvesters: dict[
        str, list[NPCHarvester],
    ] = dataclasses.field(default_factory=dict)
    _events: list[HarvestEvent] = dataclasses.field(
        default_factory=list,
    )

    def register_node(self, node: HarvestNode) -> HarvestNode:
        self._nodes[node.node_id] = node
        return node

    def node_for(self, node_id: str) -> t.Optional[HarvestNode]:
        return self._nodes.get(node_id)

    def add_npc_harvester(
        self, *, node_id: str, harvester: NPCHarvester,
    ) -> bool:
        if node_id not in self._nodes:
            return False
        self._harvesters.setdefault(node_id, []).append(harvester)
        return True

    def tick(self, *, now_seconds: float) -> dict[str, int]:
        """Run the simulation forward to now_seconds. Each node
        regenerates capacity, then NPC harvesters extract units.
        Returns counters."""
        regenerated = 0
        npc_extracted = 0
        for node in self._nodes.values():
            elapsed_hours = (
                now_seconds - node.last_tick_at_seconds
            ) / 3600.0
            if elapsed_hours <= 0:
                continue
            # Regenerate
            regen_amount = int(
                node.regen_rate_per_hour * elapsed_hours,
            )
            old = node.capacity_current
            node.capacity_current = min(
                node.capacity_max,
                node.capacity_current + regen_amount,
            )
            regenerated += node.capacity_current - old
            # NPC extraction
            harvesters = self._harvesters.get(node.node_id, [])
            for h in harvesters:
                if node.capacity_current <= 0:
                    break
                npc_units = int(h.units_per_hour * elapsed_hours)
                if npc_units <= 0:
                    continue
                taken = min(npc_units, node.capacity_current)
                node.capacity_current -= taken
                node.output_units_lifetime += taken
                npc_extracted += taken
                h.last_acted_at_seconds = now_seconds
                self._events.append(HarvestEvent(
                    node_id=node.node_id, actor_id=h.npc_id,
                    units=taken, at_seconds=now_seconds,
                ))
            if node.capacity_current <= 0:
                node.last_depleted_at_seconds = now_seconds
            node.last_tick_at_seconds = now_seconds
        return {
            "regenerated": regenerated,
            "npc_extracted": npc_extracted,
        }

    def player_harvest(
        self, *, player_id: str, node_id: str,
        units: int = 1, now_seconds: float = 0.0,
    ) -> HarvestResult:
        node = self._nodes.get(node_id)
        if node is None:
            return HarvestResult(False, reason="no such node")
        if units <= 0:
            return HarvestResult(False, reason="must harvest >0")
        if node.capacity_current <= 0:
            return HarvestResult(
                False, reason="node depleted",
                new_capacity=node.capacity_current,
            )
        taken = min(units, node.capacity_current)
        node.capacity_current -= taken
        node.output_units_lifetime += taken
        if node.capacity_current <= 0:
            node.last_depleted_at_seconds = now_seconds
        self._events.append(HarvestEvent(
            node_id=node_id, actor_id=player_id, units=taken,
            at_seconds=now_seconds,
        ))
        return HarvestResult(
            accepted=True, units=taken,
            new_capacity=node.capacity_current,
        )

    def node_status(self, node_id: str) -> t.Optional[NodeStatus]:
        node = self._nodes.get(node_id)
        return node.status() if node else None

    def output_for(self, node_id: str) -> int:
        node = self._nodes.get(node_id)
        return node.output_units_lifetime if node else 0

    def events_at_node(
        self, node_id: str,
    ) -> tuple[HarvestEvent, ...]:
        return tuple(
            e for e in self._events if e.node_id == node_id
        )

    def total_events(self) -> int:
        return len(self._events)

    def total_nodes(self) -> int:
        return len(self._nodes)

    def npc_harvester_count(self, node_id: str) -> int:
        return len(self._harvesters.get(node_id, []))


__all__ = [
    "HEALTHY_THRESHOLD", "DEPLETED_THRESHOLD",
    "NodeKind", "NodeStatus",
    "HarvestNode", "NPCHarvester", "HarvestEvent",
    "HarvestResult", "HarvestCompetitorRegistry",
]
