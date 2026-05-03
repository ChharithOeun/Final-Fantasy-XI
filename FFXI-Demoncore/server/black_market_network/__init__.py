"""Black market network — underground economy graph.

The visible economy (auction_house, npc_economy) has a SHADOW —
fences who buy stolen gear, smugglers who run contraband across
nation borders, brokers who launder gil. This module models the
graph of those shadow nodes and the contraband moving along it.

Routes have RISK ratings; when crackdowns happen (governance
event), nodes shut down and the contraband supply backs up.
Players can take CONTRACTS to move contraband, getting paid more
than honest courier work — at the cost of bounty/honor exposure
through outlaw_system and honor_reputation.

Public surface
--------------
    NodeKind enum
    BlackMarketNode dataclass
    SmugglerRoute dataclass
    Contraband dataclass
    BlackMarketNetwork
        .add_node(node_id, kind, zone, owner_npc)
        .add_route(from_node, to_node, risk, base_payout)
        .seize_node(node_id) — crackdown shuts it down
        .contract_run(player_id, route_id, items) -> RunResult
        .active_routes_from(node_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default risk multipliers.
DEFAULT_HEAT_PER_RUN = 5      # heat accumulates per successful run
HEAT_CRACKDOWN_THRESHOLD = 100
RISK_PAYOUT_MULTIPLIER = 0.05  # +5% payout per risk point


class NodeKind(str, enum.Enum):
    FENCE = "fence"             # buys hot items
    SMUGGLER_DEN = "smuggler_den"
    LAUNDRY = "laundry"         # cleans dirty gil
    ARMS_DEALER = "arms_dealer"
    SLAVER = "slaver"           # for outlaw beastman captives
    DRUG_KITCHEN = "drug_kitchen"


class NodeStatus(str, enum.Enum):
    OPERATIONAL = "operational"
    HEAT = "heat"               # under suspicion, half capacity
    SEIZED = "seized"           # closed by crackdown


@dataclasses.dataclass
class BlackMarketNode:
    node_id: str
    kind: NodeKind
    zone_id: str
    owner_npc_id: t.Optional[str] = None
    status: NodeStatus = NodeStatus.OPERATIONAL
    heat: int = 0
    last_run_at_seconds: float = 0.0


@dataclasses.dataclass
class SmugglerRoute:
    route_id: str
    from_node_id: str
    to_node_id: str
    risk: int                   # 0..100 — bounty exposure
    base_payout_gil: int
    runs_completed: int = 0


@dataclasses.dataclass(frozen=True)
class Contraband:
    item_id: str
    declared_value_gil: int
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class RunResult:
    accepted: bool
    payout_gil: int = 0
    bounty_exposure: int = 0
    heat_added: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BlackMarketNetwork:
    crackdown_threshold: int = HEAT_CRACKDOWN_THRESHOLD
    heat_per_run: int = DEFAULT_HEAT_PER_RUN
    _nodes: dict[str, BlackMarketNode] = dataclasses.field(
        default_factory=dict,
    )
    _routes: dict[str, SmugglerRoute] = dataclasses.field(
        default_factory=dict,
    )
    _next_route_id: int = 0

    def add_node(
        self, *, node_id: str, kind: NodeKind,
        zone_id: str,
        owner_npc_id: t.Optional[str] = None,
    ) -> t.Optional[BlackMarketNode]:
        if node_id in self._nodes:
            return None
        node = BlackMarketNode(
            node_id=node_id, kind=kind, zone_id=zone_id,
            owner_npc_id=owner_npc_id,
        )
        self._nodes[node_id] = node
        return node

    def node(
        self, node_id: str,
    ) -> t.Optional[BlackMarketNode]:
        return self._nodes.get(node_id)

    def add_route(
        self, *, from_node_id: str, to_node_id: str,
        risk: int, base_payout_gil: int,
    ) -> t.Optional[SmugglerRoute]:
        if (
            from_node_id not in self._nodes
            or to_node_id not in self._nodes
        ):
            return None
        if from_node_id == to_node_id:
            return None
        if not (0 <= risk <= 100):
            return None
        if base_payout_gil < 0:
            return None
        rid = f"route_{self._next_route_id}"
        self._next_route_id += 1
        route = SmugglerRoute(
            route_id=rid,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            risk=risk, base_payout_gil=base_payout_gil,
        )
        self._routes[rid] = route
        return route

    def seize_node(self, *, node_id: str) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        if node.status == NodeStatus.SEIZED:
            return False
        node.status = NodeStatus.SEIZED
        return True

    def active_routes_from(
        self, node_id: str,
    ) -> tuple[SmugglerRoute, ...]:
        out: list[SmugglerRoute] = []
        for r in self._routes.values():
            if r.from_node_id != node_id:
                continue
            from_node = self._nodes[r.from_node_id]
            to_node = self._nodes[r.to_node_id]
            if (
                from_node.status == NodeStatus.SEIZED
                or to_node.status == NodeStatus.SEIZED
            ):
                continue
            out.append(r)
        return tuple(out)

    def contract_run(
        self, *, player_id: str, route_id: str,
        contraband: tuple[Contraband, ...],
        now_seconds: float = 0.0,
    ) -> RunResult:
        route = self._routes.get(route_id)
        if route is None:
            return RunResult(False, reason="no such route")
        if not contraband:
            return RunResult(
                False, reason="no contraband supplied",
            )
        from_node = self._nodes[route.from_node_id]
        to_node = self._nodes[route.to_node_id]
        if from_node.status == NodeStatus.SEIZED:
            return RunResult(False, reason="origin seized")
        if to_node.status == NodeStatus.SEIZED:
            return RunResult(
                False, reason="destination seized",
            )
        # Compute payout: base + value-based + risk multiplier
        cargo_value = sum(
            c.declared_value_gil for c in contraband
        )
        risk_bonus = int(
            (route.base_payout_gil + cargo_value)
            * route.risk * RISK_PAYOUT_MULTIPLIER,
        )
        payout = route.base_payout_gil + risk_bonus
        # Heat accumulates on origin and destination
        heat_added = self.heat_per_run
        for n in (from_node, to_node):
            n.heat += heat_added
            n.last_run_at_seconds = now_seconds
            if n.heat >= self.crackdown_threshold:
                n.status = NodeStatus.HEAT
        route.runs_completed += 1
        return RunResult(
            accepted=True, payout_gil=payout,
            bounty_exposure=route.risk,
            heat_added=heat_added,
        )

    def crackdown_check(
        self,
    ) -> tuple[BlackMarketNode, ...]:
        seized: list[BlackMarketNode] = []
        for node in self._nodes.values():
            if node.status != NodeStatus.HEAT:
                continue
            if node.heat >= self.crackdown_threshold * 2:
                node.status = NodeStatus.SEIZED
                seized.append(node)
        return tuple(seized)

    def total_nodes(self) -> int:
        return len(self._nodes)

    def total_routes(self) -> int:
        return len(self._routes)


__all__ = [
    "DEFAULT_HEAT_PER_RUN",
    "HEAT_CRACKDOWN_THRESHOLD",
    "RISK_PAYOUT_MULTIPLIER",
    "NodeKind", "NodeStatus",
    "BlackMarketNode", "SmugglerRoute",
    "Contraband", "RunResult",
    "BlackMarketNetwork",
]
