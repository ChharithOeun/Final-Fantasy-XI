"""Tests for nation_governor."""
from __future__ import annotations

from server.nation_governor import (
    NationGovernorSystem, GovernorState,
)


def test_install_appointed():
    s = NationGovernorSystem()
    assert s.install_appointed(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    ) is not None


def test_install_elected():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    assert rid is not None


def test_install_blank_nation():
    s = NationGovernorSystem()
    assert s.install_appointed(
        nation_id="", governor_id="cid",
        term_days=365, now_day=10,
    ) is None


def test_install_zero_term():
    s = NationGovernorSystem()
    assert s.install_appointed(
        nation_id="bastok", governor_id="cid",
        term_days=0, now_day=10,
    ) is None


def test_install_dup_nation_blocked():
    s = NationGovernorSystem()
    s.install_appointed(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    assert s.install_appointed(
        nation_id="bastok", governor_id="someone",
        term_days=365, now_day=11,
    ) is None


def test_current_returns_seated():
    s = NationGovernorSystem()
    s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    cur = s.current(nation_id="bastok")
    assert cur is not None
    assert cur.governor_id == "cid"
    assert cur.state == GovernorState.ELECTED


def test_current_unknown():
    s = NationGovernorSystem()
    assert s.current(nation_id="ghost") is None


def test_suspend_happy():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    assert s.suspend(
        record_id=rid, now_day=20,
        reason="scandal",
    ) is True


def test_suspend_blank_reason():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    assert s.suspend(
        record_id=rid, now_day=20, reason="",
    ) is False


def test_restore_after_suspend():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    s.suspend(record_id=rid, now_day=20,
              reason="illness")
    assert s.restore(
        record_id=rid, now_day=30,
    ) is True
    assert s.current(
        nation_id="bastok",
    ).state == GovernorState.ELECTED


def test_restore_appointed_returns_to_appointed():
    s = NationGovernorSystem()
    rid = s.install_appointed(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    s.suspend(record_id=rid, now_day=20,
              reason="x")
    s.restore(record_id=rid, now_day=30)
    assert s.current(
        nation_id="bastok",
    ).state == GovernorState.APPOINTED


def test_restore_when_not_suspended_blocked():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    assert s.restore(
        record_id=rid, now_day=20,
    ) is False


def test_depose_happy():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    assert s.depose(
        record_id=rid, now_day=50,
        reason="treason",
    ) is True
    assert s.current(nation_id="bastok") is None


def test_depose_blank_reason():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    assert s.depose(
        record_id=rid, now_day=50, reason="",
    ) is False


def test_depose_then_install_new():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=365, now_day=10,
    )
    s.depose(record_id=rid, now_day=50,
             reason="treason")
    assert s.install_elected(
        nation_id="bastok", governor_id="naji",
        term_days=365, now_day=60,
    ) is not None


def test_tick_archives_at_term_end():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=10, now_day=0,
    )
    changes = s.tick(now_day=10)
    assert (rid, GovernorState.HISTORICAL) in changes
    assert s.current(nation_id="bastok") is None


def test_tick_skips_within_term():
    s = NationGovernorSystem()
    rid = s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=10, now_day=0,
    )
    s.tick(now_day=5)
    cur = s.current(nation_id="bastok")
    assert cur is not None
    assert cur.record_id == rid


def test_history_lists_all():
    s = NationGovernorSystem()
    rid_a = s.install_elected(
        nation_id="bastok", governor_id="a",
        term_days=10, now_day=0,
    )
    s.tick(now_day=10)
    rid_b = s.install_elected(
        nation_id="bastok", governor_id="b",
        term_days=10, now_day=10,
    )
    out = s.history(nation_id="bastok")
    ids = [r.record_id for r in out]
    assert rid_a in ids
    assert rid_b in ids


def test_term_remaining():
    s = NationGovernorSystem()
    s.install_elected(
        nation_id="bastok", governor_id="cid",
        term_days=10, now_day=0,
    )
    assert s.term_remaining(
        nation_id="bastok", now_day=3,
    ) == 7


def test_term_remaining_no_governor():
    s = NationGovernorSystem()
    assert s.term_remaining(
        nation_id="bastok", now_day=10,
    ) == 0


def test_enum_count():
    assert len(list(GovernorState)) == 5
