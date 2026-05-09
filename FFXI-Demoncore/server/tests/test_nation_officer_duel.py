"""Tests for nation_officer_duel."""
from __future__ import annotations

from server.nation_officer_duel import (
    NationOfficerDuelSystem, Stake, DuelState,
    DuelOutcome,
)


def _propose(s, **overrides):
    args = dict(
        challenger="off_volker", target="off_naji",
        stake=Stake.HONOR_ONLY, purse_gil=0,
        proposed_day=10,
    )
    args.update(overrides)
    return s.propose(**args)


def test_propose_happy():
    s = NationOfficerDuelSystem()
    assert _propose(s) is not None


def test_propose_self_blocked():
    s = NationOfficerDuelSystem()
    assert _propose(
        s, challenger="x", target="x",
    ) is None


def test_propose_blank():
    s = NationOfficerDuelSystem()
    assert _propose(s, challenger="") is None


def test_propose_gil_purse_zero_blocked():
    s = NationOfficerDuelSystem()
    assert _propose(
        s, stake=Stake.GIL_PURSE, purse_gil=0,
    ) is None


def test_propose_negative_purse():
    s = NationOfficerDuelSystem()
    assert _propose(s, purse_gil=-1) is None


def test_accept_happy():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    assert s.accept(duel_id=did) is True


def test_accept_double_blocked():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    s.accept(duel_id=did)
    assert s.accept(duel_id=did) is False


def test_decline_happy():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    assert s.decline(duel_id=did) is True


def test_decline_after_accept_blocked():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    s.accept(duel_id=did)
    assert s.decline(duel_id=did) is False


def test_expire():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    assert s.expire(duel_id=did) is True


def test_resolve_challenger_wins():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    s.accept(duel_id=did)
    res = s.resolve(
        duel_id=did, challenger_martial=95,
        challenger_leadership=80,
        target_martial=60, target_leadership=50,
        seed=1, now_day=11,
    )
    assert res.outcome == DuelOutcome.CHALLENGER_WINS
    assert res.winner == "off_volker"


def test_resolve_target_wins():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    s.accept(duel_id=did)
    res = s.resolve(
        duel_id=did, challenger_martial=50,
        challenger_leadership=50,
        target_martial=95, target_leadership=85,
        seed=1, now_day=11,
    )
    assert res.outcome == DuelOutcome.TARGET_WINS


def test_resolve_draw_close_scores():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    s.accept(duel_id=did)
    res = s.resolve(
        duel_id=did, challenger_martial=70,
        challenger_leadership=60,
        target_martial=70, target_leadership=60,
        seed=0, now_day=11,
    )
    assert res.outcome == DuelOutcome.DRAW


def test_resolve_head_stake_can_kill():
    s = NationOfficerDuelSystem()
    did = _propose(
        s, stake=Stake.HEAD, purse_gil=0,
    )
    s.accept(duel_id=did)
    res = s.resolve(
        duel_id=did, challenger_martial=99,
        challenger_leadership=99,
        target_martial=20, target_leadership=20,
        seed=1, now_day=11,
    )
    assert res.death is True


def test_resolve_honor_no_death():
    s = NationOfficerDuelSystem()
    did = _propose(s, stake=Stake.HONOR_ONLY)
    s.accept(duel_id=did)
    res = s.resolve(
        duel_id=did, challenger_martial=99,
        challenger_leadership=99,
        target_martial=20, target_leadership=20,
        seed=1, now_day=11,
    )
    assert res.death is False


def test_resolve_unknown():
    s = NationOfficerDuelSystem()
    res = s.resolve(
        duel_id="ghost", challenger_martial=50,
        challenger_leadership=50,
        target_martial=50, target_leadership=50,
        seed=0, now_day=11,
    )
    assert res is None


def test_resolve_when_proposed_blocked():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    res = s.resolve(
        duel_id=did, challenger_martial=50,
        challenger_leadership=50,
        target_martial=50, target_leadership=50,
        seed=0, now_day=11,
    )
    assert res is None


def test_resolve_invalid_stat():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    s.accept(duel_id=did)
    res = s.resolve(
        duel_id=did, challenger_martial=200,
        challenger_leadership=50,
        target_martial=50, target_leadership=50,
        seed=0, now_day=11,
    )
    assert res is None


def test_double_resolve_blocked():
    s = NationOfficerDuelSystem()
    did = _propose(s)
    s.accept(duel_id=did)
    s.resolve(
        duel_id=did, challenger_martial=80,
        challenger_leadership=70,
        target_martial=60, target_leadership=50,
        seed=0, now_day=11,
    )
    res = s.resolve(
        duel_id=did, challenger_martial=80,
        challenger_leadership=70,
        target_martial=60, target_leadership=50,
        seed=0, now_day=12,
    )
    assert res is None


def test_resolve_deterministic_same_seed():
    s = NationOfficerDuelSystem()
    did1 = _propose(s)
    s.accept(duel_id=did1)
    r1 = s.resolve(
        duel_id=did1, challenger_martial=80,
        challenger_leadership=70,
        target_martial=80, target_leadership=70,
        seed=42, now_day=11,
    )
    s2 = NationOfficerDuelSystem()
    did2 = _propose(s2)
    s2.accept(duel_id=did2)
    r2 = s2.resolve(
        duel_id=did2, challenger_martial=80,
        challenger_leadership=70,
        target_martial=80, target_leadership=70,
        seed=42, now_day=11,
    )
    assert r1.challenger_score == r2.challenger_score
    assert r1.target_score == r2.target_score


def test_duels_for_officer():
    s = NationOfficerDuelSystem()
    _propose(s, challenger="a", target="b")
    _propose(s, challenger="c", target="a")
    _propose(s, challenger="b", target="c")
    out = s.duels_for(officer_id="a")
    assert len(out) == 2


def test_duel_unknown():
    s = NationOfficerDuelSystem()
    assert s.duel(duel_id="ghost") is None


def test_enum_counts():
    assert len(list(Stake)) == 4
    assert len(list(DuelState)) == 5
    assert len(list(DuelOutcome)) == 4
