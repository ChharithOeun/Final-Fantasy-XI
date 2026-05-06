"""Wild forage — gather food and water from the land.

Off the road, away from inns, the survivor gathers. Berry
bushes, mushroom logs, fallen fruit, water-skins from
springs — these regrow over time and reward small finds.

A forage_node has:
    - kind (BERRY / MUSHROOM / FRUIT / SPRING / HERB)
    - zone_id, position
    - max_charges (how many gathers before depleted)
    - regen_seconds (time to fully regrow)

Gathering returns a NodeYield. Depleted nodes recharge
gradually with linear interp.

Public surface
--------------
    ForageKind enum
    ForageNode dataclass (mutable)
    NodeYield dataclass (frozen)
    WildForageRegistry
        .register_node(node_id, zone_id, position, kind,
                       max_charges, regen_seconds) -> bool
        .gather(node_id, gatherer_id, now_seconds)
            -> NodeYield
        .charges_at(node_id, now_seconds) -> int
        .nodes_in_zone(zone_id) -> tuple[ForageNode, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ForageKind(str, enum.Enum):
    BERRY = "berry"        # food, restores hunger
    MUSHROOM = "mushroom"
    FRUIT = "fruit"
    SPRING = "spring"      # water, restores thirst
    HERB = "herb"          # crafting reagent


@dataclasses.dataclass
class ForageNode:
    node_id: str
    zone_id: str
    position: tuple[float, float, float]
    kind: ForageKind
    max_charges: int
    regen_seconds: int
    charges: int
    last_depleted_at: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class NodeYield:
    success: bool
    kind: t.Optional[ForageKind]
    quantity: int
    reason: str = ""


@dataclasses.dataclass
class WildForageRegistry:
    _nodes: dict[str, ForageNode] = dataclasses.field(
        default_factory=dict,
    )

    def register_node(
        self, *, node_id: str, zone_id: str,
        position: tuple[float, float, float],
        kind: ForageKind, max_charges: int,
        regen_seconds: int,
    ) -> bool:
        if not node_id or not zone_id:
            return False
        if max_charges <= 0 or regen_seconds <= 0:
            return False
        if node_id in self._nodes:
            return False
        self._nodes[node_id] = ForageNode(
            node_id=node_id, zone_id=zone_id,
            position=position, kind=kind,
            max_charges=max_charges,
            regen_seconds=regen_seconds,
            charges=max_charges,
        )
        return True

    def gather(
        self, *, node_id: str, gatherer_id: str,
        now_seconds: int,
    ) -> NodeYield:
        n = self._nodes.get(node_id)
        if n is None:
            return NodeYield(
                success=False, kind=None,
                quantity=0, reason="unknown node",
            )
        if not gatherer_id:
            return NodeYield(
                success=False, kind=None,
                quantity=0, reason="invalid gatherer",
            )
        # update charges based on regen
        current = self.charges_at(node_id=node_id, now_seconds=now_seconds)
        n.charges = current
        if n.charges <= 0:
            return NodeYield(
                success=False, kind=n.kind,
                quantity=0, reason="depleted",
            )
        n.charges -= 1
        if n.charges == 0:
            n.last_depleted_at = now_seconds
        return NodeYield(
            success=True, kind=n.kind, quantity=1,
        )

    def charges_at(
        self, *, node_id: str, now_seconds: int,
    ) -> int:
        n = self._nodes.get(node_id)
        if n is None:
            return 0
        if n.charges >= n.max_charges:
            return n.max_charges
        if n.last_depleted_at is None:
            return n.charges
        elapsed = now_seconds - n.last_depleted_at
        if elapsed <= 0:
            return n.charges
        # linear regen: full bar in regen_seconds
        recovered = (elapsed * n.max_charges) // n.regen_seconds
        new_count = min(n.max_charges, n.charges + recovered)
        return new_count

    def nodes_in_zone(
        self, *, zone_id: str,
    ) -> tuple[ForageNode, ...]:
        return tuple(
            n for n in self._nodes.values()
            if n.zone_id == zone_id
        )

    def total_nodes(self) -> int:
        return len(self._nodes)


__all__ = [
    "ForageKind", "ForageNode", "NodeYield",
    "WildForageRegistry",
]
