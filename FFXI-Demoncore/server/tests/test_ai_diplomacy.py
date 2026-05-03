"""Tests for AI diplomacy."""
from __future__ import annotations

from server.ai_diplomacy import (
    AIDiplomacy,
    ClauseKind,
    TreatyClause,
    TreatyStatus,
)


def _ceasefire() -> tuple[TreatyClause, ...]:
    return (
        TreatyClause(kind=ClauseKind.CEASE_HOSTILITY),
        TreatyClause(kind=ClauseKind.RETURN_PRISONERS),
    )


def test_propose_creates_treaty():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="bastok", faction_b="san_doria",
        clauses=_ceasefire(),
    )
    assert res.accepted
    assert res.treaty.status == TreatyStatus.PROPOSED


def test_propose_self_rejected():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="bastok", faction_b="bastok",
        clauses=_ceasefire(),
    )
    assert not res.accepted


def test_propose_no_clauses_rejected():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="bastok", faction_b="san_doria",
        clauses=(),
    )
    assert not res.accepted


def test_duplicate_active_proposal_rejected():
    d = AIDiplomacy()
    d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    assert not res.accepted


def test_accept_treaty_both_sides():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    out1 = d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="a",
    )
    assert out1.new_status == TreatyStatus.PROPOSED
    out2 = d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="b",
        now_seconds=10.0,
    )
    assert out2.new_status == TreatyStatus.ACCEPTED


def test_accept_unknown_treaty():
    d = AIDiplomacy()
    assert d.accept_treaty(
        treaty_id="ghost", by_faction="a",
    ) is None


def test_accept_outsider_rejected():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    out = d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="c",
    )
    assert out is None


def test_reject_treaty():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    out = d.reject_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="b",
    )
    assert out.new_status == TreatyStatus.REJECTED


def test_violation_logged_below_limit():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="a",
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="b",
    )
    out = d.report_violation(
        treaty_id=res.treaty.treaty_id, violator="a",
        clause_kind=ClauseKind.CEASE_HOSTILITY,
    )
    assert out.new_status == TreatyStatus.ACCEPTED
    assert "violation logged" in out.note


def test_violation_limit_breaks_treaty():
    d = AIDiplomacy(violation_limit=2)
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="a",
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="b",
    )
    d.report_violation(
        treaty_id=res.treaty.treaty_id, violator="a",
        clause_kind=ClauseKind.CEASE_HOSTILITY,
    )
    out = d.report_violation(
        treaty_id=res.treaty.treaty_id, violator="b",
        clause_kind=ClauseKind.RETURN_PRISONERS,
    )
    assert out.new_status == TreatyStatus.BROKEN


def test_violation_unmatched_clause_returns_none():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="a",
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="b",
    )
    # OPEN_TRADE not in this treaty's clauses
    out = d.report_violation(
        treaty_id=res.treaty.treaty_id, violator="a",
        clause_kind=ClauseKind.OPEN_TRADE,
    )
    assert out is None


def test_violation_on_unaccepted_treaty():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    out = d.report_violation(
        treaty_id=res.treaty.treaty_id, violator="a",
        clause_kind=ClauseKind.CEASE_HOSTILITY,
    )
    assert out is None


def test_active_treaties_for_faction():
    d = AIDiplomacy()
    r1 = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    d.accept_treaty(
        treaty_id=r1.treaty.treaty_id, by_faction="a",
    )
    d.accept_treaty(
        treaty_id=r1.treaty.treaty_id, by_faction="b",
    )
    r2 = d.propose_treaty(
        faction_a="a", faction_b="c",
        clauses=_ceasefire(),
    )
    # r2 not accepted
    active = d.active_treaties_for("a")
    assert len(active) == 1


def test_expire_check_flips_status():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
        proposed_at_seconds=0.0,
        expires_at_seconds=100.0,
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="a",
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="b",
    )
    outs = d.expire_check(now_seconds=200.0)
    assert len(outs) == 1
    assert outs[0].new_status == TreatyStatus.EXPIRED


def test_expire_check_keeps_active():
    d = AIDiplomacy()
    res = d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
        proposed_at_seconds=0.0,
        expires_at_seconds=200.0,
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="a",
    )
    d.accept_treaty(
        treaty_id=res.treaty.treaty_id, by_faction="b",
    )
    outs = d.expire_check(now_seconds=100.0)
    assert outs == ()


def test_total_treaties():
    d = AIDiplomacy()
    d.propose_treaty(
        faction_a="a", faction_b="b",
        clauses=_ceasefire(),
    )
    d.propose_treaty(
        faction_a="c", faction_b="d",
        clauses=_ceasefire(),
    )
    assert d.total_treaties() == 2
