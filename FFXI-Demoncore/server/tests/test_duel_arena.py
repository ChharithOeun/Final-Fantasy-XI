"""Tests for duel_arena."""
from __future__ import annotations

from server.duel_arena import (
    ArenaKind,
    ArenaState,
    DuelArenaRegistry,
)


def _setup_arena():
    r = DuelArenaRegistry()
    r.register_arena(
        arena_id="bastok_platform", kind=ArenaKind.NATION_PLATFORM,
        capacity=20, region_id="bastok_markets",
    )
    return r


def test_register_arena_happy():
    r = _setup_arena()
    assert r.get(arena_id="bastok_platform") is not None


def test_register_blank_id_blocked():
    r = DuelArenaRegistry()
    assert r.register_arena(
        arena_id="", kind=ArenaKind.OUTLAW_PIT,
        capacity=10, region_id="x",
    ) is False


def test_negative_capacity_blocked():
    r = DuelArenaRegistry()
    assert r.register_arena(
        arena_id="x", kind=ArenaKind.OUTLAW_PIT,
        capacity=-1, region_id="x",
    ) is False


def test_duplicate_arena_blocked():
    r = _setup_arena()
    again = r.register_arena(
        arena_id="bastok_platform",
        kind=ArenaKind.NATION_PLATFORM,
        capacity=10, region_id="x",
    )
    assert again is False


def test_assign_duel_happy():
    r = _setup_arena()
    ok = r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    assert ok is True
    a = r.get(arena_id="bastok_platform")
    assert a is not None
    assert a.state == ArenaState.ASSIGNED


def test_assign_to_busy_arena_blocked():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    out = r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_2", scheduled_at=200,
    )
    assert out is False


def test_assign_same_challenge_to_two_arenas_blocked():
    r = _setup_arena()
    r.register_arena(
        arena_id="other", kind=ArenaKind.NATION_PLATFORM,
        capacity=10, region_id="other",
    )
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    out = r.assign_duel(
        arena_id="other",
        challenge_id="duel_1", scheduled_at=200,
    )
    assert out is False


def test_seat_witness():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    ok = r.seat_witness(
        arena_id="bastok_platform", witness_id="alice",
    )
    assert ok is True
    a = r.get(arena_id="bastok_platform")
    assert a is not None
    assert "alice" in a.witnesses


def test_seat_witness_dedup():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    r.seat_witness(arena_id="bastok_platform", witness_id="alice")
    again = r.seat_witness(
        arena_id="bastok_platform", witness_id="alice",
    )
    assert again is False


def test_seat_witness_capacity_cap():
    r = DuelArenaRegistry()
    r.register_arena(
        arena_id="tiny", kind=ArenaKind.OUTLAW_PIT,
        capacity=2, region_id="bastok_mines",
    )
    r.assign_duel(
        arena_id="tiny", challenge_id="d", scheduled_at=10,
    )
    assert r.seat_witness(arena_id="tiny", witness_id="a") is True
    assert r.seat_witness(arena_id="tiny", witness_id="b") is True
    assert r.seat_witness(arena_id="tiny", witness_id="c") is False


def test_seat_witness_in_idle_arena_blocked():
    r = _setup_arena()
    out = r.seat_witness(
        arena_id="bastok_platform", witness_id="alice",
    )
    assert out is False


def test_start_match_happy():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    ok = r.start_match(
        arena_id="bastok_platform", started_at=110,
    )
    assert ok is True
    a = r.get(arena_id="bastok_platform")
    assert a is not None
    assert a.state == ArenaState.LIVE


def test_start_match_when_idle_blocked():
    r = _setup_arena()
    out = r.start_match(
        arena_id="bastok_platform", started_at=110,
    )
    assert out is False


def test_conclude_happy():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    r.start_match(arena_id="bastok_platform", started_at=110)
    ok = r.conclude_match(
        arena_id="bastok_platform",
        winner_id="alice", ended_at=200,
    )
    assert ok is True
    a = r.get(arena_id="bastok_platform")
    assert a is not None
    assert a.state == ArenaState.CONCLUDED
    assert a.winner_id == "alice"


def test_conclude_before_start_blocked():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    out = r.conclude_match(
        arena_id="bastok_platform",
        winner_id="alice", ended_at=200,
    )
    assert out is False


def test_reset_after_conclude():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    r.start_match(arena_id="bastok_platform", started_at=110)
    r.conclude_match(
        arena_id="bastok_platform",
        winner_id="alice", ended_at=200,
    )
    ok = r.reset_arena(arena_id="bastok_platform")
    assert ok is True
    a = r.get(arena_id="bastok_platform")
    assert a is not None
    assert a.state == ArenaState.IDLE
    assert a.current_challenge_id is None
    assert a.witnesses == ()


def test_reset_before_conclude_blocked():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    out = r.reset_arena(arena_id="bastok_platform")
    assert out is False


def test_arena_for_challenge():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    a = r.arena_for(challenge_id="duel_1")
    assert a is not None
    assert a.arena_id == "bastok_platform"


def test_arena_for_unknown_challenge():
    r = _setup_arena()
    assert r.arena_for(challenge_id="nope") is None


def test_available_arenas_filters_by_kind():
    r = _setup_arena()
    r.register_arena(
        arena_id="outlaw1", kind=ArenaKind.OUTLAW_PIT,
        capacity=10, region_id="bastok_mines",
    )
    r.register_arena(
        arena_id="outlaw2", kind=ArenaKind.OUTLAW_PIT,
        capacity=10, region_id="port_bastok",
    )
    pits = r.available_arenas(kind=ArenaKind.OUTLAW_PIT)
    assert pits == ("outlaw1", "outlaw2")


def test_available_excludes_busy():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    out = r.available_arenas(kind=ArenaKind.NATION_PLATFORM)
    assert "bastok_platform" not in out


def test_four_arena_kinds():
    assert len(list(ArenaKind)) == 4


def test_blank_winner_rejected():
    r = _setup_arena()
    r.assign_duel(
        arena_id="bastok_platform",
        challenge_id="duel_1", scheduled_at=100,
    )
    r.start_match(arena_id="bastok_platform", started_at=110)
    out = r.conclude_match(
        arena_id="bastok_platform",
        winner_id="", ended_at=200,
    )
    assert out is False
