"""Tests for the treasure map system."""
from __future__ import annotations

from server.treasure_map import (
    MapQuality,
    TreasureCacheTier,
    TreasureMapRegistry,
)


def test_mint_map_returns_record():
    reg = TreasureMapRegistry()
    m = reg.mint_map(
        zone_id="batallia", x=100, y=200,
        quality=MapQuality.PRISTINE,
    )
    assert m is not None
    assert m.uses_remaining == 3
    assert m.cache_tier == TreasureCacheTier.HIGH


def test_mint_uses_per_quality():
    reg = TreasureMapRegistry()
    m1 = reg.mint_map(
        zone_id="z", x=0, y=0, quality=MapQuality.WORN,
    )
    m2 = reg.mint_map(
        zone_id="z", x=0, y=0, quality=MapQuality.DECENT,
    )
    assert m1.uses_remaining == 1
    assert m2.uses_remaining == 2


def test_grant_to_player():
    reg = TreasureMapRegistry()
    m = reg.mint_map(
        zone_id="z", x=0, y=0, quality=MapQuality.WORN,
    )
    assert reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    assert m.holder_player_id == "alice"


def test_grant_unknown_map_rejected():
    reg = TreasureMapRegistry()
    assert not reg.grant_to_player(
        map_id="ghost", player_id="alice",
    )


def test_grant_already_held_rejected():
    reg = TreasureMapRegistry()
    m = reg.mint_map(
        zone_id="z", x=0, y=0, quality=MapQuality.WORN,
    )
    reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    assert not reg.grant_to_player(
        map_id=m.map_id, player_id="bob",
    )


def test_dig_at_x_succeeds():
    reg = TreasureMapRegistry()
    m = reg.mint_map(
        zone_id="batallia", x=100, y=200,
        quality=MapQuality.DECENT,
    )
    reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    res = reg.dig(
        player_id="alice", map_id=m.map_id,
        zone_id="batallia", x=100, y=200,
    )
    assert res.accepted
    assert res.cache_tier == TreasureCacheTier.MID
    assert res.map_consumed


def test_dig_within_tolerance_succeeds():
    reg = TreasureMapRegistry(dig_radius=10.0)
    m = reg.mint_map(
        zone_id="z", x=100, y=100,
        quality=MapQuality.WORN,
    )
    reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    res = reg.dig(
        player_id="alice", map_id=m.map_id,
        zone_id="z", x=105, y=103,
    )
    assert res.accepted


def test_dig_outside_tolerance_burns_use():
    reg = TreasureMapRegistry(dig_radius=10.0)
    m = reg.mint_map(
        zone_id="z", x=100, y=100,
        quality=MapQuality.PRISTINE,    # 3 uses
    )
    reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    res = reg.dig(
        player_id="alice", map_id=m.map_id,
        zone_id="z", x=200, y=200,
    )
    assert not res.accepted
    assert "too far" in res.reason
    assert res.uses_remaining == 2


def test_dig_wrong_zone_burns_use():
    reg = TreasureMapRegistry()
    m = reg.mint_map(
        zone_id="z1", x=100, y=100,
        quality=MapQuality.DECENT,    # 2 uses
    )
    reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    res = reg.dig(
        player_id="alice", map_id=m.map_id,
        zone_id="z2", x=100, y=100,
    )
    assert not res.accepted
    assert "wrong zone" in res.reason
    assert res.uses_remaining == 1


def test_dig_burning_last_use_consumes_map():
    reg = TreasureMapRegistry()
    m = reg.mint_map(
        zone_id="z1", x=100, y=100,
        quality=MapQuality.WORN,    # 1 use
    )
    reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    res = reg.dig(
        player_id="alice", map_id=m.map_id,
        zone_id="z2", x=100, y=100,
    )
    assert res.map_consumed
    assert res.uses_remaining == 0


def test_dig_consumed_map_rejected():
    reg = TreasureMapRegistry()
    m = reg.mint_map(
        zone_id="z", x=0, y=0,
        quality=MapQuality.WORN,
    )
    reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    reg.dig(
        player_id="alice", map_id=m.map_id,
        zone_id="z", x=0, y=0,
    )
    res = reg.dig(
        player_id="alice", map_id=m.map_id,
        zone_id="z", x=0, y=0,
    )
    assert not res.accepted
    assert "consumed" in res.reason


def test_dig_unknown_map():
    reg = TreasureMapRegistry()
    res = reg.dig(
        player_id="alice", map_id="ghost",
        zone_id="z", x=0, y=0,
    )
    assert not res.accepted


def test_dig_wrong_holder_rejected():
    reg = TreasureMapRegistry()
    m = reg.mint_map(
        zone_id="z", x=0, y=0, quality=MapQuality.WORN,
    )
    reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    res = reg.dig(
        player_id="bob", map_id=m.map_id,
        zone_id="z", x=0, y=0,
    )
    assert not res.accepted
    assert "holder" in res.reason


def test_explicit_cache_tier_override():
    reg = TreasureMapRegistry()
    m = reg.mint_map(
        zone_id="z", x=0, y=0, quality=MapQuality.WORN,
        cache_tier=TreasureCacheTier.NM_MARKED,
    )
    assert m.cache_tier == TreasureCacheTier.NM_MARKED


def test_total_maps_count():
    reg = TreasureMapRegistry()
    reg.mint_map(
        zone_id="z", x=0, y=0, quality=MapQuality.WORN,
    )
    reg.mint_map(
        zone_id="z", x=0, y=0, quality=MapQuality.DECENT,
    )
    assert reg.total_maps() == 2


def test_distance_reported_in_result():
    reg = TreasureMapRegistry(dig_radius=5.0)
    m = reg.mint_map(
        zone_id="z", x=100, y=100,
        quality=MapQuality.PRISTINE,
    )
    reg.grant_to_player(
        map_id=m.map_id, player_id="alice",
    )
    res = reg.dig(
        player_id="alice", map_id=m.map_id,
        zone_id="z", x=110, y=100,
    )
    assert res.distance_to_x == 10.0
