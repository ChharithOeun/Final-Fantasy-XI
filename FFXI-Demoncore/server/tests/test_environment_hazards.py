"""Tests for environment_hazards."""
from __future__ import annotations

from server.arena_environment import FeatureKind
from server.environment_hazards import (
    CEILING_DEBRIS_DAMAGE,
    CEILING_STUN_SECONDS,
    EnvironmentHazards,
    FLOOR_FALL_DAMAGE,
    HazardKind,
    ICE_BREAK_DROWN_TIMER_SECONDS,
    ICE_BREAK_FROST_SLEEP_SECONDS,
    PILLAR_CRUSH_DAMAGE,
    SHIP_LIST_SLIDE_YALMS,
)


def test_floor_collapse_drops_players():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="floor_main",
        feature_kind=FeatureKind.FLOOR, feature_band=1,
        players_in_radius=[("alice", 1), ("bob", 2)],
    )
    assert len(out) == 2
    assert all(e.hazard == HazardKind.FLOOR_COLLAPSE for e in out)
    assert all(e.damage == FLOOR_FALL_DAMAGE for e in out)
    assert all(e.band_change == -1 for e in out)


def test_floor_collapse_skips_below_floor():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="floor_main",
        feature_kind=FeatureKind.FLOOR, feature_band=1,
        players_in_radius=[("alice", 0)],   # below floor
    )
    assert out == ()


def test_ice_break_drowns_players_on_ice():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="ice_lake",
        feature_kind=FeatureKind.ICE_SHEET, feature_band=0,
        players_in_radius=[("alice", 0)],
    )
    assert len(out) == 1
    e = out[0]
    assert e.hazard == HazardKind.ICE_BREAK
    assert e.status_id == "frost_sleep"
    assert e.status_seconds == ICE_BREAK_FROST_SLEEP_SECONDS
    assert e.drown_timer_seconds == ICE_BREAK_DROWN_TIMER_SECONDS
    assert e.band_change == -1


def test_ceiling_crumble_stuns_below():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="roof",
        feature_kind=FeatureKind.CEILING, feature_band=3,
        players_in_radius=[("alice", 2), ("bob", 1)],
    )
    assert len(out) == 2
    for e in out:
        assert e.damage == CEILING_DEBRIS_DAMAGE
        assert e.status_id == "stun"
        assert e.status_seconds == CEILING_STUN_SECONDS


def test_pillar_fall_crush_in_band():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="east_pillar",
        feature_kind=FeatureKind.PILLAR, feature_band=2,
        players_in_radius=[("alice", 2), ("bob", 1)],
    )
    # only band-2 alice is crushed
    assert len(out) == 1
    assert out[0].player_id == "alice"
    assert out[0].damage == PILLAR_CRUSH_DAMAGE


def test_bridge_sever_emits_split_tag():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="rope_bridge",
        feature_kind=FeatureKind.BRIDGE, feature_band=1,
        players_in_radius=[("alice", 1), ("bob", 1)],
    )
    assert len(out) == 2
    assert all(e.hazard == HazardKind.BRIDGE_SEVER for e in out)
    assert all("split" in e.notes for e in out)


def test_dam_burst_flood_warning():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="great_dam",
        feature_kind=FeatureKind.DAM, feature_band=0,
        players_in_radius=[("alice", 1), ("bob", 2)],
    )
    assert len(out) == 2
    assert all(e.hazard == HazardKind.DAM_BURST for e in out)


def test_ship_list_slides_players():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="port_hull",
        feature_kind=FeatureKind.SHIP_HULL, feature_band=1,
        players_in_radius=[("alice", 1)],
    )
    assert out[0].hazard == HazardKind.SHIP_LIST
    assert out[0].knockback_yalms == SHIP_LIST_SLIDE_YALMS


def test_wall_breach_tag_only():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="north_wall",
        feature_kind=FeatureKind.WALL, feature_band=2,
        players_in_radius=[("alice", 2)],
    )
    assert len(out) == 1
    assert out[0].hazard == HazardKind.WALL_BREACH
    assert out[0].damage == 0   # no direct damage; habitat module fires


def test_resolve_crack_fires_warnings():
    h = EnvironmentHazards()
    out = h.resolve_crack(
        arena_id="a1", feature_id="floor_main",
        feature_kind=FeatureKind.FLOOR, feature_band=1,
        players_in_radius=[("alice", 1), ("bob", 0)],
    )
    assert len(out) == 2
    assert all("cracked" in e.notes for e in out)


def test_resolve_crack_skips_distant_players():
    h = EnvironmentHazards()
    out = h.resolve_crack(
        arena_id="a1", feature_id="floor_main",
        feature_kind=FeatureKind.FLOOR, feature_band=1,
        players_in_radius=[("alice", 4)],   # 3 bands away
    )
    assert out == ()


def test_no_players_returns_empty():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.FLOOR, feature_band=1,
        players_in_radius=[],
    )
    assert out == ()


def test_blank_player_id_filtered():
    h = EnvironmentHazards()
    out = h.resolve_break(
        arena_id="a1", feature_id="x",
        feature_kind=FeatureKind.FLOOR, feature_band=1,
        players_in_radius=[("", 1), ("alice", 1)],
    )
    assert len(out) == 1
    assert out[0].player_id == "alice"
