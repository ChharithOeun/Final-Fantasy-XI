"""Tests for wandering_caravans."""
from __future__ import annotations

from server.wandering_caravans import (
    Caravan, CaravanItem, CaravanStop, WanderingCaravans,
)


def _basic_caravan(cid="cara_1"):
    return Caravan(
        caravan_id=cid,
        name="Wabe-Fendi's Wandering Wares",
        route=(
            CaravanStop(zone_id="bastok", hours_stay=24),
            CaravanStop(zone_id="sandy", hours_stay=24),
            CaravanStop(zone_id="windy", hours_stay=24),
        ),
        stock=(
            CaravanItem(
                item_id="rare_incense",
                base_price_gil=500, max_supply=10,
                restock_per_visit=5,
            ),
            CaravanItem(
                item_id="forgotten_scroll",
                base_price_gil=15000, max_supply=2,
                restock_per_visit=1,
            ),
        ),
    )


def test_register_happy():
    w = WanderingCaravans()
    assert w.register_caravan(_basic_caravan()) is True


def test_register_blank_id_blocked():
    w = WanderingCaravans()
    bad = Caravan(
        caravan_id="", name="x",
        route=(CaravanStop(zone_id="z", hours_stay=24),),
        stock=(),
    )
    assert w.register_caravan(bad) is False


def test_register_empty_route_blocked():
    w = WanderingCaravans()
    bad = Caravan(
        caravan_id="x", name="x", route=(), stock=(),
    )
    assert w.register_caravan(bad) is False


def test_register_zero_hours_blocked():
    w = WanderingCaravans()
    bad = Caravan(
        caravan_id="x", name="x",
        route=(CaravanStop(zone_id="z", hours_stay=0),),
        stock=(),
    )
    assert w.register_caravan(bad) is False


def test_register_bad_stock_blocked():
    w = WanderingCaravans()
    bad = Caravan(
        caravan_id="x", name="x",
        route=(CaravanStop(zone_id="z", hours_stay=24),),
        stock=(CaravanItem(
            item_id="bad", base_price_gil=100,
            max_supply=0, restock_per_visit=1,
        ),),
    )
    assert w.register_caravan(bad) is False


def test_advance_settles_at_first():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    assert w.current_zone(caravan_id="cara_1") == "bastok"


def test_advance_moves_to_next_stop():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    w.advance(now_hour=25)  # 25h after start
    assert w.current_zone(caravan_id="cara_1") == "sandy"


def test_advance_loops():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    # 72 hours = 3 stops at 24h each = full loop -> bastok
    w.advance(now_hour=72)
    assert w.current_zone(caravan_id="cara_1") == "bastok"


def test_stock_at_current_zone():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    snap = w.stock_at(
        caravan_id="cara_1", zone_id="bastok",
    )
    items = {s.item_id: s for s in snap}
    assert items["rare_incense"].available == 5
    assert items["forgotten_scroll"].available == 1


def test_stock_at_wrong_zone_empty():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    snap = w.stock_at(
        caravan_id="cara_1", zone_id="sandy",
    )
    assert snap == []


def test_buy_decrements_supply():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    cost = w.buy(
        player_id="bob", caravan_id="cara_1",
        item_id="rare_incense", quantity=2,
    )
    assert cost == 1000
    snap = w.stock_at(
        caravan_id="cara_1", zone_id="bastok",
    )
    items = {s.item_id: s for s in snap}
    assert items["rare_incense"].available == 3


def test_buy_more_than_supply_blocked():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    cost = w.buy(
        player_id="bob", caravan_id="cara_1",
        item_id="rare_incense", quantity=10,
    )
    assert cost is None


def test_buy_unknown_item_blocked():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    cost = w.buy(
        player_id="bob", caravan_id="cara_1",
        item_id="ghost", quantity=1,
    )
    assert cost is None


def test_buy_zero_quantity_blocked():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    cost = w.buy(
        player_id="bob", caravan_id="cara_1",
        item_id="rare_incense", quantity=0,
    )
    assert cost is None


def test_buy_blank_player_blocked():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    cost = w.buy(
        player_id="", caravan_id="cara_1",
        item_id="rare_incense", quantity=1,
    )
    assert cost is None


def test_buy_unknown_caravan_blocked():
    w = WanderingCaravans()
    cost = w.buy(
        player_id="bob", caravan_id="ghost",
        item_id="x", quantity=1,
    )
    assert cost is None


def test_restock_on_new_visit():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    w.buy(
        player_id="bob", caravan_id="cara_1",
        item_id="rare_incense", quantity=5,
    )
    # Empty stock; advance to next stop and back
    w.advance(now_hour=72)  # full loop -> back to bastok
    snap = w.stock_at(
        caravan_id="cara_1", zone_id="bastok",
    )
    items = {s.item_id: s for s in snap}
    assert items["rare_incense"].available == 5


def test_current_zone_unknown_caravan():
    w = WanderingCaravans()
    assert w.current_zone(caravan_id="ghost") is None


def test_current_zone_before_advance():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    assert w.current_zone(caravan_id="cara_1") is None


def test_stock_snapshot_carries_price():
    w = WanderingCaravans()
    w.register_caravan(_basic_caravan())
    w.advance(now_hour=0)
    snap = w.stock_at(
        caravan_id="cara_1", zone_id="bastok",
    )
    scrolls = [
        s for s in snap if s.item_id == "forgotten_scroll"
    ]
    assert scrolls[0].price_gil == 15000
