"""Tests for lifetime dive log."""
from __future__ import annotations

from server.lifetime_dive_log import LifetimeDiveLog


def test_record_dive_updates_deepest():
    log = LifetimeDiveLog()
    log.record_dive(
        player_id="p1", depth_m=300, duration_seconds=60,
    )
    s = log.stats_for(player_id="p1")
    assert s.deepest_dive_meters == 300


def test_record_dive_keeps_max_depth():
    log = LifetimeDiveLog()
    log.record_dive(
        player_id="p1", depth_m=300, duration_seconds=60,
    )
    log.record_dive(
        player_id="p1", depth_m=200, duration_seconds=60,
    )
    s = log.stats_for(player_id="p1")
    assert s.deepest_dive_meters == 300


def test_record_dive_updates_session_max():
    log = LifetimeDiveLog()
    log.record_dive(
        player_id="p1", depth_m=100, duration_seconds=120,
    )
    log.record_dive(
        player_id="p1", depth_m=100, duration_seconds=600,
    )
    s = log.stats_for(player_id="p1")
    assert s.longest_session_seconds == 600


def test_record_dive_blank_player():
    log = LifetimeDiveLog()
    assert log.record_dive(
        player_id="", depth_m=100, duration_seconds=60,
    ) is False


def test_pact_streak_increments():
    log = LifetimeDiveLog()
    log.record_dive(
        player_id="p1", depth_m=100, duration_seconds=60,
        pact_active=True,
    )
    log.record_dive(
        player_id="p1", depth_m=100, duration_seconds=60,
        pact_active=True,
    )
    log.record_dive(
        player_id="p1", depth_m=100, duration_seconds=60,
        pact_active=True,
    )
    assert log.stats_for(player_id="p1").longest_drowned_pact == 3


def test_pact_streak_resets_on_break():
    log = LifetimeDiveLog()
    for _ in range(3):
        log.record_dive(
            player_id="p1", depth_m=100, duration_seconds=60,
            pact_active=True,
        )
    log.record_dive(
        player_id="p1", depth_m=100, duration_seconds=60,
        pact_active=False,
    )
    log.record_dive(
        player_id="p1", depth_m=100, duration_seconds=60,
        pact_active=True,
    )
    s = log.stats_for(player_id="p1")
    # max was 3 before the break; after break + 1 = streak 1
    assert s.longest_drowned_pact == 3


def test_record_kraken_kill():
    log = LifetimeDiveLog()
    log.record_kraken_kill(player_id="p1")
    log.record_kraken_kill(player_id="p1")
    assert log.stats_for(player_id="p1").total_kraken_kills == 2


def test_record_wreck_salvaged():
    log = LifetimeDiveLog()
    log.record_wreck_salvaged(player_id="p1")
    assert log.stats_for(player_id="p1").total_wrecks_salvaged == 1


def test_record_landmark_found():
    log = LifetimeDiveLog()
    log.record_landmark_found(player_id="p1")
    log.record_landmark_found(player_id="p1")
    log.record_landmark_found(player_id="p1")
    assert log.stats_for(player_id="p1").total_landmarks_found == 3


def test_stats_for_unknown_returns_zeros():
    log = LifetimeDiveLog()
    s = log.stats_for(player_id="ghost")
    assert s.deepest_dive_meters == 0.0
    assert s.total_kraken_kills == 0


def test_leaderboard_sorts_desc():
    log = LifetimeDiveLog()
    log.record_dive(
        player_id="p1", depth_m=100, duration_seconds=10,
    )
    log.record_dive(
        player_id="p2", depth_m=500, duration_seconds=10,
    )
    log.record_dive(
        player_id="p3", depth_m=300, duration_seconds=10,
    )
    out = log.leaderboard(stat="deepest_dive_meters")
    assert out[0][0] == "p2"
    assert out[1][0] == "p3"
    assert out[2][0] == "p1"


def test_leaderboard_unknown_stat():
    log = LifetimeDiveLog()
    assert log.leaderboard(stat="bogus") == ()


def test_leaderboard_top_n():
    log = LifetimeDiveLog()
    for i in range(5):
        log.record_kraken_kill(player_id=f"p{i}")
        if i % 2 == 0:
            log.record_kraken_kill(player_id=f"p{i}")
    out = log.leaderboard(stat="total_kraken_kills", top_n=3)
    assert len(out) == 3


def test_leaderboard_stable_tiebreak_by_player_id():
    log = LifetimeDiveLog()
    log.record_kraken_kill(player_id="zeta")
    log.record_kraken_kill(player_id="alpha")
    out = log.leaderboard(stat="total_kraken_kills")
    # both have 1 kill — alpha comes first by id
    assert out[0][0] == "alpha"
    assert out[1][0] == "zeta"


def test_leaderboard_skips_zero_values():
    log = LifetimeDiveLog()
    log.record_kraken_kill(player_id="killer")
    log.record_dive(
        player_id="diver", depth_m=100, duration_seconds=10,
    )
    out = log.leaderboard(stat="total_kraken_kills")
    # diver has 0 kraken kills, shouldn't appear
    assert all(p[0] != "diver" for p in out)
