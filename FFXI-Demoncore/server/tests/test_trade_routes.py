"""Tests for trade routes + caravans."""
from __future__ import annotations

import pytest

from server.trade_routes import (
    Caravan,
    CaravanStatus,
    Frequency,
    GoodsBundle,
    Settlement,
    TradeRoute,
    TradeRouteRegistry,
    seed_default_routes,
)


def _basic_route() -> TradeRoute:
    return TradeRoute(
        route_id="test_route",
        origin=Settlement.BASTOK,
        destination=Settlement.JEUNO,
        stops=("zone_a", "zone_b", "zone_c"),
        goods_catalog=(GoodsBundle("iron_ore", 50),),
        frequency=Frequency.HOURLY,
    )


def test_route_must_have_stops():
    reg = TradeRouteRegistry()
    bad = TradeRoute(
        route_id="empty",
        origin=Settlement.BASTOK,
        destination=Settlement.JEUNO,
        stops=(),
        goods_catalog=(),
    )
    with pytest.raises(ValueError):
        reg.register_route(bad)


def test_register_route_and_lookup():
    reg = TradeRouteRegistry()
    r = _basic_route()
    reg.register_route(r)
    assert reg.route_for("test_route") is r
    assert reg.total_routes() == 1


def test_dispatch_creates_caravan():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    res = reg.dispatch(route_id="test_route", now_seconds=0.0)
    assert res.accepted
    assert res.caravan.status == CaravanStatus.DEPARTING
    assert res.caravan.current_stop_index == 0


def test_dispatch_unknown_route_rejected():
    reg = TradeRouteRegistry()
    res = reg.dispatch(route_id="ghost", now_seconds=0.0)
    assert not res.accepted


def test_frequency_blocks_too_soon_dispatch():
    reg = TradeRouteRegistry()
    r = TradeRoute(
        route_id="hourly", origin=Settlement.BASTOK,
        destination=Settlement.JEUNO,
        stops=("a",), goods_catalog=(),
        frequency=Frequency.HOURLY,
    )
    reg.register_route(r)
    reg.dispatch(route_id="hourly", now_seconds=0.0)
    # 30 minutes later — too soon
    res = reg.dispatch(route_id="hourly", now_seconds=1800.0)
    assert not res.accepted


def test_frequency_allows_after_window():
    reg = TradeRouteRegistry()
    r = TradeRoute(
        route_id="hourly", origin=Settlement.BASTOK,
        destination=Settlement.JEUNO,
        stops=("a",), goods_catalog=(),
        frequency=Frequency.HOURLY,
    )
    reg.register_route(r)
    reg.dispatch(route_id="hourly", now_seconds=0.0)
    res = reg.dispatch(route_id="hourly", now_seconds=3600.0)
    assert res.accepted


def test_sporadic_no_frequency_gate():
    """SPORADIC routes can dispatch back-to-back."""
    reg = TradeRouteRegistry()
    r = TradeRoute(
        route_id="manual", origin=Settlement.BASTOK,
        destination=Settlement.JEUNO,
        stops=("a",), goods_catalog=(),
        frequency=Frequency.SPORADIC,
    )
    reg.register_route(r)
    a = reg.dispatch(route_id="manual", now_seconds=0.0)
    b = reg.dispatch(route_id="manual", now_seconds=10.0)
    assert a.accepted and b.accepted


def test_advance_through_stops():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    res = reg.dispatch(route_id="test_route", now_seconds=0.0)
    cid = res.caravan.caravan_id
    a1 = reg.advance(caravan_id=cid, now_seconds=10.0)
    assert a1.accepted
    assert a1.new_stop_index == 1
    a2 = reg.advance(caravan_id=cid, now_seconds=20.0)
    assert a2.new_stop_index == 2
    a3 = reg.advance(caravan_id=cid, now_seconds=30.0)
    # Past the last stop -> ARRIVED
    assert a3.new_status == CaravanStatus.ARRIVED


def test_advance_after_arrival_rejected():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    res = reg.dispatch(route_id="test_route", now_seconds=0.0)
    cid = res.caravan.caravan_id
    for i in range(3):
        reg.advance(caravan_id=cid, now_seconds=10.0 + i)
    again = reg.advance(caravan_id=cid, now_seconds=100.0)
    assert not again.accepted


def test_raid_marks_caravan_raided():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    res = reg.dispatch(route_id="test_route", now_seconds=0.0)
    cid = res.caravan.caravan_id
    raid_res = reg.raid(caravan_id=cid, now_seconds=10.0)
    assert raid_res.accepted
    assert raid_res.new_status == CaravanStatus.RAIDED


def test_raid_bumps_route_pressure():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    initial = reg.raid_pressure("test_route")
    res = reg.dispatch(route_id="test_route", now_seconds=0.0)
    reg.raid(
        caravan_id=res.caravan.caravan_id,
        now_seconds=10.0, risk_bump=20,
    )
    assert reg.raid_pressure("test_route") == initial + 20


def test_raid_pressure_caps_at_100():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    for i in range(20):
        res = reg.dispatch(
            route_id="test_route",
            now_seconds=float(i * 3600 * 2),
        )
        reg.raid(
            caravan_id=res.caravan.caravan_id,
            now_seconds=float(i * 3600 * 2 + 10),
            risk_bump=20,
        )
    assert reg.raid_pressure("test_route") == 100


def test_relieve_pressure_drops_risk():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    res = reg.dispatch(route_id="test_route", now_seconds=0.0)
    reg.raid(
        caravan_id=res.caravan.caravan_id,
        now_seconds=10.0, risk_bump=30,
    )
    after_raid = reg.raid_pressure("test_route")
    new = reg.relieve_pressure(route_id="test_route", amount=15)
    assert new == after_raid - 15


def test_relieve_pressure_floors_at_zero():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    new = reg.relieve_pressure(
        route_id="test_route", amount=999,
    )
    assert new == 0


def test_active_caravans_excludes_done():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    a = reg.dispatch(route_id="test_route", now_seconds=0.0)
    b = reg.dispatch(route_id="test_route", now_seconds=10000.0)
    # Raid b
    reg.raid(caravan_id=b.caravan.caravan_id, now_seconds=10001.0)
    # Arrive a
    for _ in range(3):
        reg.advance(
            caravan_id=a.caravan.caravan_id, now_seconds=10.0,
        )
    active = reg.active_caravans()
    assert len(active) == 0


def test_caravans_on_route_filter():
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    other = TradeRoute(
        route_id="other", origin=Settlement.SAN_DORIA,
        destination=Settlement.JEUNO,
        stops=("zone_x",), goods_catalog=(),
        frequency=Frequency.SPORADIC,
    )
    reg.register_route(other)
    reg.dispatch(route_id="test_route", now_seconds=0.0)
    reg.dispatch(route_id="other", now_seconds=0.0)
    assert len(reg.caravans_on_route("test_route")) == 1
    assert len(reg.caravans_on_route("other")) == 1


def test_seed_default_routes_populates_canonical():
    reg = seed_default_routes(TradeRouteRegistry())
    # Spot-check: classic Bastok-Jeuno overland
    r = reg.route_for("bastok_jeuno_caravan")
    assert r is not None
    assert r.origin == Settlement.BASTOK
    assert r.destination == Settlement.JEUNO
    # Selbina-Mhaura ferry is hourly
    ferry = reg.route_for("selbina_mhaura_ferry")
    assert ferry.frequency == Frequency.HOURLY
    # Norg corsair run is high-risk
    norg = reg.route_for("jeuno_norg_corsair_run")
    assert norg.base_risk >= 30


def test_full_lifecycle_player_escort_lowers_risk():
    """Caravan dispatches with player escort, completes the run,
    and the route's raid pressure stays low. A subsequent raid
    bumps it back up."""
    reg = TradeRouteRegistry()
    reg.register_route(_basic_route())
    initial = reg.raid_pressure("test_route")
    a = reg.dispatch(
        route_id="test_route", now_seconds=0.0,
        escort_player_ids=("alice", "bob"),
    )
    cid = a.caravan.caravan_id
    # Successful run — advance through all stops
    for _ in range(3):
        reg.advance(caravan_id=cid, now_seconds=10.0)
    # Player relief bonus for guarded caravan
    reg.relieve_pressure(route_id="test_route", amount=5)
    after_escort = reg.raid_pressure("test_route")
    assert after_escort <= initial   # at most equal (already at 0 or lower)
    # Next caravan unescorted gets raided
    b = reg.dispatch(
        route_id="test_route",
        now_seconds=2 * 3600 + 1,  # past hourly gate
    )
    reg.raid(
        caravan_id=b.caravan.caravan_id,
        now_seconds=2 * 3600 + 100, risk_bump=25,
    )
    after_raid = reg.raid_pressure("test_route")
    assert after_raid > after_escort
