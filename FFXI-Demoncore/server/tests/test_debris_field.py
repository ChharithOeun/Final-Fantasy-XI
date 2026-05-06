"""Tests for debris_field."""
from __future__ import annotations

from server.arena_environment import FeatureKind
from server.debris_field import DebrisField, DebrisKind


def test_break_creates_pile():
    df = DebrisField()
    pile = df.on_feature_break(
        arena_id="a1", feature_id="north_wall",
        feature_kind=FeatureKind.WALL, band=2,
    )
    assert pile is not None
    assert pile.kind == DebrisKind.STONE_RUBBLE


def test_floor_break_makes_planks():
    df = DebrisField()
    pile = df.on_feature_break(
        arena_id="a1", feature_id="floor",
        feature_kind=FeatureKind.FLOOR, band=1,
    )
    assert pile.kind == DebrisKind.SPLINTERED_PLANKS


def test_ceiling_break_makes_burning_timber():
    df = DebrisField()
    pile = df.on_feature_break(
        arena_id="a1", feature_id="roof",
        feature_kind=FeatureKind.CEILING, band=3,
    )
    assert pile.kind == DebrisKind.BURNING_TIMBER


def test_ice_break_makes_shards():
    df = DebrisField()
    pile = df.on_feature_break(
        arena_id="a1", feature_id="ice",
        feature_kind=FeatureKind.ICE_SHEET, band=0,
    )
    assert pile.kind == DebrisKind.ICE_SHARDS


def test_dam_break_makes_soaked_rubble():
    df = DebrisField()
    pile = df.on_feature_break(
        arena_id="a1", feature_id="dam",
        feature_kind=FeatureKind.DAM, band=0,
    )
    assert pile.kind == DebrisKind.SOAKED_RUBBLE


def test_piles_for_band_returns_only_band():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="w1",
        feature_kind=FeatureKind.WALL, band=2,
    )
    df.on_feature_break(
        arena_id="a1", feature_id="w2",
        feature_kind=FeatureKind.WALL, band=3,
    )
    out = df.piles_for(arena_id="a1", band=2)
    assert len(out) == 1


def test_los_blocked_by_stone_rubble_in_band():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="w",
        feature_kind=FeatureKind.WALL, band=2,
    )
    assert df.blocks_los(
        arena_id="a1", from_band=2, to_band=2,
    ) is True


def test_los_blocked_between_bands_with_rubble_between():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="w",
        feature_kind=FeatureKind.WALL, band=2,
    )
    assert df.blocks_los(
        arena_id="a1", from_band=1, to_band=3,
    ) is True


def test_los_not_blocked_by_planks():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="floor",
        feature_kind=FeatureKind.FLOOR, band=2,
    )
    assert df.blocks_los(
        arena_id="a1", from_band=2, to_band=2,
    ) is False


def test_cover_dr_returns_best():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="w",
        feature_kind=FeatureKind.WALL, band=2,
    )  # 25%
    df.on_feature_break(
        arena_id="a1", feature_id="floor",
        feature_kind=FeatureKind.FLOOR, band=2,
    )  # 15%
    assert df.cover_dr_pct(arena_id="a1", player_band=2) == 25


def test_cover_dr_zero_in_empty_band():
    df = DebrisField()
    assert df.cover_dr_pct(arena_id="a1", player_band=4) == 0


def test_movement_cost_sums():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="w",
        feature_kind=FeatureKind.WALL, band=2,
    )  # 4
    df.on_feature_break(
        arena_id="a1", feature_id="p",
        feature_kind=FeatureKind.PILLAR, band=2,
    )  # 4
    assert df.movement_cost_yalms(arena_id="a1", band=2) == 8


def test_tick_hazards_burning_timber_damages():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="roof",
        feature_kind=FeatureKind.CEILING, band=2,
    )
    out = df.tick_hazards(
        arena_id="a1",
        players_in_band=[("alice", 2)],
        dt_seconds=1.0,
    )
    assert len(out) == 1
    assert out[0].damage == 80
    assert out[0].status_id == "burn"


def test_stone_rubble_no_hazard_tick():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="w",
        feature_kind=FeatureKind.WALL, band=2,
    )
    out = df.tick_hazards(
        arena_id="a1",
        players_in_band=[("alice", 2)],
        dt_seconds=1.0,
    )
    assert out == ()


def test_soaked_rubble_status_only():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="dam",
        feature_kind=FeatureKind.DAM, band=0,
    )
    out = df.tick_hazards(
        arena_id="a1",
        players_in_band=[("alice", 0)],
        dt_seconds=1.0,
    )
    # soaked rubble: dps=0, no tick fires
    assert out == ()


def test_player_in_different_band_no_tick():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="roof",
        feature_kind=FeatureKind.CEILING, band=2,
    )
    out = df.tick_hazards(
        arena_id="a1",
        players_in_band=[("alice", 0)],
        dt_seconds=1.0,
    )
    assert out == ()


def test_clear_arena_drops_all():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="w",
        feature_kind=FeatureKind.WALL, band=2,
    )
    df.clear_arena(arena_id="a1")
    assert df.all_piles(arena_id="a1") == ()


def test_all_piles_collects_across_bands():
    df = DebrisField()
    df.on_feature_break(
        arena_id="a1", feature_id="w1",
        feature_kind=FeatureKind.WALL, band=2,
    )
    df.on_feature_break(
        arena_id="a1", feature_id="w2",
        feature_kind=FeatureKind.WALL, band=3,
    )
    df.on_feature_break(
        arena_id="a1", feature_id="floor",
        feature_kind=FeatureKind.FLOOR, band=1,
    )
    assert len(df.all_piles(arena_id="a1")) == 3
