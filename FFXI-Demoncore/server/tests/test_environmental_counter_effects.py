"""Tests for environmental_counter_effects."""
from __future__ import annotations

from server.environment_hazards import HazardKind
from server.environmental_counter_effects import (
    CounterId,
    EnvironmentalCounters,
    HAZARD_COUNTER_MAP,
)


def test_grant_counter_happy():
    e = EnvironmentalCounters()
    assert e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=80, expires_at=300,
    ) is True


def test_grant_blank_player_blocked():
    e = EnvironmentalCounters()
    assert e.grant_counter(
        player_id="", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=80, expires_at=300,
    ) is False


def test_grant_invalid_pct_blocked():
    e = EnvironmentalCounters()
    assert e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=0, expires_at=300,
    ) is False
    assert e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=101, expires_at=300,
    ) is False


def test_has_counter_true_when_active():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=80, expires_at=300,
    )
    assert e.has_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        now_seconds=100,
    ) is True


def test_has_counter_false_when_expired():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=80, expires_at=100,
    )
    assert e.has_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        now_seconds=200,
    ) is False


def test_mitigate_with_no_counter():
    e = EnvironmentalCounters()
    out = e.mitigate(
        player_id="alice", hazard=HazardKind.FLOOR_COLLAPSE,
        raw_value=800, now_seconds=10,
    )
    assert out.final_value == 800
    assert out.mitigated_amount == 0
    assert out.counters_used == ()


def test_mitigate_with_one_counter():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=75, expires_at=300,
    )
    out = e.mitigate(
        player_id="alice", hazard=HazardKind.FLOOR_COLLAPSE,
        raw_value=800, now_seconds=10,
    )
    assert out.mitigated_amount == 600
    assert out.final_value == 200
    assert out.counters_used == (CounterId.FEATHERFALL,)


def test_mitigate_stacks_counters():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.SHIELD_BLOCK,
        magnitude_pct=40, expires_at=300,
    )
    e.grant_counter(
        player_id="alice", counter_id=CounterId.STONESKIN,
        magnitude_pct=30, expires_at=300,
    )
    e.grant_counter(
        player_id="alice", counter_id=CounterId.STUN_RESIST,
        magnitude_pct=20, expires_at=300,
    )
    out = e.mitigate(
        player_id="alice", hazard=HazardKind.CEILING_CRUMBLE,
        raw_value=600, now_seconds=10,
    )
    # 40 + 30 + 20 = 90% mitigated
    assert out.mitigated_amount == 540
    assert out.final_value == 60
    assert len(out.counters_used) == 3


def test_mitigate_caps_at_100pct():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.SHIELD_BLOCK,
        magnitude_pct=80, expires_at=300,
    )
    e.grant_counter(
        player_id="alice", counter_id=CounterId.STONESKIN,
        magnitude_pct=80, expires_at=300,
    )
    out = e.mitigate(
        player_id="alice", hazard=HazardKind.CEILING_CRUMBLE,
        raw_value=600, now_seconds=10,
    )
    assert out.final_value == 0
    assert out.mitigated_amount == 600


def test_mitigate_ignores_wrong_hazard_counters():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=100, expires_at=300,
    )
    # featherfall doesn't help against ice break
    out = e.mitigate(
        player_id="alice", hazard=HazardKind.ICE_BREAK,
        raw_value=500, now_seconds=10,
    )
    assert out.final_value == 500
    assert out.counters_used == ()


def test_expired_counters_dont_apply():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=100, expires_at=100,
    )
    out = e.mitigate(
        player_id="alice", hazard=HazardKind.FLOOR_COLLAPSE,
        raw_value=800, now_seconds=200,
    )
    assert out.final_value == 800


def test_clear_expired_removes_grants():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=50, expires_at=100,
    )
    e.grant_counter(
        player_id="alice", counter_id=CounterId.STONESKIN,
        magnitude_pct=50, expires_at=300,
    )
    cleared = e.clear_expired(now_seconds=200)
    assert cleared == 1
    active = e.active_counter_ids(player_id="alice", now_seconds=200)
    assert active == (CounterId.STONESKIN,)


def test_better_grant_replaces_weaker():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=50, expires_at=100,
    )
    ok = e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=80, expires_at=300,
    )
    assert ok is True


def test_weaker_grant_doesnt_replace_better():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=80, expires_at=300,
    )
    ok = e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=50, expires_at=100,
    )
    assert ok is False


def test_zero_raw_value_short_circuit():
    e = EnvironmentalCounters()
    out = e.mitigate(
        player_id="alice", hazard=HazardKind.FLOOR_COLLAPSE,
        raw_value=0, now_seconds=10,
    )
    assert out.final_value == 0
    assert out.counters_used == ()


def test_hazard_counter_map_complete():
    """Every HazardKind has at least one counter mapped."""
    for h in HazardKind:
        assert h in HAZARD_COUNTER_MAP


def test_active_counter_ids_only_returns_unexpired():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.FEATHERFALL,
        magnitude_pct=50, expires_at=100,
    )
    e.grant_counter(
        player_id="alice", counter_id=CounterId.STONESKIN,
        magnitude_pct=50, expires_at=300,
    )
    out = e.active_counter_ids(player_id="alice", now_seconds=200)
    assert out == (CounterId.STONESKIN,)


def test_widescan_preflag_counts_as_wall_breach_counter():
    e = EnvironmentalCounters()
    e.grant_counter(
        player_id="alice", counter_id=CounterId.WIDESCAN_PRE_FLAGGED,
        magnitude_pct=50, expires_at=300,
    )
    out = e.mitigate(
        player_id="alice", hazard=HazardKind.WALL_BREACH,
        raw_value=100, now_seconds=10,
    )
    assert out.mitigated_amount == 50
    assert CounterId.WIDESCAN_PRE_FLAGGED in out.counters_used
