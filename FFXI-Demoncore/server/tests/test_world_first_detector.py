"""Tests for world_first_detector."""
from __future__ import annotations

from server.server_history_log import EventKind
from server.world_first_detector import WorldFirstDetector


def test_first_kill_is_world_first():
    d = WorldFirstDetector()
    out = d.observe_kill(
        boss_id="vorrak",
        party_member_ids=["alice", "bob"],
        kill_duration_seconds=600, killed_at=100,
    )
    assert out.kind == EventKind.WORLD_FIRST_KILL
    assert "vorrak" in out.summary
    assert out.participants == ("alice", "bob")
    assert out.value == 600


def test_second_kill_is_second():
    d = WorldFirstDetector()
    d.observe_kill(
        boss_id="vorrak", party_member_ids=["alice"],
        kill_duration_seconds=600, killed_at=100,
    )
    out = d.observe_kill(
        boss_id="vorrak", party_member_ids=["bob"],
        kill_duration_seconds=500, killed_at=200,
    )
    assert out.kind == EventKind.SECOND_KILL


def test_third_kill_better_time_is_speed_record():
    d = WorldFirstDetector()
    d.observe_kill(
        boss_id="v", party_member_ids=["a"],
        kill_duration_seconds=600, killed_at=10,
    )
    d.observe_kill(
        boss_id="v", party_member_ids=["b"],
        kill_duration_seconds=500, killed_at=20,
    )
    out = d.observe_kill(
        boss_id="v", party_member_ids=["c"],
        kill_duration_seconds=400, killed_at=30,
    )
    assert out.kind == EventKind.SPEED_RECORD
    assert out.value == 400


def test_third_kill_slower_no_event():
    d = WorldFirstDetector()
    d.observe_kill(
        boss_id="v", party_member_ids=["a"],
        kill_duration_seconds=300, killed_at=10,
    )
    d.observe_kill(
        boss_id="v", party_member_ids=["b"],
        kill_duration_seconds=400, killed_at=20,
    )
    out = d.observe_kill(
        boss_id="v", party_member_ids=["c"],
        kill_duration_seconds=600, killed_at=30,
    )
    assert out.kind is None


def test_blank_boss_returns_empty():
    d = WorldFirstDetector()
    out = d.observe_kill(
        boss_id="", party_member_ids=["a"],
        kill_duration_seconds=100, killed_at=10,
    )
    assert out.kind is None


def test_blank_party_returns_empty():
    d = WorldFirstDetector()
    out = d.observe_kill(
        boss_id="v", party_member_ids=[],
        kill_duration_seconds=100, killed_at=10,
    )
    assert out.kind is None


def test_best_time_tracks_minimum():
    d = WorldFirstDetector()
    d.observe_kill(
        boss_id="v", party_member_ids=["a"],
        kill_duration_seconds=600, killed_at=10,
    )
    d.observe_kill(
        boss_id="v", party_member_ids=["b"],
        kill_duration_seconds=500, killed_at=20,
    )
    d.observe_kill(
        boss_id="v", party_member_ids=["c"],
        kill_duration_seconds=400, killed_at=30,
    )
    d.observe_kill(
        boss_id="v", party_member_ids=["d"],
        kill_duration_seconds=700, killed_at=40,
    )
    assert d.best_time_for(boss_id="v") == 400


def test_kills_counter():
    d = WorldFirstDetector()
    for i in range(5):
        d.observe_kill(
            boss_id="v", party_member_ids=["a"],
            kill_duration_seconds=600, killed_at=i*10,
        )
    assert d.kills_for(boss_id="v") == 5


def test_total_known_bosses():
    d = WorldFirstDetector()
    d.observe_kill(
        boss_id="v", party_member_ids=["a"],
        kill_duration_seconds=100, killed_at=1,
    )
    d.observe_kill(
        boss_id="m", party_member_ids=["b"],
        kill_duration_seconds=200, killed_at=2,
    )
    assert d.total_known_bosses() == 2


def test_unknown_boss_best_time_none():
    d = WorldFirstDetector()
    assert d.best_time_for(boss_id="ghost") is None
    assert d.kills_for(boss_id="ghost") == 0


def test_blank_participants_filtered():
    d = WorldFirstDetector()
    out = d.observe_kill(
        boss_id="v",
        party_member_ids=["alice", "", "bob"],
        kill_duration_seconds=100, killed_at=10,
    )
    assert out.participants == ("alice", "bob")


def test_second_kill_better_time_updates_best():
    d = WorldFirstDetector()
    d.observe_kill(
        boss_id="v", party_member_ids=["a"],
        kill_duration_seconds=600, killed_at=10,
    )
    d.observe_kill(
        boss_id="v", party_member_ids=["b"],
        kill_duration_seconds=300, killed_at=20,
    )
    assert d.best_time_for(boss_id="v") == 300


def test_per_boss_isolation():
    d = WorldFirstDetector()
    d.observe_kill(
        boss_id="v", party_member_ids=["a"],
        kill_duration_seconds=100, killed_at=10,
    )
    out = d.observe_kill(
        boss_id="m", party_member_ids=["b"],
        kill_duration_seconds=200, killed_at=20,
    )
    # m's first kill is its own world-first
    assert out.kind == EventKind.WORLD_FIRST_KILL


def test_recorded_at_passes_through():
    d = WorldFirstDetector()
    out = d.observe_kill(
        boss_id="v", party_member_ids=["a"],
        kill_duration_seconds=100, killed_at=12345,
    )
    assert out.recorded_at == 12345


def test_summary_includes_boss_id():
    d = WorldFirstDetector()
    out = d.observe_kill(
        boss_id="mirahna", party_member_ids=["a"],
        kill_duration_seconds=100, killed_at=1,
    )
    assert "mirahna" in out.summary
