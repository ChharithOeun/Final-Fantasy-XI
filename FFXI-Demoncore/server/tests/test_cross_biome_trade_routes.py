"""Tests for cross-biome trade routes."""
from __future__ import annotations

from server.cross_biome_trade_routes import (
    Carrier,
    CrossBiomeTradeRoutes,
    RouteLeg,
)


def _legs_chain():
    return [
        RouteLeg(
            from_node="bastok", to_node="harbor",
            carrier=Carrier.CARAVAN, biome="surface",
            capacity=100, duration_seconds=60,
        ),
        RouteLeg(
            from_node="harbor", to_node="norg",
            carrier=Carrier.SHIP, biome="surface_sea",
            capacity=80, duration_seconds=600,
        ),
        RouteLeg(
            from_node="norg", to_node="abyss",
            carrier=Carrier.SUBMARINE, biome="deep",
            capacity=40, duration_seconds=900,
        ),
    ]


def test_register_route_happy():
    r = CrossBiomeTradeRoutes()
    assert r.register_route(
        route_id="r1", name="Bastok to Abyss",
        legs=_legs_chain(),
    ) is True


def test_register_blank_id():
    r = CrossBiomeTradeRoutes()
    assert r.register_route(
        route_id="", name="X", legs=_legs_chain(),
    ) is False


def test_register_no_legs():
    r = CrossBiomeTradeRoutes()
    assert r.register_route(
        route_id="r1", name="X", legs=[],
    ) is False


def test_register_double_blocked():
    r = CrossBiomeTradeRoutes()
    r.register_route(route_id="r1", name="X", legs=_legs_chain())
    assert r.register_route(
        route_id="r1", name="Y", legs=_legs_chain(),
    ) is False


def test_register_legs_not_chained():
    r = CrossBiomeTradeRoutes()
    legs = [
        RouteLeg(
            from_node="a", to_node="b",
            carrier=Carrier.CARAVAN, biome="surface",
            capacity=10, duration_seconds=10,
        ),
        RouteLeg(
            from_node="c", to_node="d",  # doesn't chain from "b"
            carrier=Carrier.SHIP, biome="sea",
            capacity=10, duration_seconds=10,
        ),
    ]
    assert r.register_route(route_id="r1", name="X", legs=legs) is False


def test_register_invalid_leg_capacity():
    r = CrossBiomeTradeRoutes()
    legs = [
        RouteLeg(
            from_node="a", to_node="b",
            carrier=Carrier.CARAVAN, biome="surface",
            capacity=0, duration_seconds=10,
        ),
    ]
    assert r.register_route(route_id="r1", name="X", legs=legs) is False


def test_route_capacity_is_min():
    r = CrossBiomeTradeRoutes()
    r.register_route(route_id="r1", name="X", legs=_legs_chain())
    # legs are 100, 80, 40 -> min 40
    assert r.route_capacity(route_id="r1") == 40


def test_route_duration_is_sum():
    r = CrossBiomeTradeRoutes()
    r.register_route(route_id="r1", name="X", legs=_legs_chain())
    assert r.route_duration(route_id="r1") == 60 + 600 + 900


def test_is_healthy_default_true():
    r = CrossBiomeTradeRoutes()
    r.register_route(route_id="r1", name="X", legs=_legs_chain())
    assert r.is_healthy(route_id="r1") is True


def test_set_leg_healthy_propagates():
    r = CrossBiomeTradeRoutes()
    r.register_route(route_id="r1", name="X", legs=_legs_chain())
    assert r.set_leg_healthy(
        route_id="r1", leg_index=1, healthy=False,
    ) is True
    assert r.is_healthy(route_id="r1") is False


def test_set_leg_healthy_unknown():
    r = CrossBiomeTradeRoutes()
    assert r.set_leg_healthy(
        route_id="ghost", leg_index=0, healthy=False,
    ) is False


def test_set_leg_healthy_bad_index():
    r = CrossBiomeTradeRoutes()
    r.register_route(route_id="r1", name="X", legs=_legs_chain())
    assert r.set_leg_healthy(
        route_id="r1", leg_index=99, healthy=False,
    ) is False


def test_routes_using_carrier_filters():
    r = CrossBiomeTradeRoutes()
    r.register_route(route_id="r1", name="X", legs=_legs_chain())
    out = r.routes_using_carrier(carrier=Carrier.SUBMARINE)
    assert len(out) == 1
    assert out[0].route_id == "r1"
    out2 = r.routes_using_carrier(carrier=Carrier.AIRSHIP)
    assert len(out2) == 0


def test_unknown_route_helpers_return_zero():
    r = CrossBiomeTradeRoutes()
    assert r.route_capacity(route_id="ghost") == 0
    assert r.route_duration(route_id="ghost") == 0
    assert r.is_healthy(route_id="ghost") is False


def test_health_recovers_after_set_back():
    r = CrossBiomeTradeRoutes()
    r.register_route(route_id="r1", name="X", legs=_legs_chain())
    r.set_leg_healthy(route_id="r1", leg_index=1, healthy=False)
    assert r.is_healthy(route_id="r1") is False
    r.set_leg_healthy(route_id="r1", leg_index=1, healthy=True)
    assert r.is_healthy(route_id="r1") is True
