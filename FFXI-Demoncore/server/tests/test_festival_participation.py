"""Tests for festival participation."""
from __future__ import annotations

from server.festival_participation import (
    BadgeTier,
    EventKind,
    FestivalKind,
    FestivalParticipation,
    FestivalStatus,
)


def test_open_festival():
    f = FestivalParticipation()
    fest = f.open_festival(
        festival_id="vana_2026",
        kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=1000.0,
    )
    assert fest is not None
    assert fest.status == FestivalStatus.OPEN


def test_open_invalid_window_rejected():
    f = FestivalParticipation()
    assert f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=1000.0,
        closes_at_seconds=1000.0,
    ) is None


def test_double_open_rejected():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    assert f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    ) is None


def test_close_festival():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    assert f.close_festival(festival_id="x")
    assert not f.close_festival(festival_id="x")


def test_close_unknown():
    f = FestivalParticipation()
    assert not f.close_festival(festival_id="ghost")


def test_record_succeeds():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    assert f.record(
        player_id="alice", festival_id="x",
        kind=EventKind.TASK_COMPLETED,
        points=10, at_seconds=10.0,
    )


def test_record_outside_window_rejected():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    assert not f.record(
        player_id="alice", festival_id="x",
        kind=EventKind.TASK_COMPLETED,
        points=10, at_seconds=200.0,
    )


def test_record_zero_points_rejected():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    assert not f.record(
        player_id="alice", festival_id="x",
        kind=EventKind.ENTERED, points=0,
        at_seconds=10.0,
    )


def test_record_unknown_festival():
    f = FestivalParticipation()
    assert not f.record(
        player_id="alice", festival_id="ghost",
        kind=EventKind.ENTERED, points=1,
    )


def test_record_after_close_rejected():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    f.close_festival(festival_id="x")
    assert not f.record(
        player_id="alice", festival_id="x",
        kind=EventKind.ENTERED, points=1,
        at_seconds=10.0,
    )


def test_standing_no_participation():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    s = f.standing(
        player_id="alice", festival_id="x",
    )
    assert s.points == 0
    assert s.badge == BadgeTier.NONE
    assert s.rank == 0


def test_standing_with_points():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    f.record(
        player_id="alice", festival_id="x",
        kind=EventKind.TASK_COMPLETED,
        points=300, at_seconds=10.0,
    )
    s = f.standing(
        player_id="alice", festival_id="x",
    )
    assert s.points == 300
    assert s.badge == BadgeTier.SILVER
    assert s.rank == 1


def test_standing_unknown_festival():
    f = FestivalParticipation()
    s = f.standing(
        player_id="alice", festival_id="ghost",
    )
    assert s.points == 0


def test_leaderboard_sorts_by_points():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    f.record(
        player_id="alice", festival_id="x",
        kind=EventKind.TASK_COMPLETED,
        points=100, at_seconds=10.0,
    )
    f.record(
        player_id="bob", festival_id="x",
        kind=EventKind.TASK_COMPLETED,
        points=500, at_seconds=10.0,
    )
    leaderboard = f.leaderboard(festival_id="x")
    assert leaderboard[0].player_id == "bob"
    assert leaderboard[1].player_id == "alice"


def test_leaderboard_top_n_cap():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    for i in range(10):
        f.record(
            player_id=f"p{i}", festival_id="x",
            kind=EventKind.TOKEN_COLLECTED,
            points=100 + i, at_seconds=10.0,
        )
    leaderboard = f.leaderboard(
        festival_id="x", top_n=3,
    )
    assert len(leaderboard) == 3


def test_badges_unlock_progressively():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    f.record(
        player_id="alice", festival_id="x",
        kind=EventKind.MINI_GAME_WIN,
        points=700, at_seconds=10.0,
    )
    badges = f.badges_for(
        player_id="alice", festival_id="x",
    )
    assert BadgeTier.BRONZE in badges
    assert BadgeTier.SILVER in badges
    assert BadgeTier.GOLD in badges
    assert BadgeTier.PLATINUM not in badges


def test_badges_legendary_at_5000():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    f.record(
        player_id="alice", festival_id="x",
        kind=EventKind.MINI_GAME_WIN,
        points=5000, at_seconds=10.0,
    )
    s = f.standing(
        player_id="alice", festival_id="x",
    )
    assert s.badge == BadgeTier.LEGENDARY


def test_badges_no_participation_empty():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    assert f.badges_for(
        player_id="alice", festival_id="x",
    ) == ()


def test_total_festivals():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="a", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    f.open_festival(
        festival_id="b", kind=FestivalKind.STARLIGHT,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    assert f.total_festivals() == 2


def test_record_accumulates_points():
    f = FestivalParticipation()
    f.open_festival(
        festival_id="x", kind=FestivalKind.VANAFETE,
        opens_at_seconds=0.0,
        closes_at_seconds=100.0,
    )
    for _ in range(3):
        f.record(
            player_id="alice", festival_id="x",
            kind=EventKind.TOKEN_COLLECTED,
            points=20, at_seconds=10.0,
        )
    s = f.standing(
        player_id="alice", festival_id="x",
    )
    assert s.points == 60
