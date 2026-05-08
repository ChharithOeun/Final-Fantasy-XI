"""Tests for nation_edict."""
from __future__ import annotations

from server.nation_edict import (
    NationEdictSystem, EdictKind, EdictState,
)


def _issue(s, **overrides):
    args = dict(
        nation_id="bastok", kind=EdictKind.TAX_RATE,
        title="Bastok Tax 2026",
        body="Set income tax to 5%.",
        issuer_id="cid",
        effective_from=10,
        effective_until=375, issued_day=10,
    )
    args.update(overrides)
    return s.issue(**args)


def test_issue_happy():
    s = NationEdictSystem()
    assert _issue(s) is not None


def test_issue_blank_nation():
    s = NationEdictSystem()
    assert _issue(s, nation_id="") is None


def test_issue_blank_title():
    s = NationEdictSystem()
    assert _issue(s, title="") is None


def test_issue_inverted_dates():
    s = NationEdictSystem()
    assert _issue(
        s, effective_from=20, effective_until=10,
    ) is None


def test_issue_negative_from():
    s = NationEdictSystem()
    assert _issue(s, effective_from=-1) is None


def test_issue_starts_current_when_active():
    s = NationEdictSystem()
    eid = _issue(s, effective_from=10, issued_day=15)
    assert s.edict(
        edict_id=eid,
    ).state == EdictState.CURRENT


def test_issue_starts_proposed_future():
    s = NationEdictSystem()
    eid = _issue(s, effective_from=20, issued_day=10)
    assert s.edict(
        edict_id=eid,
    ).state == EdictState.PROPOSED


def test_repeal_happy():
    s = NationEdictSystem()
    eid = _issue(s)
    assert s.repeal(
        edict_id=eid, repealer_id="naji",
        now_day=20, reason="overturned",
    ) is True


def test_repeal_blank_reason():
    s = NationEdictSystem()
    eid = _issue(s)
    assert s.repeal(
        edict_id=eid, repealer_id="naji",
        now_day=20, reason="",
    ) is False


def test_repeal_after_expired_blocked():
    s = NationEdictSystem()
    eid = _issue(s, effective_until=20)
    s.tick(now_day=21)
    assert s.repeal(
        edict_id=eid, repealer_id="naji",
        now_day=22, reason="x",
    ) is False


def test_amend_happy():
    s = NationEdictSystem()
    old = _issue(s, title="Old", body="old")
    new = _issue(s, title="New", body="new",
                 effective_from=20, issued_day=20)
    assert s.amend(
        old_edict_id=old, new_edict_id=new,
        now_day=20,
    ) is True
    assert s.edict(
        edict_id=old,
    ).state == EdictState.AMENDED
    assert s.edict(
        edict_id=old,
    ).superseded_by == new


def test_amend_kind_mismatch():
    s = NationEdictSystem()
    old = _issue(s, kind=EdictKind.TAX_RATE)
    new = _issue(
        s, kind=EdictKind.GATE_HOURS,
        title="Gate", body="Gates close at 22:00",
    )
    assert s.amend(
        old_edict_id=old, new_edict_id=new,
        now_day=20,
    ) is False


def test_amend_nation_mismatch():
    s = NationEdictSystem()
    old = _issue(s, nation_id="bastok")
    new = _issue(s, nation_id="windy",
                 title="Windy Tax",
                 body="Set Windy tax 4%.")
    assert s.amend(
        old_edict_id=old, new_edict_id=new,
        now_day=20,
    ) is False


def test_amend_self_blocked():
    s = NationEdictSystem()
    eid = _issue(s)
    assert s.amend(
        old_edict_id=eid, new_edict_id=eid,
        now_day=20,
    ) is False


def test_tick_proposed_to_current():
    s = NationEdictSystem()
    eid = _issue(s, effective_from=20, issued_day=10)
    changes = s.tick(now_day=20)
    assert (eid, EdictState.CURRENT) in changes


def test_tick_current_to_expired():
    s = NationEdictSystem()
    eid = _issue(
        s, effective_from=10, effective_until=20,
        issued_day=10,
    )
    changes = s.tick(now_day=20)
    assert (eid, EdictState.EXPIRED) in changes


def test_active_for_filters():
    s = NationEdictSystem()
    a = _issue(s, kind=EdictKind.TAX_RATE,
               effective_from=10,
               effective_until=20,
               issued_day=10)
    b = _issue(s, kind=EdictKind.GATE_HOURS,
               title="Gate", body="b",
               effective_from=10,
               effective_until=20,
               issued_day=10)
    out = s.active_for(
        nation_id="bastok",
        kind=EdictKind.TAX_RATE, now_day=15,
    )
    ids = [e.edict_id for e in out]
    assert a in ids
    assert b not in ids


def test_active_for_excludes_expired():
    s = NationEdictSystem()
    eid = _issue(
        s, effective_from=10, effective_until=20,
        issued_day=10,
    )
    s.tick(now_day=20)
    out = s.active_for(
        nation_id="bastok",
        kind=EdictKind.TAX_RATE, now_day=21,
    )
    assert eid not in [e.edict_id for e in out]


def test_active_for_excludes_repealed():
    s = NationEdictSystem()
    eid = _issue(
        s, effective_from=10, effective_until=100,
        issued_day=10,
    )
    s.repeal(
        edict_id=eid, repealer_id="naji",
        now_day=15, reason="x",
    )
    out = s.active_for(
        nation_id="bastok",
        kind=EdictKind.TAX_RATE, now_day=16,
    )
    assert eid not in [e.edict_id for e in out]


def test_edicts_by_nation():
    s = NationEdictSystem()
    _issue(s, nation_id="bastok")
    _issue(s, nation_id="windy",
           title="Windy", body="x")
    _issue(s, nation_id="bastok",
           title="Bastok2", body="x")
    out = s.edicts_by_nation(nation_id="bastok")
    assert len(out) == 2


def test_edict_unknown():
    s = NationEdictSystem()
    assert s.edict(edict_id="ghost") is None


def test_enum_counts():
    assert len(list(EdictKind)) == 10
    assert len(list(EdictState)) == 5
