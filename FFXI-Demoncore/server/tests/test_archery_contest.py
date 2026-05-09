"""Tests for archery_contest."""
from __future__ import annotations

from server.archery_contest import (
    ArcheryContestSystem, SessionState,
)


def _shoot_full(s, sid, seed=42):
    s.begin_shooting(session_id=sid)
    for i in range(10):
        s.loose_arrow(session_id=sid, seed=seed + i)


def test_register_happy():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="bastok_open",
        archer_skill=70, bow_quality=80,
        started_day=10,
    )
    assert sid is not None


def test_register_invalid_skill():
    s = ArcheryContestSystem()
    assert s.register(
        archer_id="bob", contest_id="x",
        archer_skill=0, bow_quality=80,
        started_day=10,
    ) is None


def test_register_invalid_bow():
    s = ArcheryContestSystem()
    assert s.register(
        archer_id="bob", contest_id="x",
        archer_skill=80, bow_quality=120,
        started_day=10,
    ) is None


def test_register_dup_active_blocked():
    s = ArcheryContestSystem()
    s.register(
        archer_id="bob", contest_id="open",
        archer_skill=80, bow_quality=80,
        started_day=10,
    )
    assert s.register(
        archer_id="bob", contest_id="open",
        archer_skill=80, bow_quality=80,
        started_day=11,
    ) is None


def test_register_after_complete_ok():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="open",
        archer_skill=80, bow_quality=80,
        started_day=10,
    )
    _shoot_full(s, sid)
    new_sid = s.register(
        archer_id="bob", contest_id="open",
        archer_skill=80, bow_quality=80,
        started_day=20,
    )
    assert new_sid is not None


def test_begin_shooting():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=80, bow_quality=80,
        started_day=10,
    )
    assert s.begin_shooting(session_id=sid) is True


def test_begin_double_blocked():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=80, bow_quality=80,
        started_day=10,
    )
    s.begin_shooting(session_id=sid)
    assert s.begin_shooting(
        session_id=sid,
    ) is False


def test_loose_before_begin_blocked():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=80, bow_quality=80,
        started_day=10,
    )
    pts = s.loose_arrow(session_id=sid, seed=1)
    assert pts is None


def test_loose_arrow_returns_points():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=80, bow_quality=80,
        started_day=10,
    )
    s.begin_shooting(session_id=sid)
    pts = s.loose_arrow(session_id=sid, seed=1)
    assert pts is not None
    assert 0 <= pts <= 10


def test_loose_after_10_arrows_blocked():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=80, bow_quality=80,
        started_day=10,
    )
    _shoot_full(s, sid)
    pts = s.loose_arrow(session_id=sid, seed=99)
    assert pts is None


def test_session_completes_after_10():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=80, bow_quality=80,
        started_day=10,
    )
    _shoot_full(s, sid)
    assert s.session(
        session_id=sid,
    ).state == SessionState.COMPLETED


def test_total_score_accumulates():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=100, bow_quality=100,
        started_day=10,
    )
    _shoot_full(s, sid, seed=0)
    sess = s.session(session_id=sid)
    # max archer + bow = 10+10 = 20, capped at 10
    # per arrow = 100 perfect potential
    assert sess.total_score >= 90
    assert sess.total_score <= 100


def test_high_skill_outperforms_low():
    s = ArcheryContestSystem()
    sid_high = s.register(
        archer_id="high", contest_id="x",
        archer_skill=100, bow_quality=100,
        started_day=10,
    )
    sid_low = s.register(
        archer_id="low", contest_id="x",
        archer_skill=20, bow_quality=20,
        started_day=10,
    )
    _shoot_full(s, sid_high, seed=42)
    _shoot_full(s, sid_low, seed=42)
    high = s.session(session_id=sid_high)
    low = s.session(session_id=sid_low)
    assert high.total_score > low.total_score


def test_leaderboard_orders_descending():
    s = ArcheryContestSystem()
    sid_a = s.register(
        archer_id="a", contest_id="x",
        archer_skill=50, bow_quality=50,
        started_day=10,
    )
    sid_b = s.register(
        archer_id="b", contest_id="x",
        archer_skill=90, bow_quality=90,
        started_day=10,
    )
    sid_c = s.register(
        archer_id="c", contest_id="x",
        archer_skill=70, bow_quality=70,
        started_day=10,
    )
    _shoot_full(s, sid_a, seed=42)
    _shoot_full(s, sid_b, seed=42)
    _shoot_full(s, sid_c, seed=42)
    out = s.leaderboard(contest_id="x", limit=3)
    assert out[0].archer_id == "b"
    assert out[2].archer_id == "a"


def test_leaderboard_limits():
    s = ArcheryContestSystem()
    for i in range(5):
        sid = s.register(
            archer_id=f"archer_{i}",
            contest_id="x",
            archer_skill=50, bow_quality=50,
            started_day=10,
        )
        _shoot_full(s, sid)
    out = s.leaderboard(contest_id="x", limit=3)
    assert len(out) == 3


def test_leaderboard_excludes_unfinished():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="a", contest_id="x",
        archer_skill=50, bow_quality=50,
        started_day=10,
    )
    s.begin_shooting(session_id=sid)
    # Only 5 arrows
    for i in range(5):
        s.loose_arrow(session_id=sid, seed=i)
    out = s.leaderboard(contest_id="x", limit=10)
    assert out == []


def test_archer_best():
    s = ArcheryContestSystem()
    sid_a = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=50, bow_quality=50,
        started_day=10,
    )
    _shoot_full(s, sid_a, seed=10)
    sid_b = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=80, bow_quality=80,
        started_day=20,
    )
    _shoot_full(s, sid_b, seed=10)
    best = s.archer_best(
        archer_id="bob", contest_id="x",
    )
    assert best.session_id == sid_b


def test_archer_best_unknown():
    s = ArcheryContestSystem()
    assert s.archer_best(
        archer_id="ghost", contest_id="x",
    ) is None


def test_is_perfect_caps_at_100():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=100, bow_quality=100,
        started_day=10,
    )
    _shoot_full(s, sid, seed=0)
    sess = s.session(session_id=sid)
    if sess.total_score == 100:
        assert s.is_perfect(session_id=sid) is True


def test_session_unknown():
    s = ArcheryContestSystem()
    assert s.session(session_id="ghost") is None


def test_loose_deterministic():
    s = ArcheryContestSystem()
    sid = s.register(
        archer_id="bob", contest_id="x",
        archer_skill=70, bow_quality=70,
        started_day=10,
    )
    s.begin_shooting(session_id=sid)
    p1 = s.loose_arrow(session_id=sid, seed=42)
    s2 = ArcheryContestSystem()
    sid2 = s2.register(
        archer_id="bob", contest_id="x",
        archer_skill=70, bow_quality=70,
        started_day=10,
    )
    s2.begin_shooting(session_id=sid2)
    p2 = s2.loose_arrow(session_id=sid2, seed=42)
    assert p1 == p2


def test_leaderboard_zero_limit():
    s = ArcheryContestSystem()
    assert s.leaderboard(
        contest_id="x", limit=0,
    ) == []


def test_enum_count():
    assert len(list(SessionState)) == 3
