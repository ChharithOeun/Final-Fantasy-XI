"""Tests for mob_buff_watcher."""
from __future__ import annotations

from server.mob_buff_watcher import (
    BuffPattern, MobBuffWatcher,
)


def _has_stoneskin(snap):
    return "stoneskin" in snap.buff_ids


def _has_manafont(snap):
    return "manafont" in snap.buff_ids


def _exploding_predicate(snap):
    raise RuntimeError("oops")


def test_observe_happy():
    w = MobBuffWatcher()
    ok = w.observe(
        player_id="alice", buff_ids=["stoneskin"], ts=10,
    )
    assert ok is True
    snap = w.snapshot(player_id="alice")
    assert snap.buff_ids == ("stoneskin",)


def test_observe_blank_player_blocked():
    w = MobBuffWatcher()
    out = w.observe(player_id="", buff_ids=[], ts=10)
    assert out is False


def test_snapshot_unknown_returns_none():
    w = MobBuffWatcher()
    assert w.snapshot(player_id="ghost") is None


def test_observe_overwrites():
    w = MobBuffWatcher()
    w.observe(player_id="alice", buff_ids=["stoneskin"], ts=10)
    w.observe(player_id="alice", buff_ids=["protect"], ts=20)
    snap = w.snapshot(player_id="alice")
    assert snap.buff_ids == ("protect",)


def test_register_pattern_happy():
    w = MobBuffWatcher()
    p = BuffPattern(
        pattern_id="dispel_stoneskin",
        predicate=_has_stoneskin,
        action_id="cast_dispel",
    )
    ok = w.register_pattern(mob_id="boss_a", pattern=p)
    assert ok is True


def test_register_pattern_blank_mob_blocked():
    w = MobBuffWatcher()
    p = BuffPattern(
        pattern_id="x", predicate=_has_stoneskin,
        action_id="y",
    )
    out = w.register_pattern(mob_id="", pattern=p)
    assert out is False


def test_register_pattern_blank_pattern_id_blocked():
    w = MobBuffWatcher()
    p = BuffPattern(
        pattern_id="", predicate=_has_stoneskin,
        action_id="y",
    )
    out = w.register_pattern(mob_id="boss", pattern=p)
    assert out is False


def test_register_pattern_blank_action_blocked():
    w = MobBuffWatcher()
    p = BuffPattern(
        pattern_id="x", predicate=_has_stoneskin,
        action_id="",
    )
    out = w.register_pattern(mob_id="boss", pattern=p)
    assert out is False


def test_register_pattern_duplicate_blocked():
    w = MobBuffWatcher()
    p1 = BuffPattern(
        pattern_id="x", predicate=_has_stoneskin,
        action_id="y",
    )
    p2 = BuffPattern(
        pattern_id="x", predicate=_has_manafont,
        action_id="z",
    )
    w.register_pattern(mob_id="boss", pattern=p1)
    out = w.register_pattern(mob_id="boss", pattern=p2)
    assert out is False


def test_check_patterns_match():
    w = MobBuffWatcher()
    w.observe(
        player_id="alice", buff_ids=["stoneskin"], ts=10,
    )
    w.register_pattern(
        mob_id="boss", pattern=BuffPattern(
            pattern_id="dispel_ss",
            predicate=_has_stoneskin,
            action_id="cast_dispel",
        ),
    )
    out = w.check_patterns(mob_id="boss", player_id="alice")
    assert out == ["cast_dispel"]


def test_check_patterns_no_match():
    w = MobBuffWatcher()
    w.observe(player_id="alice", buff_ids=["protect"], ts=10)
    w.register_pattern(
        mob_id="boss", pattern=BuffPattern(
            pattern_id="dispel_ss",
            predicate=_has_stoneskin,
            action_id="cast_dispel",
        ),
    )
    out = w.check_patterns(mob_id="boss", player_id="alice")
    assert out == []


def test_check_patterns_no_snapshot():
    w = MobBuffWatcher()
    w.register_pattern(
        mob_id="boss", pattern=BuffPattern(
            pattern_id="dispel_ss",
            predicate=_has_stoneskin,
            action_id="cast_dispel",
        ),
    )
    out = w.check_patterns(mob_id="boss", player_id="ghost")
    assert out == []


def test_check_patterns_no_patterns():
    w = MobBuffWatcher()
    w.observe(player_id="alice", buff_ids=["stoneskin"], ts=10)
    out = w.check_patterns(mob_id="boss", player_id="alice")
    assert out == []


def test_check_patterns_multiple_match():
    w = MobBuffWatcher()
    w.observe(
        player_id="alice",
        buff_ids=["stoneskin", "manafont"], ts=10,
    )
    w.register_pattern(
        mob_id="boss", pattern=BuffPattern(
            pattern_id="dispel_ss",
            predicate=_has_stoneskin, action_id="cast_dispel",
        ),
    )
    w.register_pattern(
        mob_id="boss", pattern=BuffPattern(
            pattern_id="counter_mf",
            predicate=_has_manafont, action_id="cast_silence",
        ),
    )
    out = w.check_patterns(mob_id="boss", player_id="alice")
    assert set(out) == {"cast_dispel", "cast_silence"}


def test_predicate_exception_does_not_propagate():
    w = MobBuffWatcher()
    w.observe(player_id="alice", buff_ids=["stoneskin"], ts=10)
    w.register_pattern(
        mob_id="boss", pattern=BuffPattern(
            pattern_id="bad",
            predicate=_exploding_predicate,
            action_id="cast_dispel",
        ),
    )
    # second pattern should still match
    w.register_pattern(
        mob_id="boss", pattern=BuffPattern(
            pattern_id="ok",
            predicate=_has_stoneskin,
            action_id="cast_silence",
        ),
    )
    out = w.check_patterns(mob_id="boss", player_id="alice")
    # the bad one is skipped, the good one matches
    assert out == ["cast_silence"]


def test_clear_snapshot():
    w = MobBuffWatcher()
    w.observe(player_id="alice", buff_ids=["x"], ts=10)
    out = w.clear_snapshot(player_id="alice")
    assert out is True
    assert w.snapshot(player_id="alice") is None


def test_clear_snapshot_unknown():
    w = MobBuffWatcher()
    out = w.clear_snapshot(player_id="ghost")
    assert out is False


def test_total_observed():
    w = MobBuffWatcher()
    w.observe(player_id="alice", buff_ids=[], ts=10)
    w.observe(player_id="bob", buff_ids=[], ts=10)
    assert w.total_observed() == 2


def test_per_mob_patterns_independent():
    w = MobBuffWatcher()
    w.observe(player_id="alice", buff_ids=["stoneskin"], ts=10)
    w.register_pattern(
        mob_id="boss_a", pattern=BuffPattern(
            pattern_id="x", predicate=_has_stoneskin,
            action_id="dispel",
        ),
    )
    # boss_b has no patterns
    out = w.check_patterns(mob_id="boss_b", player_id="alice")
    assert out == []


def test_snapshot_carries_timestamp():
    w = MobBuffWatcher()
    w.observe(player_id="alice", buff_ids=["x"], ts=42)
    snap = w.snapshot(player_id="alice")
    assert snap.observed_at == 42
