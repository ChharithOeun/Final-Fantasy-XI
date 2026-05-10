"""Tests for demo_packaging."""
from __future__ import annotations

import pytest

from server.demo_packaging import (
    DemoBuildManifest,
    DemoPackager,
    KNOWN_RENDER_PRESETS,
    TargetPlatform,
    ValidationReport,
    ValidationStatus,
)


def _packager_with_strict() -> DemoPackager:
    """Packager that knows only a tiny set of valid IDs."""
    valid_chars = {"volker", "cid", "iron_eater"}
    valid_voices = {
        "vline_a", "vline_b", "vline_volker_handoff_001",
    }
    valid_dressing = {"cid_forge", "cid_anvil"}
    return DemoPackager(
        has_character=lambda c: c in valid_chars,
        has_voice_line=lambda v: v in valid_voices,
        has_dressing_item=lambda d: d in valid_dressing,
    )


def _build_simple(
    pkg: DemoPackager,
    chars: tuple[str, ...] = ("volker",),
    voices: tuple[str, ...] = ("vline_a",),
    dress: tuple[str, ...] = ("cid_forge",),
    preset: str = "trailer_master",
) -> DemoBuildManifest:
    return pkg.build_manifest(
        name="test", zone_id="bastok_markets",
        character_ids=chars,
        voice_track_uris=voices,
        dressing_item_ids=dress,
        choreography_seq_name="bastok_markets_demo",
        render_preset=preset,
    )


# ---- Constants ----

def test_known_render_presets_set():
    assert "trailer_master" in KNOWN_RENDER_PRESETS
    assert "gameplay_realtime" in KNOWN_RENDER_PRESETS
    assert "cutscene_cinematic" in KNOWN_RENDER_PRESETS
    assert "social_clip" in KNOWN_RENDER_PRESETS
    assert "led_virtual_production" in KNOWN_RENDER_PRESETS


def test_target_platform_enum_complete():
    names = {p.value for p in TargetPlatform}
    assert names == {
        "pc_high", "pc_ultra", "xbox_series_x", "ps5",
    }


# ---- build_manifest validation ----

def test_build_manifest_creates_pending():
    pkg = DemoPackager()
    m = _build_simple(pkg)
    assert m.validation_status == ValidationStatus.PENDING
    assert m.zone_id == "bastok_markets"


def test_build_manifest_assigns_unique_id():
    pkg = DemoPackager()
    m1 = _build_simple(pkg)
    m2 = _build_simple(pkg)
    assert m1.manifest_id != m2.manifest_id


def test_build_manifest_empty_name_raises():
    pkg = DemoPackager()
    with pytest.raises(ValueError):
        pkg.build_manifest(
            name="", zone_id="z",
            choreography_seq_name="seq",
        )


def test_build_manifest_empty_zone_raises():
    pkg = DemoPackager()
    with pytest.raises(ValueError):
        pkg.build_manifest(
            name="x", zone_id="",
            choreography_seq_name="seq",
        )


def test_build_manifest_empty_choreography_raises():
    pkg = DemoPackager()
    with pytest.raises(ValueError):
        pkg.build_manifest(
            name="x", zone_id="z",
            choreography_seq_name="",
        )


def test_build_manifest_default_platform_pc_ultra():
    pkg = DemoPackager()
    m = _build_simple(pkg)
    assert m.target_platform == TargetPlatform.PC_ULTRA


# ---- estimated_size_gb formula ----

def test_estimated_size_zero_chars_zone_only_with_trailer():
    pkg = DemoPackager()
    m = pkg.build_manifest(
        name="x", zone_id="z",
        choreography_seq_name="seq",
        render_preset="trailer_master",
    )
    # 8.0 zone * 4.0 trailer master multiplier
    assert m.estimated_size_gb == 32.0


def test_estimated_size_chars_voices_dressing_gameplay():
    pkg = DemoPackager()
    m = pkg.build_manifest(
        name="x", zone_id="z",
        character_ids=("a", "b"),
        voice_track_uris=("v1", "v2", "v3", "v4"),
        dressing_item_ids=("d1", "d2", "d3"),
        choreography_seq_name="seq",
        render_preset="gameplay_realtime",
    )
    # 8.0 + 2*1.2 + 4*0.05 + 3*0.001 = 10.603, *1.0 mult
    assert m.estimated_size_gb == 10.603


def test_estimated_size_trailer_master_4x_gameplay():
    pkg = DemoPackager()
    m_trailer = pkg.build_manifest(
        name="t", zone_id="z",
        character_ids=("a",),
        choreography_seq_name="seq",
        render_preset="trailer_master",
    )
    m_play = pkg.build_manifest(
        name="p", zone_id="z",
        character_ids=("a",),
        choreography_seq_name="seq",
        render_preset="gameplay_realtime",
    )
    # 4x ratio.
    assert (
        round(m_trailer.estimated_size_gb / m_play.estimated_size_gb, 3)
        == 4.0
    )


def test_estimated_size_unknown_preset_falls_to_1x():
    pkg = DemoPackager(known_render_preset=lambda x: True)
    m = pkg.build_manifest(
        name="x", zone_id="z",
        character_ids=("a",),
        choreography_seq_name="seq",
        render_preset="weird_preset",
    )
    assert m.estimated_size_gb == 9.2


# ---- lookup ----

def test_lookup_returns_manifest():
    pkg = DemoPackager()
    m = _build_simple(pkg)
    assert pkg.lookup(m.manifest_id).name == "test"


def test_lookup_unknown_raises():
    pkg = DemoPackager()
    with pytest.raises(KeyError):
        pkg.lookup("nope")


# ---- validate ----

def test_validate_default_packager_passes():
    pkg = DemoPackager()  # accept_all defaults
    m = _build_simple(pkg)
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.PASSED


def test_validate_strict_passes_when_all_present():
    pkg = _packager_with_strict()
    m = pkg.build_manifest(
        name="x", zone_id="bastok_markets",
        character_ids=("volker", "cid"),
        voice_track_uris=("vline_a", "vline_b"),
        dressing_item_ids=("cid_forge", "cid_anvil"),
        choreography_seq_name="seq",
        render_preset="trailer_master",
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.PASSED
    assert rep.missing_characters == ()


def test_validate_fails_when_character_missing():
    pkg = _packager_with_strict()
    m = pkg.build_manifest(
        name="x", zone_id="z",
        character_ids=("volker", "ghost_npc"),
        voice_track_uris=("vline_a",),
        dressing_item_ids=("cid_forge",),
        choreography_seq_name="seq",
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.FAILED
    assert "ghost_npc" in rep.missing_characters


def test_validate_fails_when_voice_missing():
    pkg = _packager_with_strict()
    m = pkg.build_manifest(
        name="x", zone_id="z",
        character_ids=("volker",),
        voice_track_uris=("vline_a", "vline_missing"),
        dressing_item_ids=("cid_forge",),
        choreography_seq_name="seq",
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.FAILED
    assert "vline_missing" in rep.missing_voice_lines


def test_validate_fails_when_dressing_missing():
    pkg = _packager_with_strict()
    m = pkg.build_manifest(
        name="x", zone_id="z",
        character_ids=("volker",),
        voice_track_uris=("vline_a",),
        dressing_item_ids=("cid_forge", "phantom_chair"),
        choreography_seq_name="seq",
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.FAILED
    assert "phantom_chair" in rep.missing_dressing


def test_validate_fails_when_unknown_preset():
    pkg = _packager_with_strict()
    m = pkg.build_manifest(
        name="x", zone_id="z",
        character_ids=("volker",),
        voice_track_uris=("vline_a",),
        dressing_item_ids=("cid_forge",),
        choreography_seq_name="seq",
        render_preset="not_a_real_preset",
    )
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.FAILED
    assert rep.unknown_render_preset is True


def test_validate_persists_missing_to_manifest():
    pkg = _packager_with_strict()
    m = pkg.build_manifest(
        name="x", zone_id="z",
        character_ids=("ghost_npc",),
        voice_track_uris=("vline_a",),
        dressing_item_ids=("cid_forge",),
        choreography_seq_name="seq",
    )
    pkg.validate(m.manifest_id)
    m2 = pkg.lookup(m.manifest_id)
    assert m2.validation_status == ValidationStatus.FAILED
    assert any(
        s.startswith("char:ghost_npc")
        for s in m2.missing_assets
    )


def test_validate_unknown_manifest_raises():
    pkg = DemoPackager()
    with pytest.raises(KeyError):
        pkg.validate("nope")


# ---- missing_assets_for / estimated_size_gb ----

def test_missing_assets_for_returns_empty_when_passed():
    pkg = DemoPackager()
    m = _build_simple(pkg)
    pkg.validate(m.manifest_id)
    assert pkg.missing_assets_for(m.manifest_id) == ()


def test_estimated_size_gb_lookup():
    pkg = DemoPackager()
    m = _build_simple(pkg)
    assert pkg.estimated_size_gb(m.manifest_id) > 0


# ---- Filters ----

def test_manifests_for_platform():
    pkg = DemoPackager()
    pkg.build_manifest(
        name="a", zone_id="z",
        choreography_seq_name="seq",
        target_platform=TargetPlatform.PC_HIGH,
    )
    pkg.build_manifest(
        name="b", zone_id="z",
        choreography_seq_name="seq",
        target_platform=TargetPlatform.PS5,
    )
    high = pkg.manifests_for_platform(TargetPlatform.PC_HIGH)
    assert len(high) == 1
    assert high[0].name == "a"


def test_passing_manifests_filter():
    pkg = _packager_with_strict()
    good = pkg.build_manifest(
        name="g", zone_id="z",
        character_ids=("volker",),
        voice_track_uris=("vline_a",),
        dressing_item_ids=("cid_forge",),
        choreography_seq_name="seq",
    )
    bad = pkg.build_manifest(
        name="b", zone_id="z",
        character_ids=("ghost",),
        voice_track_uris=("vline_a",),
        dressing_item_ids=("cid_forge",),
        choreography_seq_name="seq",
    )
    pkg.validate(good.manifest_id)
    pkg.validate(bad.manifest_id)
    passing = pkg.passing_manifests()
    assert len(passing) == 1
    assert passing[0].manifest_id == good.manifest_id


# ---- bastok_markets_default ----

def test_bastok_markets_default_returns_manifest():
    pkg = DemoPackager()
    m = pkg.bastok_markets_default()
    assert m.zone_id == "bastok_markets"
    assert m.target_platform == TargetPlatform.PC_ULTRA
    assert m.choreography_seq_name == "bastok_markets_demo"
    assert m.render_preset == "trailer_master"


def test_bastok_markets_default_includes_demo_roster():
    pkg = DemoPackager()
    m = pkg.bastok_markets_default()
    chars = set(m.character_ids)
    for needed in (
        "volker", "cid", "iron_eater", "naji",
        "romaa_mihgo", "cornelia", "lhe_lhangavo",
    ):
        assert needed in chars
    assert len(m.character_ids) >= 11


def test_bastok_markets_default_validates_passing_with_lax_packager():
    pkg = DemoPackager()  # accept_all defaults
    m = pkg.bastok_markets_default()
    rep = pkg.validate(m.manifest_id)
    assert rep.status == ValidationStatus.PASSED


def test_bastok_markets_default_size_above_zone_baseline():
    pkg = DemoPackager()
    m = pkg.bastok_markets_default()
    # Trailer master (4x) of (8 + 11*1.2 + 10*0.05 + 31*0.001).
    assert m.estimated_size_gb > 30.0


def test_validation_report_dataclass_frozen():
    rep = ValidationReport(
        manifest_id="m", status=ValidationStatus.PASSED,
        missing_characters=(), missing_voice_lines=(),
        missing_dressing=(), unknown_render_preset=False,
    )
    with pytest.raises(dataclass_frozen_error()):
        rep.status = ValidationStatus.FAILED  # type: ignore


def dataclass_frozen_error():
    """Helper — frozen dataclasses raise dataclasses.FrozenInstanceError."""
    import dataclasses
    return dataclasses.FrozenInstanceError


def test_all_manifests_returns_all():
    pkg = DemoPackager()
    _build_simple(pkg)
    _build_simple(pkg)
    assert len(pkg.all_manifests()) == 2
