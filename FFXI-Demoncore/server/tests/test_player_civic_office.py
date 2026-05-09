"""Tests for player_civic_office."""
from __future__ import annotations

from server.player_civic_office import (
    PlayerCivicOfficeSystem, OfficeState,
)


def _create(
    s: PlayerCivicOfficeSystem,
    term: int = 90, salary: int = 100,
) -> str:
    return s.create_office(
        title="Bastok Magistrate",
        term_days=term, salary_per_day_gil=salary,
    )


def test_create_office_happy():
    s = PlayerCivicOfficeSystem()
    assert _create(s) is not None


def test_create_office_empty_title_blocked():
    s = PlayerCivicOfficeSystem()
    assert s.create_office(
        title="", term_days=90,
        salary_per_day_gil=100,
    ) is None


def test_create_office_zero_term_blocked():
    s = PlayerCivicOfficeSystem()
    assert _create(s, term=0) is None


def test_create_office_zero_salary_blocked():
    s = PlayerCivicOfficeSystem()
    assert _create(s, salary=0) is None


def test_appoint_happy():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    assert s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    ) is True
    assert s.office(
        office_id=oid,
    ).state == OfficeState.OCCUPIED


def test_appoint_already_occupied_blocked():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    assert s.appoint(
        office_id=oid, holder_id="bob",
        appointed_day=11,
    ) is False


def test_appoint_empty_holder_blocked():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    assert s.appoint(
        office_id=oid, holder_id="",
        appointed_day=10,
    ) is False


def test_collect_salary_happy():
    s = PlayerCivicOfficeSystem()
    oid = _create(s, salary=100)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    # Day 15 - day 10 = 5 days * 100/day = 500
    owed = s.collect_salary(
        office_id=oid, holder_id="alice",
        current_day=15,
    )
    assert owed == 500


def test_collect_salary_advances_baseline():
    s = PlayerCivicOfficeSystem()
    oid = _create(s, salary=100)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    s.collect_salary(
        office_id=oid, holder_id="alice",
        current_day=15,
    )
    # Second collection: only days 15-20 owed
    owed = s.collect_salary(
        office_id=oid, holder_id="alice",
        current_day=20,
    )
    assert owed == 500


def test_collect_salary_caps_at_term_end():
    s = PlayerCivicOfficeSystem()
    oid = _create(s, term=10, salary=100)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    # term ends at day 20; day 50 caps to day 20
    owed = s.collect_salary(
        office_id=oid, holder_id="alice",
        current_day=50,
    )
    assert owed == 1000  # 10 days * 100


def test_collect_salary_wrong_holder_blocked():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    assert s.collect_salary(
        office_id=oid, holder_id="bob",
        current_day=15,
    ) is None


def test_collect_salary_vacant_blocked():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    assert s.collect_salary(
        office_id=oid, holder_id="alice",
        current_day=15,
    ) is None


def test_vacate_happy():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    assert s.vacate(
        office_id=oid, holder_id="alice",
    ) is True
    assert s.office(
        office_id=oid,
    ).state == OfficeState.VACANT


def test_vacate_wrong_holder_blocked():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    assert s.vacate(
        office_id=oid, holder_id="bob",
    ) is False


def test_vacate_already_vacant_blocked():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    assert s.vacate(
        office_id=oid, holder_id="alice",
    ) is False


def test_re_appoint_after_vacate():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    s.vacate(
        office_id=oid, holder_id="alice",
    )
    assert s.appoint(
        office_id=oid, holder_id="bob",
        appointed_day=20,
    ) is True


def test_lifetime_salary_tracked():
    s = PlayerCivicOfficeSystem()
    oid = _create(s, salary=50)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    s.collect_salary(
        office_id=oid, holder_id="alice",
        current_day=20,
    )
    s.collect_salary(
        office_id=oid, holder_id="alice",
        current_day=30,
    )
    # 20 days * 50 = 1000
    assert s.office(
        office_id=oid,
    ).salary_paid_lifetime_gil == 1000


def test_term_remaining():
    s = PlayerCivicOfficeSystem()
    oid = _create(s, term=90)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    # appointed at 10, term 90 -> ends 100; day 30 -> 70 remaining
    assert s.term_remaining(
        office_id=oid, current_day=30,
    ) == 70


def test_term_remaining_clamps_at_zero():
    s = PlayerCivicOfficeSystem()
    oid = _create(s, term=10)
    s.appoint(
        office_id=oid, holder_id="alice",
        appointed_day=10,
    )
    assert s.term_remaining(
        office_id=oid, current_day=50,
    ) == 0


def test_term_remaining_vacant_returns_none():
    s = PlayerCivicOfficeSystem()
    oid = _create(s)
    assert s.term_remaining(
        office_id=oid, current_day=10,
    ) is None


def test_unknown_office():
    s = PlayerCivicOfficeSystem()
    assert s.office(office_id="ghost") is None


def test_enum_count():
    assert len(list(OfficeState)) == 2
