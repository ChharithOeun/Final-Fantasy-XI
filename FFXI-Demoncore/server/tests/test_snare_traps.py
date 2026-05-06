"""Tests for snare_traps."""
from __future__ import annotations

from server.snare_traps import (
    CheckOutcome, SnareTrapRegistry, TrapKind, WeightClass,
)


def _place(r, tid="t1", **overrides):
    kwargs = dict(
        trap_id=tid, owner_id="alice",
        kind=TrapKind.FOOT_SNARE, zone="east_wood",
        x=0.0, y=0.0, baited=False, placed_at=10,
    )
    kwargs.update(overrides)
    return r.place(**kwargs)


def test_place_happy():
    r = SnareTrapRegistry()
    assert _place(r) is True


def test_place_blank_id_blocked():
    r = SnareTrapRegistry()
    assert _place(r, tid="") is False


def test_place_blank_owner_blocked():
    r = SnareTrapRegistry()
    assert _place(r, owner_id="") is False


def test_place_blank_zone_blocked():
    r = SnareTrapRegistry()
    assert _place(r, zone="") is False


def test_place_duplicate_blocked():
    r = SnareTrapRegistry()
    _place(r)
    assert _place(r) is False


def test_check_no_traffic_empty():
    r = SnareTrapRegistry()
    _place(r)
    out = r.check(
        trap_id="t1", traffic_kind="",
        traffic_weight=WeightClass.SMALL, now=20,
    )
    assert out.outcome == CheckOutcome.EMPTY


def test_check_unknown_trap_empty():
    r = SnareTrapRegistry()
    out = r.check(
        trap_id="ghost", traffic_kind="rabbit",
        traffic_weight=WeightClass.SMALL, now=20,
    )
    assert out.outcome == CheckOutcome.EMPTY


def test_foot_snare_catches_small():
    r = SnareTrapRegistry()
    _place(r, kind=TrapKind.FOOT_SNARE)
    out = r.check(
        trap_id="t1", traffic_kind="rabbit",
        traffic_weight=WeightClass.SMALL, now=20,
    )
    assert out.outcome == CheckOutcome.PREY_CAUGHT
    assert out.quarry_id == "rabbit"


def test_foot_snare_destroyed_by_large():
    r = SnareTrapRegistry()
    _place(r, kind=TrapKind.FOOT_SNARE)
    out = r.check(
        trap_id="t1", traffic_kind="manticore",
        traffic_weight=WeightClass.LARGE, now=20,
    )
    assert out.outcome == CheckOutcome.DESTROYED
    assert out.trap_destroyed is True


def test_pit_trap_catches_large():
    r = SnareTrapRegistry()
    _place(r, kind=TrapKind.PIT_TRAP)
    out = r.check(
        trap_id="t1", traffic_kind="dhalmel",
        traffic_weight=WeightClass.LARGE, now=20,
    )
    assert out.outcome == CheckOutcome.PREY_CAUGHT


def test_pit_trap_sprung_by_small():
    r = SnareTrapRegistry()
    _place(r, kind=TrapKind.PIT_TRAP)
    out = r.check(
        trap_id="t1", traffic_kind="rabbit",
        traffic_weight=WeightClass.SMALL, now=20,
    )
    # rabbit too light, sprung but no catch
    assert out.outcome == CheckOutcome.SPRUNG_EMPTY


def test_net_trap_destroyed_by_large():
    r = SnareTrapRegistry()
    _place(r, kind=TrapKind.NET_TRAP)
    out = r.check(
        trap_id="t1", traffic_kind="manticore",
        traffic_weight=WeightClass.LARGE, now=20,
    )
    assert out.outcome == CheckOutcome.DESTROYED


def test_baited_cage_catches():
    r = SnareTrapRegistry()
    _place(r, kind=TrapKind.BAITED_CAGE, baited=True)
    out = r.check(
        trap_id="t1", traffic_kind="fox",
        traffic_weight=WeightClass.MEDIUM, now=20,
    )
    assert out.outcome == CheckOutcome.PREY_CAUGHT


def test_trap_disarmed_after_catch():
    r = SnareTrapRegistry()
    _place(r, kind=TrapKind.FOOT_SNARE)
    r.check(
        trap_id="t1", traffic_kind="rabbit",
        traffic_weight=WeightClass.SMALL, now=20,
    )
    # subsequent check returns empty (trap is sprung)
    out = r.check(
        trap_id="t1", traffic_kind="rabbit",
        traffic_weight=WeightClass.SMALL, now=30,
    )
    assert out.outcome == CheckOutcome.EMPTY


def test_remove_owner():
    r = SnareTrapRegistry()
    _place(r)
    assert r.remove(trap_id="t1", by_owner_id="alice") is True
    assert r.total_traps() == 0


def test_remove_non_owner_blocked():
    r = SnareTrapRegistry()
    _place(r)
    assert r.remove(trap_id="t1", by_owner_id="bob") is False


def test_remove_unknown():
    r = SnareTrapRegistry()
    assert r.remove(trap_id="ghost", by_owner_id="alice") is False


def test_traps_in_zone_filters():
    r = SnareTrapRegistry()
    _place(r, tid="a", zone="east_wood")
    _place(r, tid="b", zone="south_marsh")
    out = r.traps_in_zone(zone="east_wood")
    assert len(out) == 1


def test_get_unknown():
    r = SnareTrapRegistry()
    assert r.get(trap_id="ghost") is None


def test_six_trap_kinds():
    assert len(list(TrapKind)) == 6


def test_three_weight_classes():
    assert len(list(WeightClass)) == 3


def test_four_check_outcomes():
    assert len(list(CheckOutcome)) == 4
