"""Tests for player_restaurant."""
from __future__ import annotations

from server.player_restaurant import (
    PlayerRestaurantSystem, RestaurantState,
)


def _found(s: PlayerRestaurantSystem) -> str:
    return s.found_restaurant(
        owner_id="naji", name="The Mythril Spoon",
    )


def _ready(
    s: PlayerRestaurantSystem,
) -> tuple[str, str, str]:
    rid = _found(s)
    did = s.add_dish(
        restaurant_id=rid, name="Mythril Stew",
        price_gil=100, cooking_skill_required=30,
    )
    s.hire_waitstaff(
        restaurant_id=rid, staff_id="cara",
    )
    return rid, did, "cara"


def test_found_happy():
    s = PlayerRestaurantSystem()
    assert _found(s) is not None


def test_found_empty_owner_blocked():
    s = PlayerRestaurantSystem()
    assert s.found_restaurant(
        owner_id="", name="x",
    ) is None


def test_add_dish_happy():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    assert s.add_dish(
        restaurant_id=rid, name="Soup",
        price_gil=100, cooking_skill_required=10,
    ) is not None


def test_add_dish_zero_price_blocked():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    assert s.add_dish(
        restaurant_id=rid, name="Soup",
        price_gil=10, cooking_skill_required=10,
    ) is None


def test_add_dish_empty_name_blocked():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    assert s.add_dish(
        restaurant_id=rid, name="",
        price_gil=100, cooking_skill_required=10,
    ) is None


def test_add_dish_to_closed_blocked():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    s.close_restaurant(
        restaurant_id=rid, owner_id="naji",
    )
    assert s.add_dish(
        restaurant_id=rid, name="x",
        price_gil=100, cooking_skill_required=0,
    ) is None


def test_hire_waitstaff_happy():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    assert s.hire_waitstaff(
        restaurant_id=rid, staff_id="cara",
    ) is True


def test_hire_waitstaff_owner_blocked():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    assert s.hire_waitstaff(
        restaurant_id=rid, staff_id="naji",
    ) is False


def test_hire_waitstaff_dup_blocked():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    s.hire_waitstaff(
        restaurant_id=rid, staff_id="cara",
    )
    assert s.hire_waitstaff(
        restaurant_id=rid, staff_id="cara",
    ) is False


def test_fire_waitstaff_happy():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    s.hire_waitstaff(
        restaurant_id=rid, staff_id="cara",
    )
    assert s.fire_waitstaff(
        restaurant_id=rid, staff_id="cara",
    ) is True


def test_order_dish_happy():
    s = PlayerRestaurantSystem()
    rid, did, st = _ready(s)
    paid = s.order_dish(
        restaurant_id=rid, dish_id=did,
        customer_id="bob", staff_id=st,
        cook_skill=50,
    )
    assert paid == 100


def test_order_dish_owner_as_customer_blocked():
    s = PlayerRestaurantSystem()
    rid, did, st = _ready(s)
    assert s.order_dish(
        restaurant_id=rid, dish_id=did,
        customer_id="naji", staff_id=st,
        cook_skill=50,
    ) is None


def test_order_dish_skill_insufficient_blocked():
    s = PlayerRestaurantSystem()
    rid, did, st = _ready(s)
    assert s.order_dish(
        restaurant_id=rid, dish_id=did,
        customer_id="bob", staff_id=st,
        cook_skill=10,
    ) is None


def test_order_dish_unknown_dish_blocked():
    s = PlayerRestaurantSystem()
    rid, _, st = _ready(s)
    assert s.order_dish(
        restaurant_id=rid, dish_id="ghost",
        customer_id="bob", staff_id=st,
        cook_skill=50,
    ) is None


def test_order_dish_non_staff_blocked():
    s = PlayerRestaurantSystem()
    rid, did, _ = _ready(s)
    assert s.order_dish(
        restaurant_id=rid, dish_id=did,
        customer_id="bob", staff_id="stranger",
        cook_skill=50,
    ) is None


def test_order_dish_after_close_blocked():
    s = PlayerRestaurantSystem()
    rid, did, st = _ready(s)
    s.close_restaurant(
        restaurant_id=rid, owner_id="naji",
    )
    assert s.order_dish(
        restaurant_id=rid, dish_id=did,
        customer_id="bob", staff_id=st,
        cook_skill=50,
    ) is None


def test_owner_revenue_minus_wage():
    s = PlayerRestaurantSystem()
    rid, did, st = _ready(s)
    s.order_dish(
        restaurant_id=rid, dish_id=did,
        customer_id="bob", staff_id=st,
        cook_skill=50,
    )
    # Price 100 - wage 20 = 80
    assert s.restaurant(
        restaurant_id=rid,
    ).revenue_gil == 80


def test_staff_earnings_accumulate():
    s = PlayerRestaurantSystem()
    rid, did, st = _ready(s)
    for _ in range(3):
        s.order_dish(
            restaurant_id=rid, dish_id=did,
            customer_id="bob", staff_id=st,
            cook_skill=50,
        )
    assert s.staff_earnings(
        restaurant_id=rid, staff_id=st,
    ) == 60


def test_close_restaurant_happy():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    assert s.close_restaurant(
        restaurant_id=rid, owner_id="naji",
    ) is True
    assert s.restaurant(
        restaurant_id=rid,
    ).state == RestaurantState.CLOSED


def test_close_restaurant_not_owner_blocked():
    s = PlayerRestaurantSystem()
    rid = _found(s)
    assert s.close_restaurant(
        restaurant_id=rid, owner_id="bob",
    ) is False


def test_orders_filled_tracked():
    s = PlayerRestaurantSystem()
    rid, did, st = _ready(s)
    s.order_dish(
        restaurant_id=rid, dish_id=did,
        customer_id="bob", staff_id=st,
        cook_skill=50,
    )
    s.order_dish(
        restaurant_id=rid, dish_id=did,
        customer_id="cara", staff_id=st,
        cook_skill=50,
    )
    assert s.restaurant(
        restaurant_id=rid,
    ).orders_filled == 2


def test_enum_count():
    assert len(list(RestaurantState)) == 2
