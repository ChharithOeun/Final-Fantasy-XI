"""Tests for city_hospital."""
from __future__ import annotations

from server.city_hospital import (
    CityHospitalSystem, ServiceKind, BedState,
)


def test_open_happy():
    s = CityHospitalSystem()
    assert s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    ) is True


def test_open_blank_blocked():
    s = CityHospitalSystem()
    assert s.open_hospital(
        hospital_id="", city="bastok", bed_capacity=4,
    ) is False


def test_open_negative_capacity():
    s = CityHospitalSystem()
    assert s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=-1,
    ) is False


def test_open_dup():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    assert s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    ) is False


def test_set_price_happy():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    assert s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.HP_RESTORE, gil=100,
    ) is True


def test_set_price_negative_blocked():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    assert s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.HP_RESTORE, gil=-1,
    ) is False


def test_set_price_unknown_hospital():
    s = CityHospitalSystem()
    assert s.set_price(
        hospital_id="ghost",
        kind=ServiceKind.HP_RESTORE, gil=100,
    ) is False


def test_render_happy():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.HP_RESTORE, gil=100,
    )
    ok, _ = s.render_service(
        hospital_id="bastok_h",
        kind=ServiceKind.HP_RESTORE, player_id="bob",
        gil_paid=100,
    )
    assert ok is True


def test_render_unpriced():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    ok, reason = s.render_service(
        hospital_id="bastok_h",
        kind=ServiceKind.HP_RESTORE, player_id="bob",
        gil_paid=100,
    )
    assert ok is False and reason == "unpriced"


def test_render_insufficient():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.HP_RESTORE, gil=100,
    )
    ok, reason = s.render_service(
        hospital_id="bastok_h",
        kind=ServiceKind.HP_RESTORE, player_id="bob",
        gil_paid=50,
    )
    assert ok is False and reason == "insufficient_gil"


def test_render_bed_rest_redirected():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, gil=200,
    )
    ok, reason = s.render_service(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, player_id="bob",
        gil_paid=200,
    )
    assert ok is False and reason == "use_request_bed"


def test_request_bed_happy():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, gil=200,
    )
    oid = s.request_bed(
        hospital_id="bastok_h", player_id="bob",
        gil_paid_per_hour=200, hours=2, now_hour=10,
    )
    assert oid is not None


def test_request_bed_capacity_full():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=2,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, gil=200,
    )
    s.request_bed(
        hospital_id="bastok_h", player_id="bob",
        gil_paid_per_hour=200, hours=2, now_hour=10,
    )
    s.request_bed(
        hospital_id="bastok_h", player_id="cara",
        gil_paid_per_hour=200, hours=2, now_hour=10,
    )
    # Third blocked
    out = s.request_bed(
        hospital_id="bastok_h", player_id="dave",
        gil_paid_per_hour=200, hours=2, now_hour=10,
    )
    assert out is None


def test_request_bed_underpaid():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, gil=200,
    )
    out = s.request_bed(
        hospital_id="bastok_h", player_id="bob",
        gil_paid_per_hour=100, hours=2, now_hour=10,
    )
    assert out is None


def test_request_bed_zero_hours():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, gil=200,
    )
    out = s.request_bed(
        hospital_id="bastok_h", player_id="bob",
        gil_paid_per_hour=200, hours=0, now_hour=10,
    )
    assert out is None


def test_release_bed_happy():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, gil=200,
    )
    oid = s.request_bed(
        hospital_id="bastok_h", player_id="bob",
        gil_paid_per_hour=200, hours=2, now_hour=10,
    )
    assert s.release_bed(
        occupancy_id=oid, now_hour=12,
    ) is True


def test_release_double_blocked():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, gil=200,
    )
    oid = s.request_bed(
        hospital_id="bastok_h", player_id="bob",
        gil_paid_per_hour=200, hours=2, now_hour=10,
    )
    s.release_bed(occupancy_id=oid, now_hour=12)
    assert s.release_bed(
        occupancy_id=oid, now_hour=13,
    ) is False


def test_release_unknown():
    s = CityHospitalSystem()
    assert s.release_bed(
        occupancy_id="ghost", now_hour=10,
    ) is False


def test_occupied_count_drops_after_release():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, gil=200,
    )
    oid = s.request_bed(
        hospital_id="bastok_h", player_id="bob",
        gil_paid_per_hour=200, hours=2, now_hour=10,
    )
    assert s.occupied_count(
        hospital_id="bastok_h",
    ) == 1
    s.release_bed(occupancy_id=oid, now_hour=12)
    assert s.occupied_count(
        hospital_id="bastok_h",
    ) == 0


def test_occupancies_lookup():
    s = CityHospitalSystem()
    s.open_hospital(
        hospital_id="bastok_h", city="bastok",
        bed_capacity=4,
    )
    s.set_price(
        hospital_id="bastok_h",
        kind=ServiceKind.BED_REST, gil=200,
    )
    s.request_bed(
        hospital_id="bastok_h", player_id="bob",
        gil_paid_per_hour=200, hours=2, now_hour=10,
    )
    out = s.occupancies(hospital_id="bastok_h")
    assert len(out) == 1


def test_render_unknown_hospital():
    s = CityHospitalSystem()
    ok, reason = s.render_service(
        hospital_id="ghost",
        kind=ServiceKind.HP_RESTORE, player_id="bob",
        gil_paid=100,
    )
    assert ok is False and reason == "no_hospital"


def test_enum_counts():
    assert len(list(ServiceKind)) == 8
    assert len(list(BedState)) == 2
