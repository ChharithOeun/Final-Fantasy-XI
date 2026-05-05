"""Tests for submersible dock."""
from __future__ import annotations

from server.submersible_craft import SubClass
from server.submersible_dock import SubmersibleDock


def test_register_port_happy():
    d = SubmersibleDock()
    ok = d.register_port(
        port_id="bastok_dock",
        allowed_classes=(SubClass.DIVING_BELL, SubClass.SCOUT_SUB),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    assert ok is True


def test_register_port_blank_id_rejected():
    d = SubmersibleDock()
    ok = d.register_port(
        port_id="",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    assert ok is False


def test_register_port_no_classes_rejected():
    d = SubmersibleDock()
    ok = d.register_port(
        port_id="x",
        allowed_classes=(),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    assert ok is False


def test_register_port_zero_rates_rejected():
    d = SubmersibleDock()
    ok = d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=0,
        fuel_rate_gil_per_cell=20,
    )
    assert ok is False


def test_stow_happy():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.SCOUT_SUB,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    r = d.stow(
        sub_id="s1",
        sub_class=SubClass.SCOUT_SUB,
        port_id="x",
        current_hp=500, hp_max=900,
        fuel_remaining=10,
    )
    assert r.accepted is True


def test_stow_class_not_serviced():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    r = d.stow(
        sub_id="s1",
        sub_class=SubClass.ABYSSAL_RIG,
        port_id="x",
        current_hp=100, hp_max=100,
        fuel_remaining=1,
    )
    assert r.accepted is False


def test_stow_unknown_port():
    d = SubmersibleDock()
    r = d.stow(
        sub_id="s1",
        sub_class=SubClass.DIVING_BELL,
        port_id="ghost",
        current_hp=100, hp_max=100,
        fuel_remaining=1,
    )
    assert r.accepted is False


def test_stow_duplicate_rejected():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    d.stow(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        port_id="x", current_hp=100, hp_max=400,
        fuel_remaining=1,
    )
    r = d.stow(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        port_id="x", current_hp=200, hp_max=400,
        fuel_remaining=2,
    )
    assert r.accepted is False


def test_retrieve_happy():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    d.stow(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        port_id="x", current_hp=200, hp_max=400,
        fuel_remaining=3,
    )
    sub = d.retrieve(sub_id="s1", port_id="x")
    assert sub is not None
    assert sub.sub_id == "s1"
    # double retrieve fails
    assert d.retrieve(sub_id="s1", port_id="x") is None


def test_retrieve_wrong_port():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    d.stow(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        port_id="x", current_hp=200, hp_max=400,
        fuel_remaining=3,
    )
    assert d.retrieve(sub_id="s1", port_id="y") is None


def test_repair_partial():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    d.stow(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        port_id="x", current_hp=100, hp_max=400,
        fuel_remaining=0,
    )
    # 100 gil at 5/hp = 20 hp
    r = d.repair(sub_id="s1", port_id="x", gil_paid=100)
    assert r.accepted is True
    assert r.hp_restored == 20
    assert r.new_hp == 120
    assert r.gil_consumed == 100


def test_repair_caps_at_max():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    d.stow(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        port_id="x", current_hp=350, hp_max=400,
        fuel_remaining=0,
    )
    # over-paying for full repair only consumes what's needed
    r = d.repair(sub_id="s1", port_id="x", gil_paid=10_000)
    assert r.hp_restored == 50
    assert r.gil_consumed == 250


def test_repair_already_max():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    d.stow(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        port_id="x", current_hp=400, hp_max=400,
        fuel_remaining=0,
    )
    r = d.repair(sub_id="s1", port_id="x", gil_paid=100)
    assert r.hp_restored == 0
    assert r.reason == "already at max"


def test_refuel_happy():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    d.stow(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        port_id="x", current_hp=400, hp_max=400,
        fuel_remaining=2,
    )
    r = d.refuel(sub_id="s1", port_id="x", gil_paid=100)
    # 100 / 20 = 5 cells
    assert r.accepted is True
    assert r.cells_added == 5
    assert r.new_fuel == 7
    assert r.gil_consumed == 100


def test_refuel_not_enough_gil():
    d = SubmersibleDock()
    d.register_port(
        port_id="x",
        allowed_classes=(SubClass.DIVING_BELL,),
        repair_rate_gil_per_hp=5,
        fuel_rate_gil_per_cell=20,
    )
    d.stow(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        port_id="x", current_hp=400, hp_max=400,
        fuel_remaining=1,
    )
    r = d.refuel(sub_id="s1", port_id="x", gil_paid=10)
    assert r.accepted is False


def test_repair_unknown_sub():
    d = SubmersibleDock()
    r = d.repair(sub_id="ghost", port_id="x", gil_paid=100)
    assert r.accepted is False
