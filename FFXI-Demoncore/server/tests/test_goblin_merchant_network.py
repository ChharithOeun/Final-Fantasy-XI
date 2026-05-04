"""Tests for the goblin merchant network."""
from __future__ import annotations

from server.goblin_merchant_network import (
    GoblinMerchantNetwork,
    GoblinNodeKind,
)


def _setup(net: GoblinMerchantNetwork):
    net.add_node(
        node_id="hub_jeuno_under",
        kind=GoblinNodeKind.HUB_BAZAAR,
        zone_id="jeuno",
    )
    net.add_node(
        node_id="outpost_kuftal",
        kind=GoblinNodeKind.OUTPOST,
        zone_id="kuftal_tunnel",
    )
    return net.add_route(
        from_node_id="hub_jeuno_under",
        to_node_id="outpost_kuftal",
        safety=8,
        distance_yalms=100,
    )


def test_add_node():
    net = GoblinMerchantNetwork()
    n = net.add_node(
        node_id="x",
        kind=GoblinNodeKind.OUTPOST,
        zone_id="z",
    )
    assert n is not None


def test_add_node_double_rejected():
    net = GoblinMerchantNetwork()
    net.add_node(
        node_id="x",
        kind=GoblinNodeKind.OUTPOST,
        zone_id="z",
    )
    second = net.add_node(
        node_id="x",
        kind=GoblinNodeKind.HUB_BAZAAR,
        zone_id="z",
    )
    assert second is None


def test_add_node_empty_zone_rejected():
    net = GoblinMerchantNetwork()
    res = net.add_node(
        node_id="x",
        kind=GoblinNodeKind.OUTPOST,
        zone_id="",
    )
    assert res is None


def test_add_route():
    net = GoblinMerchantNetwork()
    r = _setup(net)
    assert r is not None


def test_add_route_self_loop_rejected():
    net = GoblinMerchantNetwork()
    net.add_node(
        node_id="x",
        kind=GoblinNodeKind.OUTPOST,
        zone_id="z",
    )
    assert net.add_route(
        from_node_id="x", to_node_id="x",
        safety=5, distance_yalms=0,
    ) is None


def test_add_route_unknown_node():
    net = GoblinMerchantNetwork()
    net.add_node(
        node_id="x",
        kind=GoblinNodeKind.OUTPOST,
        zone_id="z",
    )
    assert net.add_route(
        from_node_id="x", to_node_id="ghost",
        safety=5, distance_yalms=0,
    ) is None


def test_add_route_invalid_safety():
    net = GoblinMerchantNetwork()
    net.add_node(
        node_id="a",
        kind=GoblinNodeKind.OUTPOST,
        zone_id="z",
    )
    net.add_node(
        node_id="b",
        kind=GoblinNodeKind.OUTPOST,
        zone_id="z",
    )
    assert net.add_route(
        from_node_id="a", to_node_id="b",
        safety=99, distance_yalms=0,
    ) is None


def test_stock_node():
    net = GoblinMerchantNetwork()
    _setup(net)
    assert net.stock(
        node_id="hub_jeuno_under",
        item_id="cermet_chunk",
        qty=10, base_price=100,
    )


def test_stock_invalid_qty_rejected():
    net = GoblinMerchantNetwork()
    _setup(net)
    assert not net.stock(
        node_id="hub_jeuno_under",
        item_id="x", qty=0, base_price=100,
    )


def test_stock_unknown_node_rejected():
    net = GoblinMerchantNetwork()
    assert not net.stock(
        node_id="ghost",
        item_id="x", qty=1, base_price=1,
    )


def test_neighbors_lookup():
    net = GoblinMerchantNetwork()
    _setup(net)
    n = net.neighbors(node_id="hub_jeuno_under")
    assert len(n) == 1
    assert n[0].node_id == "outpost_kuftal"


def test_broker_trip_basic():
    net = GoblinMerchantNetwork()
    route = _setup(net)
    net.stock(
        node_id="hub_jeuno_under",
        item_id="cermet_chunk",
        qty=10, base_price=100,
    )
    net.stock(
        node_id="outpost_kuftal",
        item_id="cermet_chunk",
        qty=10, base_price=200,
    )
    trip = net.broker_trip(
        player_id="alice",
        route_id=route.route_id,
        item_id="cermet_chunk", qty=2,
    )
    assert trip.accepted
    assert trip.gross_payout > 0


def test_broker_trip_unknown_route():
    net = GoblinMerchantNetwork()
    trip = net.broker_trip(
        player_id="alice",
        route_id="ghost",
        item_id="x", qty=1,
    )
    assert not trip.accepted


def test_broker_trip_qty_zero_rejected():
    net = GoblinMerchantNetwork()
    route = _setup(net)
    trip = net.broker_trip(
        player_id="alice",
        route_id=route.route_id,
        item_id="x", qty=0,
    )
    assert not trip.accepted


def test_broker_trip_no_source_stock():
    net = GoblinMerchantNetwork()
    route = _setup(net)
    trip = net.broker_trip(
        player_id="alice",
        route_id=route.route_id,
        item_id="cermet_chunk", qty=1,
    )
    assert not trip.accepted


def test_broker_trip_insufficient_source_stock():
    net = GoblinMerchantNetwork()
    route = _setup(net)
    net.stock(
        node_id="hub_jeuno_under",
        item_id="cermet_chunk",
        qty=2, base_price=100,
    )
    net.stock(
        node_id="outpost_kuftal",
        item_id="cermet_chunk",
        qty=10, base_price=200,
    )
    trip = net.broker_trip(
        player_id="alice",
        route_id=route.route_id,
        item_id="cermet_chunk", qty=10,
    )
    assert not trip.accepted


def test_broker_trip_low_safety_higher_haircut():
    net = GoblinMerchantNetwork()
    net.add_node(
        node_id="a",
        kind=GoblinNodeKind.UNDERMARKET,
        zone_id="z",
    )
    net.add_node(
        node_id="b",
        kind=GoblinNodeKind.HUB_BAZAAR,
        zone_id="z",
    )
    safe = net.add_route(
        from_node_id="a", to_node_id="b",
        safety=10, distance_yalms=10,
    )
    risky = net.add_route(
        from_node_id="a", to_node_id="b",
        safety=2, distance_yalms=10,
    )
    net.stock(
        node_id="a", item_id="x",
        qty=20, base_price=100,
    )
    net.stock(
        node_id="b", item_id="x",
        qty=20, base_price=200,
    )
    safe_trip = net.broker_trip(
        player_id="alice",
        route_id=safe.route_id,
        item_id="x", qty=2,
    )
    risky_trip = net.broker_trip(
        player_id="alice",
        route_id=risky.route_id,
        item_id="x", qty=2,
    )
    assert risky_trip.haircut_pct > safe_trip.haircut_pct


def test_broker_trip_negotiation_helps():
    net = GoblinMerchantNetwork()
    route = _setup(net)
    net.stock(
        node_id="hub_jeuno_under",
        item_id="x", qty=10, base_price=100,
    )
    net.stock(
        node_id="outpost_kuftal",
        item_id="x", qty=10, base_price=200,
    )
    no_neg = net.broker_trip(
        player_id="alice",
        route_id=route.route_id,
        item_id="x", qty=2,
        player_negotiation=0,
    )
    net.stock(
        node_id="hub_jeuno_under",
        item_id="x", qty=10, base_price=100,
    )
    high_neg = net.broker_trip(
        player_id="alice",
        route_id=route.route_id,
        item_id="x", qty=2,
        player_negotiation=50,
    )
    assert (
        high_neg.gross_payout >= no_neg.gross_payout
    )


def test_broker_trip_decrements_source_stock():
    net = GoblinMerchantNetwork()
    route = _setup(net)
    net.stock(
        node_id="hub_jeuno_under",
        item_id="x", qty=10, base_price=100,
    )
    net.stock(
        node_id="outpost_kuftal",
        item_id="x", qty=10, base_price=200,
    )
    net.broker_trip(
        player_id="alice",
        route_id=route.route_id,
        item_id="x", qty=3,
    )
    src = net.get_node("hub_jeuno_under")
    assert src.stock["x"][0] == 7


def test_total_counts():
    net = GoblinMerchantNetwork()
    _setup(net)
    assert net.total_nodes() == 2
    assert net.total_routes() == 1
