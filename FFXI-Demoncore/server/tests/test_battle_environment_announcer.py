"""Tests for battle_environment_announcer."""
from __future__ import annotations

from server.arena_environment import FeatureKind
from server.battle_environment_announcer import (
    AnnouncementKind,
    BattleEnvironmentAnnouncer,
    DEBOUNCE_SECONDS,
    Severity,
)
from server.habitat_disturbance import HabitatBiome


def test_on_break_floor_raid_banner():
    a = BattleEnvironmentAnnouncer()
    out = a.on_break(
        arena_id="a1", feature_id="floor_main",
        feature_kind=FeatureKind.FLOOR, now_seconds=10,
    )
    assert out is not None
    assert out.severity == Severity.RAID_BANNER
    assert out.kind == AnnouncementKind.BREAK_EVENT


def test_on_break_pillar_shout():
    a = BattleEnvironmentAnnouncer()
    out = a.on_break(
        arena_id="a1", feature_id="east_pillar",
        feature_kind=FeatureKind.PILLAR, now_seconds=10,
    )
    assert out.severity == Severity.SHOUT


def test_on_crack_say():
    a = BattleEnvironmentAnnouncer()
    out = a.on_crack(
        arena_id="a1", feature_id="ice",
        feature_kind=FeatureKind.ICE_SHEET, now_seconds=10,
    )
    assert out.severity == Severity.SAY


def test_break_debounce():
    a = BattleEnvironmentAnnouncer()
    a.on_break(
        arena_id="a1", feature_id="ice",
        feature_kind=FeatureKind.ICE_SHEET, now_seconds=10,
    )
    blocked = a.on_break(
        arena_id="a1", feature_id="ice",
        feature_kind=FeatureKind.ICE_SHEET,
        now_seconds=10 + DEBOUNCE_SECONDS - 1,
    )
    assert blocked is None
    later = a.on_break(
        arena_id="a1", feature_id="ice",
        feature_kind=FeatureKind.ICE_SHEET,
        now_seconds=10 + DEBOUNCE_SECONDS + 1,
    )
    assert later is not None


def test_crack_debounce():
    a = BattleEnvironmentAnnouncer()
    a.on_crack(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.WALL, now_seconds=0,
    )
    out = a.on_crack(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.WALL, now_seconds=2,
    )
    assert out is None


def test_different_features_no_debounce_collision():
    a = BattleEnvironmentAnnouncer()
    a.on_crack(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.WALL, now_seconds=0,
    )
    out = a.on_crack(
        arena_id="a1", feature_id="y",
        feature_kind=FeatureKind.WALL, now_seconds=2,
    )
    assert out is not None


def test_habitat_swoop_count_threshold_appends():
    a = BattleEnvironmentAnnouncer()
    out_few = a.on_habitat_swoop(
        arena_id="a1", biome=HabitatBiome.UNDERSEA,
        count=2, now_seconds=10,
    )
    assert "(2)" not in out_few.voice_line
    out_many = a.on_habitat_swoop(
        arena_id="a1", biome=HabitatBiome.UNDERSEA,
        count=5, now_seconds=20,
    )
    assert "(5)" in out_many.voice_line


def test_cascade_announcement():
    a = BattleEnvironmentAnnouncer()
    out = a.on_cascade(
        arena_id="a1", source_feature_id="east_pillar",
        target_feature_id="ceiling", now_seconds=10,
    )
    assert out.kind == AnnouncementKind.CASCADE
    assert "east_pillar" in out.voice_line
    assert "ceiling" in out.voice_line


def test_recent_filters_by_since():
    a = BattleEnvironmentAnnouncer()
    a.on_break(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.WALL, now_seconds=10,
    )
    a.on_break(
        arena_id="a1", feature_id="y",
        feature_kind=FeatureKind.PILLAR, now_seconds=50,
    )
    out = a.recent(arena_id="a1", since_seconds=30)
    assert len(out) == 1
    assert "PILLAR" in out[0].voice_line


def test_break_event_logs_into_recent():
    a = BattleEnvironmentAnnouncer()
    a.on_break(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.DAM, now_seconds=10,
    )
    out = a.recent(arena_id="a1", since_seconds=0)
    assert len(out) == 1


def test_clear_arena_removes_log():
    a = BattleEnvironmentAnnouncer()
    a.on_break(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.WALL, now_seconds=10,
    )
    a.clear_arena(arena_id="a1")
    out = a.recent(arena_id="a1", since_seconds=0)
    assert out == ()


def test_unknown_arena_recent_empty():
    a = BattleEnvironmentAnnouncer()
    assert a.recent(arena_id="ghost", since_seconds=0) == ()


def test_break_voice_line_has_kind():
    a = BattleEnvironmentAnnouncer()
    out = a.on_break(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.DAM, now_seconds=10,
    )
    assert "DAM" in out.voice_line.upper()


def test_audio_cue_unique_per_kind():
    a = BattleEnvironmentAnnouncer()
    floor = a.on_break(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.FLOOR, now_seconds=10,
    )
    ice = a.on_break(
        arena_id="a1", feature_id="y",
        feature_kind=FeatureKind.ICE_SHEET, now_seconds=20,
    )
    assert floor.audio_cue != ice.audio_cue


def test_habitat_swoop_no_debounce():
    """Swoops always announce — no debounce."""
    a = BattleEnvironmentAnnouncer()
    a.on_habitat_swoop(
        arena_id="a1", biome=HabitatBiome.CAVE,
        count=3, now_seconds=10,
    )
    out = a.on_habitat_swoop(
        arena_id="a1", biome=HabitatBiome.CAVE,
        count=2, now_seconds=11,
    )
    assert out is not None


def test_break_after_crack_cleared_separate_keys():
    """CRACK_WARNING and BREAK_EVENT have separate debounce keys."""
    a = BattleEnvironmentAnnouncer()
    a.on_crack(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.WALL, now_seconds=0,
    )
    out = a.on_break(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.WALL, now_seconds=1,
    )
    assert out is not None
