"""Resource depletion — harvest nodes deplete, recover, exhaust.

Mining points, logging trees, fishing holes, and excavation
patches each have a finite SUPPLY and a per-tick RECOVERY rate.
Successful harvests draw down supply; supply replenishes naturally.
But over-farming below a CRITICAL threshold permanently damages the
node — recovery rate halves and the cap drops. Push past the
PERMANENT_EXHAUSTION floor and the node is dead forever.

This wires into harvesting/, fishing/, mat_essentiality_registry/.
The node identity is per-(zone_id, node_id) so the same kind of
node in a different zone has its own state.

Public surface
--------------
    NodeKind enum
    HarvestNode dataclass
    HarvestResult dataclass
    ResourceDepletionRegistry
        .register_node(zone_id, node_id, kind, capacity, recovery)
        .harvest(zone_id, node_id, amount)
        .tick(seconds_elapsed)  -- recovers all nodes
        .state(zone_id, node_id) -> HarvestNode | None
        .is_exhausted(zone_id, node_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default thresholds.
CRITICAL_RATIO = 0.10           # below 10% capacity = damaged
PERMANENT_EXHAUSTION_RATIO = 0.0
DAMAGED_RECOVERY_PENALTY = 0.5  # halves recovery once damaged
DAMAGED_CAPACITY_PENALTY = 0.7  # cap drops to 70% once damaged


class NodeKind(str, enum.Enum):
    MINING = "mining"
    LOGGING = "logging"
    FISHING = "fishing"
    EXCAVATION = "excavation"
    HARVESTING = "harvesting"


class NodeStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DAMAGED = "damaged"      # lower recovery + cap, can revive
    EXHAUSTED = "exhausted"  # permanently dead


@dataclasses.dataclass
class HarvestNode:
    zone_id: str
    node_id: str
    kind: NodeKind
    capacity: int
    current_supply: int
    recovery_per_second: float
    status: NodeStatus = NodeStatus.HEALTHY
    last_tick_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class HarvestResult:
    accepted: bool
    yielded: int = 0
    remaining: int = 0
    new_status: NodeStatus = NodeStatus.HEALTHY
    reason: t.Optional[str] = None


@dataclasses.dataclass
class ResourceDepletionRegistry:
    critical_ratio: float = CRITICAL_RATIO
    damaged_recovery_penalty: float = DAMAGED_RECOVERY_PENALTY
    damaged_capacity_penalty: float = DAMAGED_CAPACITY_PENALTY
    _nodes: dict[tuple[str, str], HarvestNode] = dataclasses.field(
        default_factory=dict,
    )

    def register_node(
        self, *, zone_id: str, node_id: str,
        kind: NodeKind, capacity: int,
        recovery_per_second: float,
        starting_supply: t.Optional[int] = None,
    ) -> t.Optional[HarvestNode]:
        key = (zone_id, node_id)
        if key in self._nodes:
            return None
        if capacity <= 0 or recovery_per_second < 0:
            return None
        node = HarvestNode(
            zone_id=zone_id, node_id=node_id,
            kind=kind, capacity=capacity,
            current_supply=(
                capacity if starting_supply is None
                else max(0, min(capacity, starting_supply))
            ),
            recovery_per_second=recovery_per_second,
        )
        self._nodes[key] = node
        return node

    def state(
        self, *, zone_id: str, node_id: str,
    ) -> t.Optional[HarvestNode]:
        return self._nodes.get((zone_id, node_id))

    def is_exhausted(
        self, *, zone_id: str, node_id: str,
    ) -> bool:
        node = self._nodes.get((zone_id, node_id))
        if node is None:
            return False
        return node.status == NodeStatus.EXHAUSTED

    def harvest(
        self, *, zone_id: str, node_id: str,
        amount: int,
    ) -> HarvestResult:
        node = self._nodes.get((zone_id, node_id))
        if node is None:
            return HarvestResult(False, reason="no such node")
        if node.status == NodeStatus.EXHAUSTED:
            return HarvestResult(
                False, reason="node permanently exhausted",
                new_status=NodeStatus.EXHAUSTED,
            )
        if amount <= 0:
            return HarvestResult(
                False, reason="amount must be positive",
            )
        # Yield is min of requested vs supply
        yielded = min(amount, node.current_supply)
        node.current_supply -= yielded

        # Status check
        ratio = (
            node.current_supply / node.capacity
            if node.capacity > 0 else 0.0
        )
        if (
            ratio <= PERMANENT_EXHAUSTION_RATIO
            and node.status == NodeStatus.DAMAGED
        ):
            # Repeated drain on damaged node = permanent kill
            node.status = NodeStatus.EXHAUSTED
        elif (
            ratio < self.critical_ratio
            and node.status == NodeStatus.HEALTHY
        ):
            node.status = NodeStatus.DAMAGED
            node.recovery_per_second *= (
                self.damaged_recovery_penalty
            )
            node.capacity = int(
                node.capacity * self.damaged_capacity_penalty,
            )
            node.current_supply = min(
                node.current_supply, node.capacity,
            )
        return HarvestResult(
            accepted=True, yielded=yielded,
            remaining=node.current_supply,
            new_status=node.status,
        )

    def tick(
        self, *, elapsed_seconds: float,
    ) -> int:
        """Run recovery on every node; returns count of nodes
        whose supply changed."""
        if elapsed_seconds <= 0:
            return 0
        affected = 0
        for node in self._nodes.values():
            if node.status == NodeStatus.EXHAUSTED:
                continue
            if node.current_supply >= node.capacity:
                continue
            recovered = int(
                node.recovery_per_second * elapsed_seconds,
            )
            if recovered <= 0:
                continue
            node.current_supply = min(
                node.capacity,
                node.current_supply + recovered,
            )
            node.last_tick_seconds += elapsed_seconds
            affected += 1
        return affected

    def total_nodes(self) -> int:
        return len(self._nodes)


__all__ = [
    "CRITICAL_RATIO", "PERMANENT_EXHAUSTION_RATIO",
    "DAMAGED_RECOVERY_PENALTY", "DAMAGED_CAPACITY_PENALTY",
    "NodeKind", "NodeStatus",
    "HarvestNode", "HarvestResult",
    "ResourceDepletionRegistry",
]
