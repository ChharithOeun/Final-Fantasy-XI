"""Goblin merchant network — neutral trader graph.

Goblins are neutral merchants (per beastman_pantheon). This
module models the GRAPH of goblin traders and the goods that
flow between them. Each goblin trader sits at a NODE; routes
between nodes are directed edges with a per-edge SAFETY rating
that governs how much price markup a smuggling player can
extract by ferrying goods across the edge.

A player can BROKER a transaction at a node — buy from one
goblin, sell to another — and the network calculates the gross
profit accounting for SAFETY haircut and DISTANCE penalty.

Public surface
--------------
    GoblinNodeKind enum
    Route dataclass
    GoblinNode dataclass
    BrokerTrip dataclass
    GoblinMerchantNetwork
        .add_node(node_id, kind, zone)
        .add_route(from_id, to_id, safety, distance_yalms)
        .stock(node_id, item_id, qty, base_price)
        .broker_trip(player_id, route_id, item_id, qty,
                     player_negotiation) -> BrokerTrip
        .neighbors(node_id) -> tuple[GoblinNode]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default markup multipliers (expressed as PERCENT-per-point).
# safety 0..10 — lower safety carves a bigger haircut out of
# profit. At safety=10 no cut; at safety=0, 50% cut.
SAFETY_PENALTY_PER_POINT = 5.0      # percent per (10-safety)
DISTANCE_PENALTY_PER_YALM = 0.05    # percent per yalm
NEGOTIATION_BONUS_PER_POINT = 1.0   # percent per skill point


class GoblinNodeKind(str, enum.Enum):
    HUB_BAZAAR = "hub_bazaar"        # major trading post
    OUTPOST = "outpost"              # remote stall
    CARAVANSERAI = "caravanserai"    # waystation
    DOCK = "dock"                    # port-side
    UNDERMARKET = "undermarket"      # black-market dealer


@dataclasses.dataclass
class GoblinNode:
    node_id: str
    kind: GoblinNodeKind
    zone_id: str
    stock: dict[str, tuple[int, int]] = dataclasses.field(
        default_factory=dict,
    )   # item_id -> (qty, base_price)


@dataclasses.dataclass(frozen=True)
class Route:
    route_id: str
    from_node_id: str
    to_node_id: str
    safety: int                       # 0..10
    distance_yalms: int


@dataclasses.dataclass(frozen=True)
class BrokerTrip:
    accepted: bool
    route_id: str
    item_id: str
    qty: int
    gross_payout: int = 0
    haircut_pct: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class GoblinMerchantNetwork:
    safety_penalty_per_point: float = SAFETY_PENALTY_PER_POINT
    distance_penalty_per_yalm: float = (
        DISTANCE_PENALTY_PER_YALM
    )
    negotiation_bonus_per_point: float = (
        NEGOTIATION_BONUS_PER_POINT
    )
    _nodes: dict[str, GoblinNode] = dataclasses.field(
        default_factory=dict,
    )
    _routes: dict[str, Route] = dataclasses.field(
        default_factory=dict,
    )
    _next_route: int = 0

    def add_node(
        self, *, node_id: str,
        kind: GoblinNodeKind,
        zone_id: str,
    ) -> t.Optional[GoblinNode]:
        if node_id in self._nodes:
            return None
        if not zone_id:
            return None
        n = GoblinNode(
            node_id=node_id, kind=kind, zone_id=zone_id,
        )
        self._nodes[node_id] = n
        return n

    def add_route(
        self, *, from_node_id: str,
        to_node_id: str,
        safety: int,
        distance_yalms: int,
    ) -> t.Optional[Route]:
        if from_node_id == to_node_id:
            return None
        if (
            from_node_id not in self._nodes
            or to_node_id not in self._nodes
        ):
            return None
        if not (0 <= safety <= 10):
            return None
        if distance_yalms < 0:
            return None
        rid = f"goblin_route_{self._next_route}"
        self._next_route += 1
        r = Route(
            route_id=rid,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            safety=safety,
            distance_yalms=distance_yalms,
        )
        self._routes[rid] = r
        return r

    def stock(
        self, *, node_id: str, item_id: str,
        qty: int, base_price: int,
    ) -> bool:
        n = self._nodes.get(node_id)
        if n is None or qty <= 0 or base_price <= 0:
            return False
        n.stock[item_id] = (qty, base_price)
        return True

    def neighbors(
        self, *, node_id: str,
    ) -> tuple[GoblinNode, ...]:
        out: list[GoblinNode] = []
        for r in self._routes.values():
            if r.from_node_id != node_id:
                continue
            n = self._nodes.get(r.to_node_id)
            if n is not None:
                out.append(n)
        out.sort(key=lambda x: x.node_id)
        return tuple(out)

    def get_node(
        self, node_id: str,
    ) -> t.Optional[GoblinNode]:
        return self._nodes.get(node_id)

    def get_route(
        self, route_id: str,
    ) -> t.Optional[Route]:
        return self._routes.get(route_id)

    def broker_trip(
        self, *, player_id: str,
        route_id: str,
        item_id: str,
        qty: int,
        player_negotiation: int = 0,
    ) -> BrokerTrip:
        r = self._routes.get(route_id)
        if r is None:
            return BrokerTrip(
                False, route_id=route_id,
                item_id=item_id, qty=qty,
                reason="no such route",
            )
        if qty <= 0:
            return BrokerTrip(
                False, route_id=route_id,
                item_id=item_id, qty=qty,
                reason="qty must be positive",
            )
        src = self._nodes[r.from_node_id]
        dst = self._nodes[r.to_node_id]
        src_stock = src.stock.get(item_id)
        dst_stock = dst.stock.get(item_id)
        if src_stock is None:
            return BrokerTrip(
                False, route_id=route_id,
                item_id=item_id, qty=qty,
                reason="source has no stock",
            )
        src_qty, src_price = src_stock
        if src_qty < qty:
            return BrokerTrip(
                False, route_id=route_id,
                item_id=item_id, qty=qty,
                reason="insufficient source stock",
            )
        if dst_stock is None:
            # Destination doesn't trade this item — base on src
            dst_price = src_price
        else:
            _, dst_price = dst_stock
        # Gross spread before deductions
        gross_per_unit = max(0, dst_price - src_price)
        gross = gross_per_unit * qty
        # Safety haircut: lower safety -> higher haircut.
        # All values stored directly as PERCENT.
        haircut_pct = int(
            (10 - r.safety)
            * self.safety_penalty_per_point
        )
        # Distance penalty (additive percent)
        haircut_pct += int(
            r.distance_yalms
            * self.distance_penalty_per_yalm
        )
        # Negotiation refund (subtracted from haircut)
        bonus_pct = int(
            player_negotiation
            * self.negotiation_bonus_per_point
        )
        net_haircut_pct = max(0, haircut_pct - bonus_pct)
        net_haircut_pct = min(100, net_haircut_pct)
        payout = gross * (100 - net_haircut_pct) // 100
        # Decrement source stock
        src.stock[item_id] = (
            src_qty - qty, src_price,
        )
        return BrokerTrip(
            accepted=True, route_id=route_id,
            item_id=item_id, qty=qty,
            gross_payout=payout,
            haircut_pct=net_haircut_pct,
        )

    def total_nodes(self) -> int:
        return len(self._nodes)

    def total_routes(self) -> int:
        return len(self._routes)


__all__ = [
    "SAFETY_PENALTY_PER_POINT",
    "DISTANCE_PENALTY_PER_YALM",
    "NEGOTIATION_BONUS_PER_POINT",
    "GoblinNodeKind",
    "GoblinNode", "Route", "BrokerTrip",
    "GoblinMerchantNetwork",
]
