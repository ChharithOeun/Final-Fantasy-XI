"""Tests for city_prison."""
from __future__ import annotations

from server.city_prison import (
    CityPrisonSystem, PrisonState,
)


def _open(s):
    s.open_prison(
        prison_id="bastok_p", city="bastok",
        capacity=4,
    )


def _book(s, **overrides):
    args = dict(
        prison_id="bastok_p", prisoner_id="bob",
        case_id="case_1", sentence_days=10,
        now_day=10,
    )
    args.update(overrides)
    return s.book(**args)


def test_open_happy():
    s = CityPrisonSystem()
    assert s.open_prison(
        prison_id="bastok_p", city="bastok",
        capacity=4,
    ) is True


def test_open_zero_capacity():
    s = CityPrisonSystem()
    assert s.open_prison(
        prison_id="bastok_p", city="bastok",
        capacity=0,
    ) is False


def test_open_dup():
    s = CityPrisonSystem()
    _open(s)
    assert s.open_prison(
        prison_id="bastok_p", city="bastok",
        capacity=4,
    ) is False


def test_book_happy():
    s = CityPrisonSystem()
    _open(s)
    assert _book(s) is not None


def test_book_zero_sentence():
    s = CityPrisonSystem()
    _open(s)
    assert _book(s, sentence_days=0) is None


def test_book_unknown_prison():
    s = CityPrisonSystem()
    assert _book(s) is None


def test_book_capacity_full():
    s = CityPrisonSystem()
    s.open_prison(
        prison_id="bastok_p", city="bastok",
        capacity=2,
    )
    _book(s, prisoner_id="bob")
    _book(s, prisoner_id="cara")
    assert _book(s, prisoner_id="dave") is None


def test_assign_cell_happy():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s)
    assert s.assign_cell(
        record_id=rid, now_day=10,
    ) is True


def test_assign_double_blocked():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s)
    s.assign_cell(record_id=rid, now_day=10)
    assert s.assign_cell(
        record_id=rid, now_day=11,
    ) is False


def test_tick_accumulates_served_days():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s, sentence_days=10, now_day=10)
    s.assign_cell(record_id=rid, now_day=10)
    s.tick(now_day=15)
    r = s.record(record_id=rid)
    assert r.served_days == 5
    assert r.state == PrisonState.SERVING


def test_tick_discharges_when_complete():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s, sentence_days=10, now_day=10)
    s.assign_cell(record_id=rid, now_day=10)
    changes = s.tick(now_day=20)
    assert (rid, PrisonState.DISCHARGED) in changes


def test_apply_good_behavior_reduces():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s, sentence_days=10, now_day=10)
    s.assign_cell(record_id=rid, now_day=10)
    s.tick(now_day=12)
    assert s.apply_good_behavior(
        record_id=rid, days=3,
    ) is True
    r = s.record(record_id=rid)
    assert r.sentence_days == 7


def test_apply_good_behavior_negative_blocked():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s)
    s.assign_cell(record_id=rid, now_day=10)
    assert s.apply_good_behavior(
        record_id=rid, days=-1,
    ) is False


def test_request_parole_at_half_served():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s, sentence_days=10, now_day=10)
    s.assign_cell(record_id=rid, now_day=10)
    s.tick(now_day=15)  # 5 served of 10 -> eligible
    assert s.request_parole(
        record_id=rid, now_day=15,
    ) is True


def test_request_parole_too_early():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s, sentence_days=10, now_day=10)
    s.assign_cell(record_id=rid, now_day=10)
    s.tick(now_day=12)  # 2 served — not half
    assert s.request_parole(
        record_id=rid, now_day=12,
    ) is False


def test_report_in_parole():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s, sentence_days=10, now_day=10)
    s.assign_cell(record_id=rid, now_day=10)
    s.tick(now_day=15)
    s.request_parole(record_id=rid, now_day=15)
    assert s.report_in_parole(
        record_id=rid, now_day=18,
    ) is True


def test_report_in_parole_completes():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s, sentence_days=10, now_day=10)
    s.assign_cell(record_id=rid, now_day=10)
    s.tick(now_day=15)  # 5 served
    s.request_parole(record_id=rid, now_day=15)
    s.report_in_parole(record_id=rid, now_day=20)
    r = s.record(record_id=rid)
    assert r.state == PrisonState.DISCHARGED


def test_mark_escaped():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s)
    s.assign_cell(record_id=rid, now_day=10)
    assert s.mark_escaped(
        record_id=rid, now_day=12,
    ) is True
    assert s.record(
        record_id=rid,
    ).state == PrisonState.ESCAPED


def test_mark_escaped_after_discharge_blocked():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s, sentence_days=2, now_day=10)
    s.assign_cell(record_id=rid, now_day=10)
    s.tick(now_day=12)
    assert s.mark_escaped(
        record_id=rid, now_day=13,
    ) is False


def test_pardon_happy():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s, sentence_days=10, now_day=10)
    s.assign_cell(record_id=rid, now_day=10)
    s.tick(now_day=12)
    assert s.pardon(
        record_id=rid, now_day=13,
    ) is True
    assert s.record(
        record_id=rid,
    ).state == PrisonState.DISCHARGED


def test_pardon_after_escape_blocked():
    s = CityPrisonSystem()
    _open(s)
    rid = _book(s)
    s.assign_cell(record_id=rid, now_day=10)
    s.mark_escaped(record_id=rid, now_day=11)
    assert s.pardon(
        record_id=rid, now_day=12,
    ) is False


def test_records_for_prisoner():
    s = CityPrisonSystem()
    _open(s)
    _book(s, prisoner_id="bob", case_id="c1")
    _book(s, prisoner_id="bob", case_id="c2")
    _book(s, prisoner_id="cara", case_id="c3")
    assert len(s.records_for(prisoner_id="bob")) == 2


def test_active_records():
    s = CityPrisonSystem()
    _open(s)
    rid_a = _book(s, prisoner_id="bob",
                  sentence_days=10)
    rid_b = _book(s, prisoner_id="cara",
                  sentence_days=2)
    s.assign_cell(record_id=rid_a, now_day=10)
    s.assign_cell(record_id=rid_b, now_day=10)
    s.tick(now_day=12)  # rid_b discharged
    out = s.active_records(prison_id="bastok_p")
    ids = [r.record_id for r in out]
    assert rid_a in ids
    assert rid_b not in ids


def test_enum_count():
    assert len(list(PrisonState)) == 5
