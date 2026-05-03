"""Tests for the black market network."""
from __future__ import annotations

from server.black_market_network import (
    BlackMarketNetwork,
    Contraband,
    HEAT_CRACKDOWN_THRESHOLD,
    NodeKind,
    NodeStatus,
)


def test_add_node_succeeds():
    net = BlackMarketNetwork()
    n = net.add_node(
        node_id="fence_jeuno",
        kind=NodeKind.FENCE,
        zone_id="jeuno",
    )
    assert n is not None
    assert n.status == NodeStatus.OPERATIONAL


def test_double_add_rejected():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="x", kind=NodeKind.FENCE, zone_id="z",
    )
    second = net.add_node(
        node_id="x", kind=NodeKind.FENCE, zone_id="z",
    )
    assert second is None


def test_add_route_succeeds():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z1",
    )
    net.add_node(
        node_id="b", kind=NodeKind.SMUGGLER_DEN, zone_id="z2",
    )
    route = net.add_route(
        from_node_id="a", to_node_id="b",
        risk=40, base_payout_gil=1000,
    )
    assert route is not None
    assert route.risk == 40


def test_add_route_unknown_node():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    assert net.add_route(
        from_node_id="a", to_node_id="ghost",
        risk=10, base_payout_gil=100,
    ) is None


def test_add_route_self_loop_rejected():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    assert net.add_route(
        from_node_id="a", to_node_id="a",
        risk=10, base_payout_gil=100,
    ) is None


def test_add_route_invalid_risk():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    assert net.add_route(
        from_node_id="a", to_node_id="b",
        risk=200, base_payout_gil=100,
    ) is None


def test_add_route_negative_payout():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    assert net.add_route(
        from_node_id="a", to_node_id="b",
        risk=10, base_payout_gil=-1,
    ) is None


def test_seize_node():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    assert net.seize_node(node_id="a")
    assert net.node("a").status == NodeStatus.SEIZED


def test_seize_unknown_returns_false():
    net = BlackMarketNetwork()
    assert not net.seize_node(node_id="ghost")


def test_seize_already_seized_returns_false():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.seize_node(node_id="a")
    assert not net.seize_node(node_id="a")


def test_active_routes_skip_seized():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_route(
        from_node_id="a", to_node_id="b",
        risk=10, base_payout_gil=100,
    )
    net.seize_node(node_id="b")
    assert net.active_routes_from("a") == ()


def test_contract_run_success():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    route = net.add_route(
        from_node_id="a", to_node_id="b",
        risk=20, base_payout_gil=1000,
    )
    res = net.contract_run(
        player_id="alice", route_id=route.route_id,
        contraband=(
            Contraband(
                item_id="hot_sword",
                declared_value_gil=500,
            ),
        ),
    )
    assert res.accepted
    # base 1000 + (1000 + 500) * 20 * 0.05 = 1000 + 1500 = 2500
    assert res.payout_gil == 2500
    assert res.bounty_exposure == 20


def test_contract_run_unknown_route():
    net = BlackMarketNetwork()
    res = net.contract_run(
        player_id="x", route_id="ghost",
        contraband=(
            Contraband(item_id="x", declared_value_gil=10),
        ),
    )
    assert not res.accepted


def test_contract_run_no_cargo():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    route = net.add_route(
        from_node_id="a", to_node_id="b",
        risk=10, base_payout_gil=100,
    )
    res = net.contract_run(
        player_id="x", route_id=route.route_id,
        contraband=(),
    )
    assert not res.accepted


def test_contract_run_seized_origin():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    route = net.add_route(
        from_node_id="a", to_node_id="b",
        risk=10, base_payout_gil=100,
    )
    net.seize_node(node_id="a")
    res = net.contract_run(
        player_id="x", route_id=route.route_id,
        contraband=(
            Contraband(
                item_id="x", declared_value_gil=10,
            ),
        ),
    )
    assert not res.accepted


def test_runs_accumulate_heat_to_threshold():
    net = BlackMarketNetwork(heat_per_run=20)
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    route = net.add_route(
        from_node_id="a", to_node_id="b",
        risk=10, base_payout_gil=100,
    )
    # 5 runs * 20 heat = 100 -> HEAT status
    for _ in range(5):
        net.contract_run(
            player_id="x", route_id=route.route_id,
            contraband=(
                Contraband(
                    item_id="x", declared_value_gil=10,
                ),
            ),
        )
    assert net.node("a").status == NodeStatus.HEAT


def test_crackdown_check_seizes_extreme_heat():
    net = BlackMarketNetwork(heat_per_run=20)
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    route = net.add_route(
        from_node_id="a", to_node_id="b",
        risk=10, base_payout_gil=100,
    )
    # 11 runs * 20 = 220 heat (> 2x threshold of 100 = 200)
    for _ in range(11):
        net.contract_run(
            player_id="x", route_id=route.route_id,
            contraband=(
                Contraband(
                    item_id="x", declared_value_gil=10,
                ),
            ),
        )
    seized = net.crackdown_check()
    assert len(seized) >= 1


def test_run_increments_runs_completed():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    route = net.add_route(
        from_node_id="a", to_node_id="b",
        risk=10, base_payout_gil=100,
    )
    net.contract_run(
        player_id="x", route_id=route.route_id,
        contraband=(
            Contraband(item_id="x", declared_value_gil=10),
        ),
    )
    assert route.runs_completed == 1


def test_total_counts():
    net = BlackMarketNetwork()
    net.add_node(
        node_id="a", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_node(
        node_id="b", kind=NodeKind.FENCE, zone_id="z",
    )
    net.add_route(
        from_node_id="a", to_node_id="b",
        risk=10, base_payout_gil=100,
    )
    assert net.total_nodes() == 2
    assert net.total_routes() == 1
