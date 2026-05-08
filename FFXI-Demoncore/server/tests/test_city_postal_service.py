"""Tests for city_postal_service."""
from __future__ import annotations

from server.city_postal_service import (
    CityPostalService, ParcelClass, ParcelState,
)


def _setup(s):
    s.open_office(city="bastok")
    s.open_office(city="windy")
    s.add_route(
        from_city="bastok", to_city="windy",
        transit_days=5,
    )


def _post(s, **overrides):
    args = dict(
        from_city="bastok", to_city="windy",
        sender="bob", recipient="cara", weight=2,
        parcel_class=ParcelClass.LETTER,
        postage_paid=50, posted_day=10,
    )
    args.update(overrides)
    return s.post_parcel(**args)


def test_open_office():
    s = CityPostalService()
    assert s.open_office(city="bastok") is True


def test_open_office_dup():
    s = CityPostalService()
    s.open_office(city="bastok")
    assert s.open_office(city="bastok") is False


def test_open_office_blank():
    s = CityPostalService()
    assert s.open_office(city="") is False


def test_add_route_happy():
    s = CityPostalService()
    s.open_office(city="bastok")
    s.open_office(city="windy")
    assert s.add_route(
        from_city="bastok", to_city="windy",
        transit_days=5,
    ) is True


def test_add_route_zero_days():
    s = CityPostalService()
    s.open_office(city="bastok")
    s.open_office(city="windy")
    assert s.add_route(
        from_city="bastok", to_city="windy",
        transit_days=0,
    ) is False


def test_add_route_unknown_city():
    s = CityPostalService()
    s.open_office(city="bastok")
    assert s.add_route(
        from_city="bastok", to_city="windy",
        transit_days=5,
    ) is False


def test_add_route_self():
    s = CityPostalService()
    s.open_office(city="bastok")
    assert s.add_route(
        from_city="bastok", to_city="bastok",
        transit_days=5,
    ) is False


def test_post_happy():
    s = CityPostalService()
    _setup(s)
    pid = _post(s)
    assert pid is not None


def test_post_no_route():
    s = CityPostalService()
    s.open_office(city="bastok")
    s.open_office(city="windy")
    pid = _post(s)
    assert pid is None


def test_post_underpaid():
    s = CityPostalService()
    _setup(s)
    pid = _post(s, postage_paid=10)
    assert pid is None


def test_post_zero_weight():
    s = CityPostalService()
    _setup(s)
    pid = _post(s, weight=0)
    assert pid is None


def test_post_freight_correct_postage():
    s = CityPostalService()
    _setup(s)
    pid = _post(
        s, parcel_class=ParcelClass.FREIGHT,
        postage_paid=1_000,
    )
    assert pid is not None


def test_post_freight_underpaid():
    s = CityPostalService()
    _setup(s)
    pid = _post(
        s, parcel_class=ParcelClass.FREIGHT,
        postage_paid=500,
    )
    assert pid is None


def test_tick_in_transit():
    s = CityPostalService()
    _setup(s)
    pid = _post(s, posted_day=10)
    s.tick(now_day=11)
    p = s.parcel(parcel_id=pid)
    assert p.state == ParcelState.IN_TRANSIT


def test_tick_delivered_at_eta():
    s = CityPostalService()
    _setup(s)
    pid = _post(s, posted_day=10)  # eta = 15
    s.tick(now_day=11)
    s.tick(now_day=15)
    p = s.parcel(parcel_id=pid)
    assert p.state == ParcelState.DELIVERED


def test_tick_skips_to_delivered_if_late():
    s = CityPostalService()
    _setup(s)
    pid = _post(s, posted_day=10)
    # Single tick crossing both transitions
    s.tick(now_day=20)
    p = s.parcel(parcel_id=pid)
    assert p.state == ParcelState.DELIVERED


def test_mark_lost():
    s = CityPostalService()
    _setup(s)
    pid = _post(s)
    s.tick(now_day=11)
    assert s.mark_lost(
        parcel_id=pid, leg_at_city="midpoint",
    ) is True


def test_mark_lost_after_delivered_blocked():
    s = CityPostalService()
    _setup(s)
    pid = _post(s, posted_day=10)
    s.tick(now_day=20)
    assert s.mark_lost(
        parcel_id=pid, leg_at_city="midpoint",
    ) is False


def test_refund_registered():
    s = CityPostalService()
    _setup(s)
    pid = _post(
        s, parcel_class=ParcelClass.REGISTERED,
        postage_paid=5_000,
    )
    s.mark_lost(parcel_id=pid, leg_at_city="x")
    assert s.refund(parcel_id=pid) == 5_000
    p = s.parcel(parcel_id=pid)
    assert p.state == ParcelState.REFUNDED


def test_refund_letter_returns_zero():
    s = CityPostalService()
    _setup(s)
    pid = _post(s)
    s.mark_lost(parcel_id=pid, leg_at_city="x")
    assert s.refund(parcel_id=pid) == 0


def test_refund_unknown():
    s = CityPostalService()
    assert s.refund(parcel_id="ghost") == 0


def test_inbox_returns_delivered():
    s = CityPostalService()
    _setup(s)
    pid = _post(s, posted_day=10)
    s.tick(now_day=20)
    inbox = s.inbox(city="windy")
    assert any(p.parcel_id == pid for p in inbox)


def test_outbox_returns_in_flight():
    s = CityPostalService()
    _setup(s)
    pid = _post(s, posted_day=10)
    s.tick(now_day=11)
    out = s.outbox(city="bastok")
    assert any(p.parcel_id == pid for p in out)


def test_outbox_excludes_delivered():
    s = CityPostalService()
    _setup(s)
    pid = _post(s, posted_day=10)
    s.tick(now_day=20)
    out = s.outbox(city="bastok")
    assert all(p.parcel_id != pid for p in out)


def test_enum_counts():
    assert len(list(ParcelClass)) == 4
    assert len(list(ParcelState)) == 5
