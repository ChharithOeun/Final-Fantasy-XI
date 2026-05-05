"""Tests for seafloor landmarks."""
from __future__ import annotations

from server.seafloor_landmarks import (
    DISCOVERY_RADIUS,
    LandmarkKind,
    SeafloorLandmarks,
)


def test_register_happy():
    s = SeafloorLandmarks()
    ok = s.register(
        landmark_id="lm1", name="Sunken Frigate",
        kind=LandmarkKind.WRECK,
        x=100, y=200, band=3, lore_blurb="lost in 859 AC",
    )
    assert ok is True


def test_register_blank_name():
    s = SeafloorLandmarks()
    ok = s.register(
        landmark_id="lm1", name="",
        kind=LandmarkKind.WRECK,
        x=0, y=0, band=2,
    )
    assert ok is False


def test_discover_within_radius():
    s = SeafloorLandmarks()
    s.register(
        landmark_id="lm1", name="Vent",
        kind=LandmarkKind.HYDROTHERMAL_VENT,
        x=0, y=0, band=3,
    )
    new = s.check_discovery(
        player_id="p1", x=10, y=10, band=3, now_seconds=100,
    )
    assert len(new) == 1
    assert new[0].landmark_id == "lm1"
    assert s.is_discovered(player_id="p1", landmark_id="lm1")


def test_no_discovery_wrong_band():
    s = SeafloorLandmarks()
    s.register(
        landmark_id="lm1", name="Vent",
        kind=LandmarkKind.HYDROTHERMAL_VENT,
        x=0, y=0, band=4,
    )
    new = s.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=100,
    )
    assert len(new) == 0


def test_no_discovery_too_far():
    s = SeafloorLandmarks()
    s.register(
        landmark_id="lm1", name="Vent",
        kind=LandmarkKind.HYDROTHERMAL_VENT,
        x=0, y=0, band=3,
    )
    new = s.check_discovery(
        player_id="p1",
        x=DISCOVERY_RADIUS + 10, y=0,
        band=3, now_seconds=100,
    )
    assert len(new) == 0


def test_discovery_persists():
    s = SeafloorLandmarks()
    s.register(
        landmark_id="lm1", name="Vent",
        kind=LandmarkKind.HYDROTHERMAL_VENT,
        x=0, y=0, band=3,
    )
    s.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=100,
    )
    # walk away — still discovered
    assert s.is_discovered(player_id="p1", landmark_id="lm1")


def test_no_double_discovery():
    s = SeafloorLandmarks()
    s.register(
        landmark_id="lm1", name="Vent",
        kind=LandmarkKind.HYDROTHERMAL_VENT,
        x=0, y=0, band=3,
    )
    s.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=100,
    )
    new = s.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=200,
    )
    assert len(new) == 0


def test_discoveries_isolated_per_player():
    s = SeafloorLandmarks()
    s.register(
        landmark_id="lm1", name="Vent",
        kind=LandmarkKind.HYDROTHERMAL_VENT,
        x=0, y=0, band=3,
    )
    s.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=100,
    )
    assert s.is_discovered(player_id="p1", landmark_id="lm1")
    assert not s.is_discovered(player_id="p2", landmark_id="lm1")


def test_discovered_for_returns_all():
    s = SeafloorLandmarks()
    s.register(
        landmark_id="lm1", name="Vent",
        kind=LandmarkKind.HYDROTHERMAL_VENT,
        x=0, y=0, band=3,
    )
    s.register(
        landmark_id="lm2", name="Wreck",
        kind=LandmarkKind.WRECK,
        x=20, y=0, band=3,
    )
    s.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=100,
    )
    s.check_discovery(
        player_id="p1", x=20, y=0, band=3, now_seconds=200,
    )
    out = s.discovered_for(player_id="p1")
    assert len(out) == 2


def test_discovered_for_empty_for_unknown_player():
    s = SeafloorLandmarks()
    out = s.discovered_for(player_id="ghost")
    assert out == ()


def test_simultaneous_discovery_returns_multiple():
    s = SeafloorLandmarks()
    s.register(
        landmark_id="lm1", name="Vent",
        kind=LandmarkKind.HYDROTHERMAL_VENT,
        x=0, y=0, band=3,
    )
    s.register(
        landmark_id="lm2", name="Spire",
        kind=LandmarkKind.ABYSS_SPIRE,
        x=20, y=20, band=3,
    )
    new = s.check_discovery(
        player_id="p1", x=10, y=10, band=3, now_seconds=100,
    )
    assert len(new) == 2


def test_kelp_forest_kind():
    s = SeafloorLandmarks()
    s.register(
        landmark_id="lm1", name="The Forest",
        kind=LandmarkKind.KELP_FOREST,
        x=0, y=0, band=1,
    )
    new = s.check_discovery(
        player_id="p1", x=5, y=5, band=1, now_seconds=10,
    )
    assert new[0].kind == LandmarkKind.KELP_FOREST
