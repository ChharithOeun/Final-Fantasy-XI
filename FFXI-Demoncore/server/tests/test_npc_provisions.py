"""Tests for npc_provisions."""
from __future__ import annotations

from server.cookpot_recipes import BuffPayload, DishKind
from server.leftover_storage import (
    LeftoverState, LeftoverStorage, ProvisionKind,
)
from server.npc_provisions import NpcPantry


def _setup():
    p = NpcPantry(npc_id="kupiri")
    p.define_item(
        item_id="meat_pie", dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(str_bonus=3, duration_seconds=600),
        kind=ProvisionKind.FOOD,
        max_stock=10, gil_price=120,
    )
    p.define_item(
        item_id="herbal_tea", dish=DishKind.WARMING_TEA,
        payload=BuffPayload(cold_resist=10, duration_seconds=600),
        kind=ProvisionKind.DRINK,
        max_stock=5, gil_price=60,
    )
    return p


def test_define_happy():
    p = _setup()
    assert p.total_items_defined() == 2


def test_define_blank_id_blocked():
    p = NpcPantry()
    out = p.define_item(
        item_id="", dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(duration_seconds=600),
        kind=ProvisionKind.FOOD,
        max_stock=5, gil_price=10,
    )
    assert out is False


def test_define_zero_stock_blocked():
    p = NpcPantry()
    out = p.define_item(
        item_id="x", dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(duration_seconds=600),
        kind=ProvisionKind.FOOD,
        max_stock=0, gil_price=10,
    )
    assert out is False


def test_define_negative_price_blocked():
    p = NpcPantry()
    out = p.define_item(
        item_id="x", dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(duration_seconds=600),
        kind=ProvisionKind.FOOD,
        max_stock=5, gil_price=-1,
    )
    assert out is False


def test_define_duplicate_blocked():
    p = _setup()
    out = p.define_item(
        item_id="meat_pie", dish=DishKind.HUNTERS_STEW,
        payload=BuffPayload(duration_seconds=600),
        kind=ProvisionKind.FOOD,
        max_stock=5, gil_price=10,
    )
    assert out is False


def test_initial_stock_filled():
    p = _setup()
    assert p.available(item_id="meat_pie") == 10
    assert p.available(item_id="herbal_tea") == 5


def test_available_unknown_zero():
    p = _setup()
    assert p.available(item_id="ghost") == 0


def test_price_returns():
    p = _setup()
    assert p.price(item_id="meat_pie") == 120
    assert p.price(item_id="herbal_tea") == 60


def test_price_unknown_zero():
    p = _setup()
    assert p.price(item_id="ghost") == 0


def test_purchase_decrements_stock():
    p = _setup()
    s = LeftoverStorage()
    out = p.purchase(
        item_id="meat_pie", buyer_id="alice",
        leftover_storage=s, leftover_id="lo1", now=10,
    )
    assert out == "lo1"
    assert p.available(item_id="meat_pie") == 9


def test_purchase_creates_player_owned_leftover():
    p = _setup()
    s = LeftoverStorage()
    p.purchase(
        item_id="meat_pie", buyer_id="alice",
        leftover_storage=s, leftover_id="lo1", now=10,
    )
    # After purchase the leftover should age normally
    s.age_all(dt_seconds=604801)  # past 7-day food shelf
    assert s.state_of(leftover_id="lo1") == LeftoverState.SPOILED


def test_unsold_pantry_does_not_decay():
    """The anti-monopoly rule in action."""
    p = _setup()
    s = LeftoverStorage()
    # Store 3 items in the leftover_storage marked NPC_STOCKED
    # (simulating the pantry's view of unsold inventory)
    for i in range(3):
        s.stash(
            leftover_id=f"shelf_{i}", owner_id="kupiri",
            dish=DishKind.HUNTERS_STEW,
            payload=BuffPayload(duration_seconds=600),
            stashed_at=10, kind=ProvisionKind.FOOD,
            provenance=__import__(
                "server.leftover_storage", fromlist=["Provenance"],
            ).Provenance.NPC_STOCKED,
        )
    # Time passes — much more than 7 days
    s.age_all(dt_seconds=999_999_999)
    # All three are still fresh (NPC_STOCKED is frozen)
    for i in range(3):
        assert s.state_of(
            leftover_id=f"shelf_{i}",
        ) == LeftoverState.FRESH


def test_purchase_out_of_stock():
    p = _setup()
    s = LeftoverStorage()
    # buy all 5 herbal teas
    for i in range(5):
        p.purchase(
            item_id="herbal_tea", buyer_id="alice",
            leftover_storage=s, leftover_id=f"lo{i}", now=10,
        )
    # 6th attempt fails
    out = p.purchase(
        item_id="herbal_tea", buyer_id="alice",
        leftover_storage=s, leftover_id="lo_last", now=10,
    )
    assert out is None


def test_purchase_unknown_item():
    p = _setup()
    s = LeftoverStorage()
    out = p.purchase(
        item_id="ghost", buyer_id="alice",
        leftover_storage=s, leftover_id="lo1", now=10,
    )
    assert out is None


def test_purchase_blank_buyer():
    p = _setup()
    s = LeftoverStorage()
    out = p.purchase(
        item_id="meat_pie", buyer_id="",
        leftover_storage=s, leftover_id="lo1", now=10,
    )
    assert out is None


def test_purchase_blank_leftover_id():
    p = _setup()
    s = LeftoverStorage()
    out = p.purchase(
        item_id="meat_pie", buyer_id="alice",
        leftover_storage=s, leftover_id="", now=10,
    )
    assert out is None


def test_restock_refills():
    p = _setup()
    s = LeftoverStorage()
    # buy 3 meat pies
    for i in range(3):
        p.purchase(
            item_id="meat_pie", buyer_id="alice",
            leftover_storage=s, leftover_id=f"lo{i}", now=10,
        )
    out = p.restock_cycle()
    # 3 meat pies refilled (herbal_tea was untouched)
    assert out == 3
    assert p.available(item_id="meat_pie") == 10


def test_restock_no_op_when_full():
    p = _setup()
    out = p.restock_cycle()
    assert out == 0
