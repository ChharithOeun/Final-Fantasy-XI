"""Tests for world_demo_packaging."""
from __future__ import annotations

import pytest

from server.world_demo_packaging import (
    StreamingStrategy,
    TargetPlatform,
    ValidationStatus,
    WorldDemoBuildManifest,
    WorldDemoPackager,
    WorldValidationReport,
)


def _strict_packager() -> WorldDemoPackager:
    valid_zones = {
        "bastok_markets", "bastok_mines", "north_gustaberg",
        "south_sandoria", "windurst_woods", "lower_jeuno",
        "port_jeuno",
    }
    valid_boundaries = {
        "bnd_markets_to_mines",
        "bnd_mines_to_north_gustaberg",
        "bnd_bastok_to_jeuno_airship",
        "bnd_jeuno_to_sandoria_airship",
        "bnd_jeuno_to_windurst_airship",
    }
    valid_lighting = valid_zones
    return WorldDemoPackager(
        has_zone=lambda z: z in valid_zones,
        has_boundary=lambda b: b in valid_boundaries,
        has_lighting=lambda z: z in valid_lighting,
    )


# ---- enums ----

def test_streaming_strategy_enum_complete():
    names = {s.value for s in StreamingStrategy}
    assert names == {
        "all_resident", "ring_preload", "on_demand",
    }


def test_target_platform_enum_complete():
    names = {p.value for p in TargetPlatform}
    assert names == {
        "pc_ultra", "pc_high", "ps5",
        "xbox_series_x", "xbox_series_s",
    }


# ---- build_world_manifest ----

def test_build_world_manifest_creates_pending():
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="t",
        zone_ids=("a", "b"),
        entry_zone_id="a",
    )
    assert m.validation_status == ValidationStatus.PENDING


def test_build_world_manifest_unique_id():
    pkg = WorldDemoPackager()
    m1 = pkg.build_world_manifest(
        name="t1", zone_ids=("a",), entry_zone_id="a",
    )
    m2 = pkg.build_world_manifest(
        name="t2", zone_ids=("a",), entry_zone_id="a",
    )
    assert m1.manifest_id != m2.manifest_id


def test_build_world_manifest_empty_name_raises():
    pkg = WorldDemoPackager()
    with pytest.raises(ValueError):
        pkg.build_world_manifest(
            name="", zone_ids=("a",), entry_zone_id="a",
        )


def test_build_world_manifest_empty_zones_raises():
    pkg = WorldDemoPackager()
    with pytest.raises(ValueError):
        pkg.build_world_manifest(
            name="t", zone_ids=(), entry_zone_id="a",
        )


def test_build_world_manifest_entry_must_be_in_zones():
    pkg = WorldDemoPackager()
    with pytest.raises(ValueError):
        pkg.build_world_manifest(
            name="t", zone_ids=("a", "b"),
            entry_zone_id="not_in_list",
        )


def test_build_world_manifest_exit_must_be_in_zones():
    pkg = WorldDemoPackager()
    with pytest.raises(ValueError):
        pkg.build_world_manifest(
            name="t", zone_ids=("a", "b"),
            entry_zone_id="a",
            exit_zone_ids=("not_in_list",),
        )


def test_build_world_manifest_default_strategy_ring_preload():
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="t", zone_ids=("a",), entry_zone_id="a",
    )
    assert m.streaming_strategy == StreamingStrategy.RING_PRELOAD


def test_build_world_manifest_default_platform_pc_ultra():
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="t", zone_ids=("a",), entry_zone_id="a",
    )
    assert m.target_platform == TargetPlatform.PC_ULTRA


# ---- size estimation ----

def test_size_all_resident_full_factor():
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="t", zone_ids=("a", "b", "c"),
        entry_zone_id="a",
        boundary_handoffs_required=("b1", "b2"),
        streaming_strategy=StreamingStrategy.ALL_RESIDENT,
    )
    # 3*4.0 + 2*0.5 = 13.0 GB at 1.0 factor
    assert m.total_estimated_size_gb == 13.0


def test_size_ring_preload_60_percent():
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="t", zone_ids=("a", "b", "c"),
        entry_zone_id="a",
        streaming_strategy=StreamingStrategy.RING_PRELOAD,
    )
    # 3*4.0 = 12.0 GB at 0.6 factor = 7.2
    assert m.total_estimated_size_gb == 7.2


def test_size_on_demand_30_percent():
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="t", zone_ids=("a", "b"),
        entry_zone_id="a",
        streaming_strategy=StreamingStrategy.ON_DEMAND,
    )
    # 2*4.0 = 8.0 GB at 0.3 factor = 2.4
    assert m.total_estimated_size_gb == 2.4


# ---- lookup ----

def test_lookup_returns_manifest():
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="t", zone_ids=("a",), entry_zone_id="a",
    )
    assert pkg.lookup(m.manifest_id).name == "t"


def test_lookup_unknown_raises():
    pkg = WorldDemoPackager()
    with pytest.raises(KeyError):
        pkg.lookup("nope")


# ---- validate ----

def test_validate_strict_passes_when_all_present():
    pkg = _strict_packager()
    m = pkg.bastok_to_konschtat_default()
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.PASSED


def test_validate_default_packager_passes():
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="t", zone_ids=("a",), entry_zone_id="a",
        streaming_strategy=StreamingStrategy.ON_DEMAND,
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.PASSED


def test_validate_fails_when_zone_missing():
    pkg = _strict_packager()
    m = pkg.build_world_manifest(
        name="t",
        zone_ids=("bastok_markets", "ghost_zone"),
        entry_zone_id="bastok_markets",
        streaming_strategy=StreamingStrategy.ON_DEMAND,
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.FAILED
    assert "ghost_zone" in rep.missing_zones


def test_validate_fails_when_boundary_missing():
    pkg = _strict_packager()
    m = pkg.build_world_manifest(
        name="t",
        zone_ids=("bastok_markets", "bastok_mines"),
        entry_zone_id="bastok_markets",
        boundary_handoffs_required=("phantom_boundary",),
        streaming_strategy=StreamingStrategy.ON_DEMAND,
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.FAILED
    assert "phantom_boundary" in rep.missing_boundaries


def test_validate_fails_when_lighting_missing():
    pkg = WorldDemoPackager(
        has_zone=lambda z: True,
        has_boundary=lambda b: True,
        has_lighting=lambda z: z != "no_lighting_zone",
    )
    m = pkg.build_world_manifest(
        name="t",
        zone_ids=("bastok_markets", "no_lighting_zone"),
        entry_zone_id="bastok_markets",
        streaming_strategy=StreamingStrategy.ON_DEMAND,
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.FAILED
    assert "no_lighting_zone" in rep.missing_lighting


def test_validate_fails_when_over_budget():
    # Tiny budget, big manifest.
    pkg = WorldDemoPackager(
        platform_budget_mb=lambda p: 1024,  # 1 GB
    )
    m = pkg.build_world_manifest(
        name="big",
        zone_ids=("a", "b", "c"),
        entry_zone_id="a",
        streaming_strategy=StreamingStrategy.ALL_RESIDENT,
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.FAILED
    assert rep.over_budget is True


def test_validate_persists_missing_to_manifest():
    pkg = _strict_packager()
    m = pkg.build_world_manifest(
        name="t", zone_ids=("ghost",),
        entry_zone_id="ghost",
        streaming_strategy=StreamingStrategy.ON_DEMAND,
    )
    pkg.validate(m.manifest_id)
    m2 = pkg.lookup(m.manifest_id)
    assert m2.validation_status == ValidationStatus.FAILED
    assert any(
        s.startswith("zone:ghost")
        for s in m2.missing_assets
    )


def test_validate_unknown_manifest_raises():
    pkg = WorldDemoPackager()
    with pytest.raises(KeyError):
        pkg.validate("nope")


# ---- estimated / fits ----

def test_estimated_size_gb_lookup():
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="t", zone_ids=("a",), entry_zone_id="a",
    )
    assert pkg.estimated_size_gb(m.manifest_id) > 0


def test_platform_fits_pc_ultra_for_small_demo():
    pkg = WorldDemoPackager()
    m = pkg.bastok_to_konschtat_default()
    assert pkg.platform_fits(
        m.manifest_id, TargetPlatform.PC_ULTRA,
    )


def test_platform_fits_false_for_too_small_budget():
    # On-demand 30% factor, 41 zones = ~74 GB, won't fit on
    # XBOX_SERIES_S 8 GB.
    pkg = WorldDemoPackager()
    m = pkg.build_world_manifest(
        name="full",
        zone_ids=tuple(f"z{i}" for i in range(41)),
        entry_zone_id="z0",
        streaming_strategy=StreamingStrategy.ON_DEMAND,
    )
    assert not pkg.platform_fits(
        m.manifest_id, TargetPlatform.XBOX_SERIES_S,
    )


# ---- predefined demos ----

def test_bastok_to_konschtat_default():
    pkg = WorldDemoPackager()
    m = pkg.bastok_to_konschtat_default()
    assert m.entry_zone_id == "bastok_markets"
    assert "north_gustaberg" in m.zone_ids
    assert m.streaming_strategy \
        == StreamingStrategy.RING_PRELOAD
    assert len(m.zone_ids) == 3


def test_bastok_to_konschtat_validates_strict():
    pkg = _strict_packager()
    m = pkg.bastok_to_konschtat_default()
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.PASSED


def test_three_nations_grand_tour_default():
    pkg = WorldDemoPackager()
    m = pkg.three_nations_grand_tour_default()
    assert m.streaming_strategy \
        == StreamingStrategy.ALL_RESIDENT
    assert "south_sandoria" in m.zone_ids
    assert "windurst_woods" in m.zone_ids
    assert "bastok_markets" in m.zone_ids
    assert len(m.zone_ids) == 5


def test_three_nations_validates_strict():
    pkg = _strict_packager()
    m = pkg.three_nations_grand_tour_default()
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.PASSED


def test_full_world_flythrough_default():
    pkg = WorldDemoPackager()
    zones = tuple(f"z{i}" for i in range(41))
    m = pkg.full_world_flythrough_default(zones)
    assert m.streaming_strategy \
        == StreamingStrategy.ON_DEMAND
    assert len(m.zone_ids) == 41


def test_full_world_flythrough_empty_raises():
    pkg = WorldDemoPackager()
    with pytest.raises(ValueError):
        pkg.full_world_flythrough_default(())


# ---- frozen + filters ----

def test_world_manifest_frozen():
    pkg = WorldDemoPackager()
    m = pkg.bastok_to_konschtat_default()
    with pytest.raises(Exception):
        m.entry_zone_id = "x"  # type: ignore


def test_world_validation_report_frozen():
    rep = WorldValidationReport(
        manifest_id="m",
        status=ValidationStatus.PASSED,
        missing_zones=(),
        missing_boundaries=(),
        missing_lighting=(),
        over_budget=False,
        budget_mb=24576, estimated_mb=10000,
    )
    with pytest.raises(Exception):
        rep.over_budget = True  # type: ignore


def test_all_manifests_returns_all():
    pkg = WorldDemoPackager()
    pkg.bastok_to_konschtat_default()
    pkg.three_nations_grand_tour_default()
    assert len(pkg.all_manifests()) == 2
