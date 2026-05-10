"""Tests for world_streaming."""
from __future__ import annotations

import pytest

from server.world_streaming import (
    PLATFORM_BUDGET_MB,
    StreamAction,
    StreamPlatform,
    StreamTile,
    StreamingPlan,
    TileState,
    WorldStreamer,
)


def _tile(
    tid: str,
    cx: float = 0.0,
    cy: float = 0.0,
    cz: float = 0.0,
    size_mb: float = 100.0,
    half: float = 50.0,
    zone: str = "bastok_markets",
    neighbors: tuple[str, ...] = (),
) -> StreamTile:
    return StreamTile(
        tile_id=tid,
        zone_id=zone,
        bounds_min_xyz=(cx - half, cy - half, cz - half),
        bounds_max_xyz=(cx + half, cy + half, cz + half),
        asset_size_mb=size_mb,
        lod_levels=4,
        neighbor_tile_ids=neighbors,
    )


# ---- platform budgets ----

def test_platform_budget_table_complete():
    assert set(PLATFORM_BUDGET_MB.keys()) == {
        StreamPlatform.PC_ULTRA,
        StreamPlatform.PC_HIGH,
        StreamPlatform.PS5,
        StreamPlatform.XBOX_SERIES_X,
        StreamPlatform.XBOX_SERIES_S,
    }


def test_pc_ultra_budget_24gb():
    assert PLATFORM_BUDGET_MB[StreamPlatform.PC_ULTRA] == 24576


def test_xbox_series_s_budget_8gb():
    assert (
        PLATFORM_BUDGET_MB[StreamPlatform.XBOX_SERIES_S] == 8192
    )


def test_ps5_xbox_x_same_budget():
    assert (
        PLATFORM_BUDGET_MB[StreamPlatform.PS5]
        == PLATFORM_BUDGET_MB[StreamPlatform.XBOX_SERIES_X]
    )


# ---- WorldStreamer init ----

def test_default_radii_valid():
    s = WorldStreamer()
    assert s.prefetch_radius_m == 200.0
    assert s.keep_radius_m == 500.0
    assert s.evict_radius_m == 1500.0


def test_invalid_radii_ordering_raises():
    with pytest.raises(ValueError):
        WorldStreamer(
            prefetch_radius_m=500.0,
            keep_radius_m=200.0,
            evict_radius_m=1500.0,
        )


def test_zero_prefetch_radius_raises():
    with pytest.raises(ValueError):
        WorldStreamer(prefetch_radius_m=0.0)


# ---- register_tile ----

def test_register_tile_initial_state_unloaded():
    s = WorldStreamer()
    s.register_tile(_tile("t1"))
    assert s.state_of("t1") == TileState.UNLOADED


def test_register_tile_empty_id_raises():
    s = WorldStreamer()
    with pytest.raises(ValueError):
        s.register_tile(_tile(""))


def test_register_tile_negative_size_raises():
    s = WorldStreamer()
    with pytest.raises(ValueError):
        s.register_tile(_tile("t1", size_mb=-1.0))


def test_register_tile_zero_lods_raises():
    s = WorldStreamer()
    bad = StreamTile(
        tile_id="t1", zone_id="z",
        bounds_min_xyz=(0, 0, 0), bounds_max_xyz=(1, 1, 1),
        asset_size_mb=1.0, lod_levels=0,
    )
    with pytest.raises(ValueError):
        s.register_tile(bad)


def test_register_tile_inverted_bounds_raises():
    s = WorldStreamer()
    bad = StreamTile(
        tile_id="t1", zone_id="z",
        bounds_min_xyz=(10, 10, 10), bounds_max_xyz=(0, 0, 0),
        asset_size_mb=1.0, lod_levels=1,
    )
    with pytest.raises(ValueError):
        s.register_tile(bad)


def test_get_tile_unknown_raises():
    s = WorldStreamer()
    with pytest.raises(KeyError):
        s.get_tile("nope")


def test_state_of_unknown_raises():
    s = WorldStreamer()
    with pytest.raises(KeyError):
        s.state_of("nope")


def test_neighbors_of_returns_tuple():
    s = WorldStreamer()
    s.register_tile(_tile("t1", neighbors=("t2", "t3")))
    assert s.neighbors_of("t1") == ("t2", "t3")


def test_all_tiles_returns_all():
    s = WorldStreamer()
    s.register_tile(_tile("t1"))
    s.register_tile(_tile("t2"))
    assert len(s.all_tiles()) == 2


# ---- current_resident_mb / would_exceed_budget ----

def test_current_resident_zero_initially():
    s = WorldStreamer()
    s.register_tile(_tile("t1", size_mb=100))
    assert s.current_resident_mb() == 0.0


def test_current_resident_after_force_active():
    s = WorldStreamer()
    s.register_tile(_tile("t1", size_mb=200))
    s.force_state("t1", TileState.ACTIVE)
    assert s.current_resident_mb() == 200.0


def test_would_exceed_budget_false_when_empty():
    s = WorldStreamer()
    assert not s.would_exceed_budget(
        StreamPlatform.PC_ULTRA, [],
    )


def test_would_exceed_budget_true_when_over():
    s = WorldStreamer()
    s.register_tile(_tile("t1", size_mb=10000))
    s.force_state("t1", TileState.ACTIVE)
    s.register_tile(_tile("t2", size_mb=10000))
    s.register_tile(_tile("t3", size_mb=10000))
    # 10000 resident + 20000 additional > 24576 PC_ULTRA budget.
    assert s.would_exceed_budget(
        StreamPlatform.PC_ULTRA, ["t2", "t3"],
    )


def test_would_exceed_budget_skips_already_resident():
    s = WorldStreamer()
    s.register_tile(_tile("t1", size_mb=10000))
    s.force_state("t1", TileState.ACTIVE)
    # Asking again about t1 should not double-count.
    assert not s.would_exceed_budget(
        StreamPlatform.PC_ULTRA, ["t1"],
    )


# ---- plan_streaming_for ----

def test_plan_loads_tile_inside_prefetch_radius():
    s = WorldStreamer()
    s.register_tile(_tile("t1", cx=50.0, half=10.0))
    plan = s.plan_streaming_for(
        (0.0, 0.0, 0.0), StreamPlatform.PC_ULTRA,
    )
    actions = dict(plan.actions)
    assert actions["t1"] == StreamAction.LOAD


def test_plan_keeps_tile_inside_keep_radius_when_loaded():
    s = WorldStreamer()
    s.register_tile(_tile("t1", cx=300.0, half=10.0))
    s.force_state("t1", TileState.LOADED)
    plan = s.plan_streaming_for(
        (0.0, 0.0, 0.0), StreamPlatform.PC_ULTRA,
    )
    actions = dict(plan.actions)
    assert actions["t1"] == StreamAction.KEEP


def test_plan_cools_tile_in_evict_ring():
    s = WorldStreamer()
    s.register_tile(_tile("t1", cx=800.0, half=10.0))
    s.force_state("t1", TileState.ACTIVE)
    plan = s.plan_streaming_for(
        (0.0, 0.0, 0.0), StreamPlatform.PC_ULTRA,
    )
    actions = dict(plan.actions)
    assert actions["t1"] == StreamAction.COOL
    assert s.state_of("t1") == TileState.COOLING


def test_plan_evicts_tile_outside_evict_ring():
    s = WorldStreamer()
    s.register_tile(_tile("t1", cx=2000.0, half=10.0))
    s.force_state("t1", TileState.ACTIVE)
    plan = s.plan_streaming_for(
        (0.0, 0.0, 0.0), StreamPlatform.PC_ULTRA,
    )
    actions = dict(plan.actions)
    assert actions["t1"] == StreamAction.EVICT
    assert s.state_of("t1") == TileState.UNLOADED


def test_plan_no_action_for_distant_unloaded_tile():
    s = WorldStreamer()
    s.register_tile(_tile("t1", cx=2000.0, half=10.0))
    plan = s.plan_streaming_for(
        (0.0, 0.0, 0.0), StreamPlatform.PC_ULTRA,
    )
    actions = dict(plan.actions)
    assert actions["t1"] == StreamAction.KEEP
    assert s.state_of("t1") == TileState.UNLOADED


def test_plan_evicts_cheapest_under_pressure():
    s = WorldStreamer()
    # Three tiles, all in cooling ring, total 9000 MB.
    s.register_tile(
        _tile("expensive", cx=800.0, half=10.0, size_mb=5000),
    )
    s.register_tile(
        _tile("medium", cx=900.0, half=10.0, size_mb=3000),
    )
    s.register_tile(
        _tile("cheap", cx=700.0, half=10.0, size_mb=1000),
    )
    s.force_state("expensive", TileState.ACTIVE)
    s.force_state("medium", TileState.ACTIVE)
    s.force_state("cheap", TileState.ACTIVE)
    # XBOX_SERIES_S has only 8192 MB; we're at 9000.
    plan = s.plan_streaming_for(
        (0.0, 0.0, 0.0), StreamPlatform.XBOX_SERIES_S,
    )
    # Cheapest cooling tile gets evicted.
    actions = dict(plan.actions)
    assert actions["cheap"] == StreamAction.EVICT
    # Remaining 8000 MB is under budget.
    assert plan.over_budget_by_mb == 0.0


def test_plan_promotes_loaded_to_active_inside_keep():
    s = WorldStreamer()
    s.register_tile(_tile("t1", cx=10.0, half=5.0))
    s.force_state("t1", TileState.LOADED)
    s.plan_streaming_for(
        (0.0, 0.0, 0.0), StreamPlatform.PC_ULTRA,
    )
    assert s.state_of("t1") == TileState.ACTIVE


def test_plan_load_brings_tile_resident():
    s = WorldStreamer()
    s.register_tile(_tile("t1", cx=50.0, half=10.0, size_mb=200))
    plan = s.plan_streaming_for(
        (0.0, 0.0, 0.0), StreamPlatform.PC_ULTRA,
    )
    assert plan.resident_mb_after == 200.0


def test_plan_actions_sorted_by_tile_id():
    s = WorldStreamer()
    s.register_tile(_tile("zzz", cx=10.0, half=5.0))
    s.register_tile(_tile("aaa", cx=10.0, half=5.0))
    plan = s.plan_streaming_for(
        (0.0, 0.0, 0.0), StreamPlatform.PC_ULTRA,
    )
    ids = [tid for tid, _ in plan.actions]
    assert ids == sorted(ids)


def test_streaming_plan_dataclass_frozen():
    plan = StreamingPlan(
        actions=(),
        resident_mb_after=0.0,
        over_budget_by_mb=0.0,
    )
    with pytest.raises(Exception):
        plan.resident_mb_after = 100.0  # type: ignore


def test_tile_dataclass_frozen():
    t = _tile("t1")
    with pytest.raises(Exception):
        t.asset_size_mb = 999  # type: ignore


# ---- tiles_in_state / force_state ----

def test_tiles_in_state_filters():
    s = WorldStreamer()
    s.register_tile(_tile("t1"))
    s.register_tile(_tile("t2"))
    s.force_state("t1", TileState.ACTIVE)
    assert s.tiles_in_state(TileState.ACTIVE) == ("t1",)
    assert s.tiles_in_state(TileState.UNLOADED) == ("t2",)


def test_force_state_unknown_raises():
    s = WorldStreamer()
    with pytest.raises(KeyError):
        s.force_state("nope", TileState.ACTIVE)


def test_three_state_enum_values_present():
    assert TileState.UNLOADED.value == "unloaded"
    assert TileState.LOADING.value == "loading"
    assert TileState.LOADED.value == "loaded"
    assert TileState.ACTIVE.value == "active"
    assert TileState.COOLING.value == "cooling"


def test_stream_action_enum_values():
    assert StreamAction.LOAD.value == "load"
    assert StreamAction.KEEP.value == "keep"
    assert StreamAction.COOL.value == "cool"
    assert StreamAction.EVICT.value == "evict"
