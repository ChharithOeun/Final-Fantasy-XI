"""Tests for niagara_vfx_library."""
from __future__ import annotations

import pytest

from server.niagara_vfx_library import (
    CinematicTier,
    ComputeMode,
    VfxEffect,
    VfxElement,
    VfxKind,
    VfxLibrary,
    WARMUP_THRESHOLD,
    populate_default_library,
)


# ---- enums ----

def test_eight_elements():
    assert {e for e in VfxElement if e != VfxElement.NONE} == {
        VfxElement.FIRE, VfxElement.EARTH, VfxElement.WATER,
        VfxElement.WIND, VfxElement.ICE, VfxElement.LIGHTNING,
        VfxElement.LIGHT, VfxElement.DARK,
    }


def test_kind_count_at_least_22():
    assert len(list(VfxKind)) >= 22


def test_four_cinematic_tiers():
    assert {t for t in CinematicTier} == {
        CinematicTier.LOW, CinematicTier.MED,
        CinematicTier.HIGH, CinematicTier.TRAILER,
    }


def test_two_compute_modes():
    assert {c for c in ComputeMode} == {
        ComputeMode.GPU, ComputeMode.CPU,
    }


# ---- register / lookup ----

def _make_effect(vfx_id="fx", kind=VfxKind.ELEMENT_FIRE, count=100):
    return VfxEffect(
        vfx_id=vfx_id,
        name="x",
        kind=kind,
        base_particle_count=count,
        duration_s=1.0,
        compute=ComputeMode.GPU,
        follows_emitter=False,
        cinematic_tier=CinematicTier.LOW,
        base_color_hex="#ffffff",
        secondary_color_hex="#000000",
        sound_cue_id="sfx_x",
        light_emit_lux=0.0,
    )


def test_register_and_lookup():
    lib = VfxLibrary()
    e = _make_effect()
    lib.register_effect(e)
    assert lib.lookup("fx") is e


def test_lookup_missing_raises():
    lib = VfxLibrary()
    with pytest.raises(KeyError):
        lib.lookup("missing")


def test_register_empty_id_raises():
    lib = VfxLibrary()
    with pytest.raises(ValueError):
        lib.register_effect(_make_effect(vfx_id=""))


def test_register_zero_duration_raises():
    lib = VfxLibrary()
    with pytest.raises(ValueError):
        lib.register_effect(VfxEffect(
            vfx_id="x", name="x", kind=VfxKind.ELEMENT_FIRE,
            base_particle_count=10, duration_s=0.0,
            compute=ComputeMode.GPU, follows_emitter=False,
            cinematic_tier=CinematicTier.LOW,
            base_color_hex="#ff0000",
            secondary_color_hex="#000000",
            sound_cue_id="x", light_emit_lux=0.0,
        ))


def test_register_negative_particle_count_raises():
    lib = VfxLibrary()
    with pytest.raises(ValueError):
        lib.register_effect(_make_effect(count=-1))


def test_register_duplicate_raises():
    lib = VfxLibrary()
    lib.register_effect(_make_effect())
    with pytest.raises(ValueError):
        lib.register_effect(_make_effect())


# ---- query helpers ----

def test_effects_with_kind():
    lib = VfxLibrary()
    lib.register_effect(_make_effect("a", VfxKind.ELEMENT_FIRE))
    lib.register_effect(_make_effect("b", VfxKind.ELEMENT_FIRE))
    lib.register_effect(_make_effect("c", VfxKind.ELEMENT_ICE))
    out = lib.effects_with_kind(VfxKind.ELEMENT_FIRE)
    assert len(out) == 2
    assert all(e.kind == VfxKind.ELEMENT_FIRE for e in out)


def test_effects_with_kind_sorted():
    lib = VfxLibrary()
    lib.register_effect(_make_effect("zzz", VfxKind.ELEMENT_FIRE))
    lib.register_effect(_make_effect("aaa", VfxKind.ELEMENT_FIRE))
    out = lib.effects_with_kind(VfxKind.ELEMENT_FIRE)
    assert [e.vfx_id for e in out] == ["aaa", "zzz"]


def test_effects_for_element():
    lib = VfxLibrary()
    populate_default_library(lib)
    fires = lib.effects_for_element(VfxElement.FIRE)
    # 5 tiers each
    assert len(fires) >= 5
    # All belong to fire
    assert all("fire" in e.vfx_id for e in fires)


def test_effects_for_element_water_distinct_from_ice():
    lib = VfxLibrary()
    populate_default_library(lib)
    water = lib.effects_for_element(VfxElement.WATER)
    ice = lib.effects_for_element(VfxElement.ICE)
    water_ids = {e.vfx_id for e in water}
    ice_ids = {e.vfx_id for e in ice}
    assert water_ids.isdisjoint(ice_ids)


# ---- tier scaling ----

def test_tier_scaled_low():
    lib = VfxLibrary()
    lib.register_effect(_make_effect(count=100))
    assert lib.tier_scaled_particle_count(
        "fx", CinematicTier.LOW,
    ) == 100


def test_tier_scaled_trailer_is_4x():
    lib = VfxLibrary()
    lib.register_effect(_make_effect(count=100))
    assert lib.tier_scaled_particle_count(
        "fx", CinematicTier.TRAILER,
    ) == 400


def test_tier_scaled_high_is_3x():
    lib = VfxLibrary()
    lib.register_effect(_make_effect(count=100))
    assert lib.tier_scaled_particle_count(
        "fx", CinematicTier.HIGH,
    ) == 300


def test_tier_scaled_med_is_2x():
    lib = VfxLibrary()
    lib.register_effect(_make_effect(count=50))
    assert lib.tier_scaled_particle_count(
        "fx", CinematicTier.MED,
    ) == 100


def test_tier_scaled_unknown_raises():
    lib = VfxLibrary()
    with pytest.raises(KeyError):
        lib.tier_scaled_particle_count("missing", CinematicTier.LOW)


# ---- warmup ----

def test_warmup_high_count():
    lib = VfxLibrary()
    lib.register_effect(_make_effect(count=WARMUP_THRESHOLD + 1))
    assert lib.warmup_recommended("fx") is True


def test_warmup_low_count():
    lib = VfxLibrary()
    lib.register_effect(_make_effect(count=10))
    assert lib.warmup_recommended("fx") is False


def test_warmup_at_threshold():
    lib = VfxLibrary()
    lib.register_effect(_make_effect(count=WARMUP_THRESHOLD))
    assert lib.warmup_recommended("fx") is True


def test_warmup_missing_raises():
    lib = VfxLibrary()
    with pytest.raises(KeyError):
        lib.warmup_recommended("missing")


# ---- all_effect_ids ----

def test_all_effect_ids_sorted():
    lib = VfxLibrary()
    lib.register_effect(_make_effect("zzz"))
    lib.register_effect(_make_effect("aaa"))
    assert lib.all_effect_ids() == ("aaa", "zzz")


def test_effect_count_tracks_registration():
    lib = VfxLibrary()
    assert lib.effect_count() == 0
    lib.register_effect(_make_effect())
    assert lib.effect_count() == 1


# ---- default library ----

def test_default_library_at_least_60_effects():
    lib = VfxLibrary()
    n = populate_default_library(lib)
    assert n >= 60
    assert lib.effect_count() == n


def test_default_library_covers_all_8_elements_5_tiers():
    lib = VfxLibrary()
    populate_default_library(lib)
    for elem in (
        VfxElement.FIRE, VfxElement.ICE, VfxElement.LIGHTNING,
        VfxElement.WATER, VfxElement.EARTH, VfxElement.WIND,
        VfxElement.LIGHT, VfxElement.DARK,
    ):
        # each element should have all 5 tiers
        ids = {e.vfx_id for e in lib.effects_for_element(elem)}
        for tier in ("tier_i", "tier_ii", "tier_iii",
                     "tier_iv", "tier_v"):
            assert f"{elem.value}_{tier}" in ids


def test_default_library_has_physical_kinds():
    lib = VfxLibrary()
    populate_default_library(lib)
    for kind in (
        VfxKind.PHYS_BLOOD, VfxKind.PHYS_SPARK,
        VfxKind.PHYS_SMOKE, VfxKind.PHYS_DUST,
        VfxKind.PHYS_EMBER, VfxKind.PHYS_DEBRIS,
    ):
        assert len(lib.effects_with_kind(kind)) > 0


def test_default_library_has_overlay_kinds():
    lib = VfxLibrary()
    populate_default_library(lib)
    for kind in (
        VfxKind.AOE_TELEGRAPH_RING, VfxKind.AOE_TELEGRAPH_LINE,
        VfxKind.IMPACT_FLASH, VfxKind.CASTING_CIRCLE,
        VfxKind.HAND_GLOW, VfxKind.MB_HALO, VfxKind.KO_AURA,
        VfxKind.RAISE_GLOW,
    ):
        assert len(lib.effects_with_kind(kind)) > 0


def test_default_library_high_tier_warm():
    lib = VfxLibrary()
    populate_default_library(lib)
    # tier_iv and tier_v carry > 500 particles by design.
    assert lib.warmup_recommended("fire_tier_iv") is True
    assert lib.warmup_recommended("fire_tier_v") is True


def test_default_library_low_tier_no_warm():
    lib = VfxLibrary()
    populate_default_library(lib)
    # tier_i fire is only 120 particles.
    assert lib.warmup_recommended("fire_tier_i") is False


def test_default_library_trailer_scales_4x_baseline():
    lib = VfxLibrary()
    populate_default_library(lib)
    fire_i = lib.lookup("fire_tier_i")
    scaled = lib.tier_scaled_particle_count(
        "fire_tier_i", CinematicTier.TRAILER,
    )
    assert scaled == fire_i.base_particle_count * 4


def test_mb_halo_present():
    lib = VfxLibrary()
    populate_default_library(lib)
    halos = lib.effects_with_kind(VfxKind.MB_HALO)
    assert len(halos) >= 1


def test_default_palette_distinct_per_element():
    lib = VfxLibrary()
    populate_default_library(lib)
    fire_i = lib.lookup("fire_tier_i")
    ice_i = lib.lookup("ice_tier_i")
    assert fire_i.base_color_hex != ice_i.base_color_hex


def test_default_compute_mode_is_gpu():
    lib = VfxLibrary()
    populate_default_library(lib)
    fire_v = lib.lookup("fire_tier_v")
    assert fire_v.compute == ComputeMode.GPU


def test_spark_follows_emitter_by_default():
    lib = VfxLibrary()
    populate_default_library(lib)
    spark = lib.lookup("spark_metal")
    assert spark.follows_emitter is True


def test_blood_does_not_follow_emitter():
    lib = VfxLibrary()
    populate_default_library(lib)
    blood = lib.lookup("blood_light")
    assert blood.follows_emitter is False


def test_default_sound_cue_id_format():
    lib = VfxLibrary()
    populate_default_library(lib)
    fire_iii = lib.lookup("fire_tier_iii")
    assert fire_iii.sound_cue_id.startswith("sfx_")


def test_light_emit_for_fire_increases_with_tier():
    lib = VfxLibrary()
    populate_default_library(lib)
    f1 = lib.lookup("fire_tier_i")
    f5 = lib.lookup("fire_tier_v")
    assert f5.light_emit_lux > f1.light_emit_lux
