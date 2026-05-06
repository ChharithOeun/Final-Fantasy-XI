"""Tests for spice_rack."""
from __future__ import annotations

from server.cookpot_recipes import BuffPayload
from server.spice_rack import SpiceKind, SpiceRack


def test_add_one_spice():
    r = SpiceRack()
    ok = r.add_to_dish(
        dish_token="d1", spice=SpiceKind.CHILI, count=1,
    )
    assert ok is True
    assert r.spices_on(dish_token="d1") == {SpiceKind.CHILI: 1}


def test_add_blank_token_blocked():
    r = SpiceRack()
    out = r.add_to_dish(
        dish_token="", spice=SpiceKind.CHILI, count=1,
    )
    assert out is False


def test_add_zero_count_blocked():
    r = SpiceRack()
    out = r.add_to_dish(
        dish_token="d1", spice=SpiceKind.CHILI, count=0,
    )
    assert out is False


def test_three_spice_slot_max():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.CHILI, count=2)
    r.add_to_dish(dish_token="d1", spice=SpiceKind.SALT, count=1)
    # already at 3 total slots; adding more refused
    out = r.add_to_dish(
        dish_token="d1", spice=SpiceKind.GARLIC, count=1,
    )
    assert out is False


def test_clear_removes_spices():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.CHILI, count=2)
    out = r.clear(dish_token="d1")
    assert out == 2
    assert r.spices_on(dish_token="d1") == {}


def test_clear_unknown():
    r = SpiceRack()
    assert r.clear(dish_token="ghost") == 0


def test_apply_no_spices_returns_input():
    r = SpiceRack()
    p = BuffPayload(str_bonus=5, duration_seconds=600)
    out = r.apply(payload=p, dish_token="d1")
    assert out.str_bonus == 5
    assert out.duration_seconds == 600


def test_chili_adds_heat_resist():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.CHILI, count=1)
    p = BuffPayload(str_bonus=5, duration_seconds=600)
    out = r.apply(payload=p, dish_token="d1")
    assert out.heat_resist == 10
    # chili shortens duration: 600 - 300 = 300
    assert out.duration_seconds == 300


def test_salt_extends_duration():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.SALT, count=1)
    p = BuffPayload(str_bonus=5, duration_seconds=600)
    out = r.apply(payload=p, dish_token="d1")
    # 125% of 600 = 750
    assert out.duration_seconds == 750


def test_diminishing_returns_on_stack():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.CHILI, count=2)
    p = BuffPayload(duration_seconds=2000)
    out = r.apply(payload=p, dish_token="d1")
    # 2 chili → factor 1.5x of single effect = +15 heat,
    # not +20
    assert out.heat_resist == 15


def test_diminishing_returns_third():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.CHILI, count=3)
    p = BuffPayload(duration_seconds=2000)
    out = r.apply(payload=p, dish_token="d1")
    # 3 chili → 1.8x factor = +18 heat
    assert out.heat_resist == 18


def test_salt_and_chili_together():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.CHILI, count=1)
    r.add_to_dish(dish_token="d1", spice=SpiceKind.SALT, count=1)
    p = BuffPayload(duration_seconds=600)
    out = r.apply(payload=p, dish_token="d1")
    # chili -300, then salt 125% → (600-300)*1.25 = 375
    assert out.duration_seconds == 375
    assert out.heat_resist == 10


def test_ginger_adds_cold_and_str():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.GINGER, count=1)
    p = BuffPayload(str_bonus=5, duration_seconds=600)
    out = r.apply(payload=p, dish_token="d1")
    assert out.cold_resist == 10
    assert out.str_bonus == 6


def test_saffron_adds_all():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.SAFFRON, count=1)
    p = BuffPayload(duration_seconds=600)
    out = r.apply(payload=p, dish_token="d1")
    assert out.str_bonus == 1
    assert out.dex_bonus == 1
    assert out.vit_bonus == 1
    assert out.cold_resist == 3
    assert out.heat_resist == 3


def test_duration_floors_at_one():
    r = SpiceRack()
    r.add_to_dish(dish_token="d1", spice=SpiceKind.CHILI, count=3)
    # 3x chili at 1.8x → -540 duration
    p = BuffPayload(duration_seconds=100)
    out = r.apply(payload=p, dish_token="d1")
    assert out.duration_seconds >= 1


def test_eight_spice_kinds():
    assert len(list(SpiceKind)) == 8


def test_spices_on_empty():
    r = SpiceRack()
    assert r.spices_on(dish_token="ghost") == {}


def test_total_dishes_in_progress():
    r = SpiceRack()
    r.add_to_dish(dish_token="a", spice=SpiceKind.CHILI, count=1)
    r.add_to_dish(dish_token="b", spice=SpiceKind.SALT, count=1)
    assert r.total_dishes_in_progress() == 2
