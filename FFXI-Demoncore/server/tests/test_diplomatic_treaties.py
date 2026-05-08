"""Tests for diplomatic_treaties."""
from __future__ import annotations

from server.diplomatic_treaties import (
    DiplomaticTreaties, Treaty, TreatyKind, TreatyState,
)


def _treaty(tid="t1", a="bastok", b="sandy",
            kind=TreatyKind.NON_AGGRESSION,
            drafted=10, duration=30):
    return Treaty(
        treaty_id=tid, nation_a=a, nation_b=b,
        kind=kind, drafted_day=drafted,
        duration_days=duration,
    )


def test_draft_happy():
    d = DiplomaticTreaties()
    assert d.draft_treaty(_treaty()) is True


def test_draft_blank_id_blocked():
    d = DiplomaticTreaties()
    bad = Treaty(
        treaty_id="", nation_a="a", nation_b="b",
        kind=TreatyKind.NON_AGGRESSION,
        drafted_day=10, duration_days=30,
    )
    assert d.draft_treaty(bad) is False


def test_draft_same_nation_blocked():
    d = DiplomaticTreaties()
    bad = _treaty(a="bastok", b="bastok")
    assert d.draft_treaty(bad) is False


def test_draft_zero_duration_blocked():
    d = DiplomaticTreaties()
    bad = _treaty(duration=0)
    assert d.draft_treaty(bad) is False


def test_draft_dup_blocked():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    assert d.draft_treaty(_treaty()) is False


def test_sign_first_half_signed():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    assert d.sign(
        treaty_id="t1", nation="bastok", now_day=15,
    ) is True
    assert d.state(
        treaty_id="t1",
    ) == TreatyState.HALF_SIGNED


def test_sign_both_in_force():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    d.sign(treaty_id="t1", nation="bastok", now_day=15)
    d.sign(treaty_id="t1", nation="sandy", now_day=16)
    assert d.state(
        treaty_id="t1",
    ) == TreatyState.IN_FORCE


def test_sign_outside_signatories_blocked():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    assert d.sign(
        treaty_id="t1", nation="windy", now_day=15,
    ) is False


def test_sign_dup_blocked():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    d.sign(treaty_id="t1", nation="bastok", now_day=15)
    assert d.sign(
        treaty_id="t1", nation="bastok", now_day=16,
    ) is False


def test_terminate_in_force():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    d.sign(treaty_id="t1", nation="bastok", now_day=15)
    d.sign(treaty_id="t1", nation="sandy", now_day=16)
    assert d.terminate(
        treaty_id="t1", by_nation="bastok", now_day=20,
    ) is True
    assert d.state(
        treaty_id="t1",
    ) == TreatyState.TERMINATED


def test_terminate_drafted_blocked():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    assert d.terminate(
        treaty_id="t1", by_nation="bastok", now_day=15,
    ) is False


def test_terminate_outside_signatories_blocked():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    d.sign(treaty_id="t1", nation="bastok", now_day=15)
    d.sign(treaty_id="t1", nation="sandy", now_day=16)
    assert d.terminate(
        treaty_id="t1", by_nation="windy", now_day=20,
    ) is False


def test_tick_expires():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty(duration=30))
    d.sign(treaty_id="t1", nation="bastok", now_day=15)
    d.sign(treaty_id="t1", nation="sandy", now_day=16)
    expired = d.tick(now_day=50)  # 16+30=46 < 50
    assert "t1" in expired
    assert d.state(
        treaty_id="t1",
    ) == TreatyState.EXPIRED


def test_tick_doesnt_expire_drafted():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    expired = d.tick(now_day=999)
    assert expired == []


def test_active_treaties_for():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty("a"))
    d.sign(treaty_id="a", nation="bastok", now_day=15)
    d.sign(treaty_id="a", nation="sandy", now_day=16)
    out = d.active_treaties_for(nation="bastok")
    assert len(out) == 1
    assert out[0].treaty_id == "a"


def test_active_treaties_for_third_party_excluded():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty("a"))
    d.sign(treaty_id="a", nation="bastok", now_day=15)
    d.sign(treaty_id="a", nation="sandy", now_day=16)
    out = d.active_treaties_for(nation="windy")
    assert out == []


def test_have_treaty_symmetric():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty(
        a="bastok", b="sandy",
        kind=TreatyKind.MUTUAL_DEFENSE,
    ))
    d.sign(treaty_id="t1", nation="bastok", now_day=15)
    d.sign(treaty_id="t1", nation="sandy", now_day=16)
    assert d.have_treaty(
        nation_a="sandy", nation_b="bastok",
        kind=TreatyKind.MUTUAL_DEFENSE,
    ) is True


def test_have_treaty_wrong_kind():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty(
        kind=TreatyKind.NON_AGGRESSION,
    ))
    d.sign(treaty_id="t1", nation="bastok", now_day=15)
    d.sign(treaty_id="t1", nation="sandy", now_day=16)
    assert d.have_treaty(
        nation_a="bastok", nation_b="sandy",
        kind=TreatyKind.MUTUAL_DEFENSE,
    ) is False


def test_have_treaty_when_terminated():
    d = DiplomaticTreaties()
    d.draft_treaty(_treaty())
    d.sign(treaty_id="t1", nation="bastok", now_day=15)
    d.sign(treaty_id="t1", nation="sandy", now_day=16)
    d.terminate(
        treaty_id="t1", by_nation="bastok", now_day=20,
    )
    assert d.have_treaty(
        nation_a="bastok", nation_b="sandy",
        kind=TreatyKind.NON_AGGRESSION,
    ) is False


def test_six_treaty_kinds():
    assert len(list(TreatyKind)) == 6


def test_five_treaty_states():
    assert len(list(TreatyState)) == 5
