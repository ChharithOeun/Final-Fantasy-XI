"""Tests for cloud landmarks."""
from __future__ import annotations

from server.cloud_landmarks import (
    CloudLandmarks,
    DISCOVERY_RADIUS,
    LandmarkKind,
)


def test_register_happy():
    c = CloudLandmarks()
    ok = c.register(
        landmark_id="lm1", name="The Cradle",
        kind=LandmarkKind.CLOUD_CITY,
        x=100, y=200, band=3,
        lore_blurb="ancient sky-port",
    )
    assert ok is True


def test_register_blank_name():
    c = CloudLandmarks()
    assert c.register(
        landmark_id="lm1", name="",
        kind=LandmarkKind.CLOUD_CITY,
        x=0, y=0, band=2,
    ) is False


def test_register_blank_id():
    c = CloudLandmarks()
    assert c.register(
        landmark_id="", name="X",
        kind=LandmarkKind.CLOUD_CITY,
        x=0, y=0, band=2,
    ) is False


def test_discover_within_radius():
    c = CloudLandmarks()
    c.register(
        landmark_id="lm1", name="Pillar",
        kind=LandmarkKind.WEATHER_PILLAR,
        x=0, y=0, band=3,
    )
    new = c.check_discovery(
        player_id="p1", x=20, y=20, band=3, now_seconds=100,
    )
    assert len(new) == 1
    assert new[0].landmark_id == "lm1"


def test_no_discovery_wrong_band():
    c = CloudLandmarks()
    c.register(
        landmark_id="lm1", name="Pillar",
        kind=LandmarkKind.WEATHER_PILLAR,
        x=0, y=0, band=4,
    )
    new = c.check_discovery(
        player_id="p1", x=0, y=0, band=2, now_seconds=100,
    )
    assert len(new) == 0


def test_no_discovery_too_far():
    c = CloudLandmarks()
    c.register(
        landmark_id="lm1", name="Pillar",
        kind=LandmarkKind.WEATHER_PILLAR,
        x=0, y=0, band=3,
    )
    new = c.check_discovery(
        player_id="p1",
        x=DISCOVERY_RADIUS + 50, y=0,
        band=3, now_seconds=100,
    )
    assert len(new) == 0


def test_discovery_persists():
    c = CloudLandmarks()
    c.register(
        landmark_id="lm1", name="Pillar",
        kind=LandmarkKind.WEATHER_PILLAR,
        x=0, y=0, band=3,
    )
    c.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=100,
    )
    assert c.is_discovered(player_id="p1", landmark_id="lm1")


def test_no_double_discovery():
    c = CloudLandmarks()
    c.register(
        landmark_id="lm1", name="Pillar",
        kind=LandmarkKind.WEATHER_PILLAR,
        x=0, y=0, band=3,
    )
    c.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=100,
    )
    new = c.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=200,
    )
    assert len(new) == 0


def test_per_player_isolation():
    c = CloudLandmarks()
    c.register(
        landmark_id="lm1", name="Pillar",
        kind=LandmarkKind.WEATHER_PILLAR,
        x=0, y=0, band=3,
    )
    c.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=100,
    )
    assert c.is_discovered(player_id="p1", landmark_id="lm1")
    assert not c.is_discovered(player_id="p2", landmark_id="lm1")


def test_discovered_for_returns_all():
    c = CloudLandmarks()
    c.register(
        landmark_id="lm1", name="A",
        kind=LandmarkKind.CLOUD_CITY,
        x=0, y=0, band=3,
    )
    c.register(
        landmark_id="lm2", name="B",
        kind=LandmarkKind.JET_GATE,
        x=20, y=0, band=3,
    )
    c.check_discovery(
        player_id="p1", x=0, y=0, band=3, now_seconds=100,
    )
    c.check_discovery(
        player_id="p1", x=20, y=0, band=3, now_seconds=200,
    )
    out = c.discovered_for(player_id="p1")
    assert len(out) == 2


def test_discovered_for_empty_unknown_player():
    c = CloudLandmarks()
    assert c.discovered_for(player_id="ghost") == ()


def test_jet_gate_kind():
    c = CloudLandmarks()
    c.register(
        landmark_id="lm1", name="The Vortex",
        kind=LandmarkKind.JET_GATE,
        x=0, y=0, band=4,
    )
    new = c.check_discovery(
        player_id="p1", x=10, y=10, band=4, now_seconds=10,
    )
    assert new[0].kind == LandmarkKind.JET_GATE


def test_floating_ruin_kind():
    c = CloudLandmarks()
    c.register(
        landmark_id="lm1", name="Old Bahamut",
        kind=LandmarkKind.FLOATING_RUIN,
        x=0, y=0, band=3,
    )
    new = c.check_discovery(
        player_id="p1", x=5, y=5, band=3, now_seconds=10,
    )
    assert new[0].kind == LandmarkKind.FLOATING_RUIN
