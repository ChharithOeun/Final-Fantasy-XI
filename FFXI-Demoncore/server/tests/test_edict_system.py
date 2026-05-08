"""Tests for edict_system."""
from __future__ import annotations

from server.edict_system import (
    Edict, EdictKind, EdictState, EdictSystem,
)


def _tax_edict(eid="tax_1", nation="bastok",
               proposed=10, effective=12, sunset=26,
               proposer="cid",
               office="bastok_president"):
    return Edict(
        edict_id=eid, nation=nation,
        kind=EdictKind.TAX_REDUCTION,
        parameters={"reduction_pct": 30},
        proposer_id=proposer,
        proposing_office_id=office,
        proposed_day=proposed,
        effective_day=effective,
        sunset_day=sunset,
    )


def test_propose_happy():
    e = EdictSystem()
    assert e.propose_edict(_tax_edict()) is True


def test_propose_blank_id_blocked():
    e = EdictSystem()
    bad = Edict(
        edict_id="", nation="bastok",
        kind=EdictKind.TAX_REDUCTION,
        parameters={}, proposer_id="x",
        proposing_office_id="x",
        proposed_day=0, effective_day=1, sunset_day=2,
    )
    assert e.propose_edict(bad) is False


def test_propose_effective_before_proposed_blocked():
    e = EdictSystem()
    bad = _tax_edict(proposed=20, effective=10, sunset=30)
    assert e.propose_edict(bad) is False


def test_propose_sunset_before_effective_blocked():
    e = EdictSystem()
    bad = _tax_edict(proposed=10, effective=12, sunset=11)
    assert e.propose_edict(bad) is False


def test_propose_dup_blocked():
    e = EdictSystem()
    e.propose_edict(_tax_edict())
    assert e.propose_edict(_tax_edict()) is False


def test_activate_at_effective_day():
    e = EdictSystem()
    e.propose_edict(_tax_edict(effective=12))
    assert e.activate(edict_id="tax_1", now_day=12) is True
    assert e.state(
        edict_id="tax_1",
    ) == EdictState.IN_FORCE


def test_activate_too_early_blocked():
    e = EdictSystem()
    e.propose_edict(_tax_edict(effective=12))
    assert e.activate(
        edict_id="tax_1", now_day=10,
    ) is False


def test_activate_already_active_blocked():
    e = EdictSystem()
    e.propose_edict(_tax_edict(effective=12))
    e.activate(edict_id="tax_1", now_day=12)
    assert e.activate(
        edict_id="tax_1", now_day=15,
    ) is False


def test_repeal_by_proposing_office():
    e = EdictSystem()
    e.propose_edict(_tax_edict())
    e.activate(edict_id="tax_1", now_day=12)
    assert e.repeal(
        edict_id="tax_1",
        by_office_id="bastok_president",
    ) is True
    assert e.state(
        edict_id="tax_1",
    ) == EdictState.REPEALED


def test_repeal_by_other_office_blocked():
    e = EdictSystem()
    e.propose_edict(_tax_edict())
    e.activate(edict_id="tax_1", now_day=12)
    assert e.repeal(
        edict_id="tax_1",
        by_office_id="bastok_general",
    ) is False


def test_repeal_after_expired_blocked():
    e = EdictSystem()
    e.propose_edict(_tax_edict(sunset=26))
    e.activate(edict_id="tax_1", now_day=12)
    e.tick(now_day=30)  # past sunset
    assert e.repeal(
        edict_id="tax_1",
        by_office_id="bastok_president",
    ) is False


def test_tick_expires():
    e = EdictSystem()
    e.propose_edict(_tax_edict(sunset=26))
    e.activate(edict_id="tax_1", now_day=12)
    expired = e.tick(now_day=30)
    assert "tax_1" in expired
    assert e.state(
        edict_id="tax_1",
    ) == EdictState.EXPIRED


def test_tick_auto_activates_proposed():
    e = EdictSystem()
    e.propose_edict(_tax_edict(effective=12, sunset=26))
    e.tick(now_day=15)
    assert e.state(
        edict_id="tax_1",
    ) == EdictState.IN_FORCE


def test_tick_late_proposed_to_expired():
    e = EdictSystem()
    e.propose_edict(_tax_edict(effective=12, sunset=26))
    expired = e.tick(now_day=30)
    # Was PROPOSED but now past sunset -> expired
    assert "tax_1" in expired


def test_active_edicts():
    e = EdictSystem()
    e.propose_edict(_tax_edict("a"))
    e.propose_edict(_tax_edict("b", nation="sandy"))
    e.activate(edict_id="a", now_day=12)
    e.activate(edict_id="b", now_day=12)
    bastok_edicts = e.active_edicts(nation="bastok")
    assert {ed.edict_id for ed in bastok_edicts} == {"a"}


def test_edicts_of_kind_filter():
    e = EdictSystem()
    e.propose_edict(_tax_edict("a"))
    bounty = Edict(
        edict_id="b", nation="bastok",
        kind=EdictKind.BOUNTY_INCREASE,
        parameters={"pct": 50},
        proposer_id="cid",
        proposing_office_id="bastok_president",
        proposed_day=10, effective_day=12, sunset_day=20,
    )
    e.propose_edict(bounty)
    e.activate(edict_id="a", now_day=12)
    e.activate(edict_id="b", now_day=12)
    out = e.edicts_of_kind(
        nation="bastok", kind=EdictKind.BOUNTY_INCREASE,
    )
    assert len(out) == 1
    assert out[0].edict_id == "b"


def test_state_unknown_edict():
    e = EdictSystem()
    assert e.state(edict_id="ghost") is None


def test_six_edict_kinds():
    assert len(list(EdictKind)) == 6


def test_four_edict_states():
    assert len(list(EdictState)) == 4
