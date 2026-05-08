"""Tests for server_chronicle."""
from __future__ import annotations

from server.server_chronicle import (
    EventKind, Importance, ServerChronicle,
)


def _record_basic(c, **overrides):
    args = dict(
        event_kind=EventKind.HNM_FELLED,
        title="Behemoth Felled",
        body="Tart's party defeated Behemoth.",
        witnesses=["bob", "cara"],
        location="behemoth_dominion",
        importance=Importance.NOTABLE,
        now_ms=1000,
    )
    args.update(overrides)
    return c.record(**args)


def test_record_happy():
    c = ServerChronicle()
    eid = _record_basic(c)
    assert eid is not None
    assert c.total() == 1


def test_record_blank_title_blocked():
    c = ServerChronicle()
    eid = _record_basic(c, title="")
    assert eid is None


def test_record_blank_body_blocked():
    c = ServerChronicle()
    eid = _record_basic(c, body="")
    assert eid is None


def test_record_negative_time_blocked():
    c = ServerChronicle()
    eid = _record_basic(c, now_ms=-1)
    assert eid is None


def test_witnesses_deduped():
    c = ServerChronicle()
    eid = _record_basic(
        c, witnesses=["bob", "bob", "cara"],
    )
    e = c.entry(entry_id=eid)
    assert len(e.witnesses) == 2


def test_witnesses_blank_filtered():
    c = ServerChronicle()
    eid = _record_basic(
        c, witnesses=["bob", "", "cara"],
    )
    e = c.entry(entry_id=eid)
    assert "" not in e.witnesses


def test_entries_in_range():
    c = ServerChronicle()
    _record_basic(c, now_ms=1000)
    _record_basic(c, now_ms=2000)
    _record_basic(c, now_ms=3000)
    out = c.entries_in_range(start_ms=1500, end_ms=2500)
    assert len(out) == 1
    assert out[0].chronicled_at_ms == 2000


def test_entries_about_witness():
    c = ServerChronicle()
    _record_basic(c, witnesses=["bob"], now_ms=1000)
    _record_basic(c, witnesses=["cara"], now_ms=2000)
    out = c.entries_about(witness_id="bob")
    assert len(out) == 1


def test_entries_in_zone():
    c = ServerChronicle()
    _record_basic(c, location="bastok", now_ms=1000)
    _record_basic(c, location="sandy", now_ms=2000)
    out = c.entries_in_zone(zone_id="bastok")
    assert len(out) == 1


def test_entries_at_importance():
    c = ServerChronicle()
    _record_basic(c, importance=Importance.NOTABLE)
    _record_basic(c, importance=Importance.EPIC)
    out = c.entries_at_importance(
        importance=Importance.EPIC,
    )
    assert len(out) == 1


def test_entry_unknown():
    c = ServerChronicle()
    assert c.entry(entry_id="ghost") is None


def test_server_wide_no_location():
    c = ServerChronicle()
    eid = _record_basic(c, location=None)
    e = c.entry(entry_id=eid)
    assert e.location is None


def test_zone_query_excludes_server_wide():
    c = ServerChronicle()
    _record_basic(c, location=None)
    out = c.entries_in_zone(zone_id="anywhere")
    assert out == []


def test_total_increments():
    c = ServerChronicle()
    _record_basic(c, now_ms=1000)
    _record_basic(c, now_ms=2000)
    assert c.total() == 2


def test_fourteen_event_kinds():
    assert len(list(EventKind)) == 14


def test_four_importance_levels():
    assert len(list(Importance)) == 4
