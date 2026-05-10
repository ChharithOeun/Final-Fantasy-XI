"""Tests for weaponskill_vfx."""
from __future__ import annotations

import pytest

from server.weaponskill_vfx import (
    BladeTrailProfile,
    HitstopWeight,
    SkillchainAttribute,
    SkillchainGlyph,
    WeaponClass,
    WeaponskillVfxSystem,
    WsVisualChain,
    blade_trail_for_weapon,
    glyph_color,
    hitstop_for,
    populate_default_glyphs,
    populate_default_ws_library,
)


# ---- enums ----

def test_weapon_class_count_at_least_16():
    assert len(list(WeaponClass)) >= 16


def test_hitstop_weights_four():
    assert {w for w in HitstopWeight} == {
        HitstopWeight.LIGHT, HitstopWeight.MEDIUM,
        HitstopWeight.HEAVY, HitstopWeight.ULTRA,
    }


def test_skillchain_attributes_sixteen():
    assert len(list(SkillchainAttribute)) == 16


# ---- hitstop ----

def test_hitstop_light():
    assert hitstop_for(HitstopWeight.LIGHT) == 40


def test_hitstop_medium():
    assert hitstop_for(HitstopWeight.MEDIUM) == 80


def test_hitstop_heavy():
    assert hitstop_for(HitstopWeight.HEAVY) == 150


def test_hitstop_ultra():
    assert hitstop_for(HitstopWeight.ULTRA) == 250


def test_hitstop_monotonic():
    assert (
        hitstop_for(HitstopWeight.LIGHT) <
        hitstop_for(HitstopWeight.MEDIUM) <
        hitstop_for(HitstopWeight.HEAVY) <
        hitstop_for(HitstopWeight.ULTRA)
    )


# ---- glyph colors ----

def test_glyph_color_liquefaction():
    assert glyph_color(SkillchainAttribute.LIQUEFACTION) == (
        "red_orange"
    )


def test_glyph_color_scission():
    assert glyph_color(SkillchainAttribute.SCISSION) == (
        "neutral_flicker"
    )


def test_glyph_color_impaction():
    assert glyph_color(SkillchainAttribute.IMPACTION) == "yellow"


def test_glyph_color_detonation():
    assert glyph_color(SkillchainAttribute.DETONATION) == "green"


def test_glyph_color_induration():
    assert glyph_color(SkillchainAttribute.INDURATION) == (
        "light_blue"
    )


def test_glyph_color_reverberation():
    assert glyph_color(SkillchainAttribute.REVERBERATION) == (
        "purple"
    )


def test_glyph_color_transfixion():
    assert glyph_color(SkillchainAttribute.TRANSFIXION) == (
        "neon_blue"
    )


def test_glyph_color_compression():
    assert glyph_color(SkillchainAttribute.COMPRESSION) == "violet"


def test_glyph_color_fusion():
    assert glyph_color(SkillchainAttribute.FUSION) == (
        "bright_yellow"
    )


def test_glyph_color_fragmentation():
    assert glyph_color(SkillchainAttribute.FRAGMENTATION) == "cyan"


def test_glyph_color_distortion():
    assert glyph_color(SkillchainAttribute.DISTORTION) == "ice_blue"


def test_glyph_color_gravitation():
    assert glyph_color(SkillchainAttribute.GRAVITATION) == (
        "dark_purple"
    )


def test_glyph_color_light_spectrum():
    assert glyph_color(SkillchainAttribute.LIGHT) == (
        "white_spectrum"
    )


def test_glyph_color_darkness():
    assert glyph_color(SkillchainAttribute.DARKNESS) == (
        "black_with_edge"
    )


def test_glyph_color_crystal_rainbow():
    assert glyph_color(SkillchainAttribute.CRYSTAL) == (
        "rainbow_prism"
    )


def test_glyph_color_umbra_void():
    assert glyph_color(SkillchainAttribute.UMBRA) == "void_black"


# ---- blade trail by weapon ----

def test_blade_trail_sword_anamorphic():
    p = blade_trail_for_weapon(WeaponClass.SWORD)
    assert p.style == "anamorphic"
    assert p.elongation > 1.5


def test_blade_trail_katana_anamorphic():
    p = blade_trail_for_weapon(WeaponClass.KATANA)
    assert p.style == "anamorphic"


def test_blade_trail_axe_broad():
    p = blade_trail_for_weapon(WeaponClass.AXE)
    assert p.style == "broad"
    assert p.thickness > 0.1


def test_blade_trail_great_axe_broad():
    p = blade_trail_for_weapon(WeaponClass.GREAT_AXE)
    assert p.style == "broad"


def test_blade_trail_h2h_minimal():
    p = blade_trail_for_weapon(WeaponClass.H2H)
    assert p.style == "minimal"


def test_blade_trail_bow_minimal():
    p = blade_trail_for_weapon(WeaponClass.BOW)
    assert p.style == "minimal"


# ---- register / resolve ----

def _make_chain(ws_id="vorpal_blade",
                weapon_class=WeaponClass.SWORD):
    return WsVisualChain(
        ws_id=ws_id, weapon_class=weapon_class,
        wind_up_anim_id="anim_x",
        blade_trail_color="silver_blue",
        blade_trail_thickness=0.05,
        impact_flash_vfx_id="impact_flash_med",
        blood_arc_count=4,
        dust_burst_id="dust_kickup",
        shockwave_id="spark_metal",
        screen_shake_intensity=0.2,
        hitstop_ms=80,
        camera_shake_axis="xy",
    )


def test_register_and_resolve():
    s = WeaponskillVfxSystem()
    c = _make_chain()
    s.register_ws("vorpal_blade", c)
    assert s.resolve_ws_vfx("vorpal_blade") is c


def test_register_empty_id_raises():
    s = WeaponskillVfxSystem()
    with pytest.raises(ValueError):
        s.register_ws("", _make_chain())


def test_register_mismatched_id_raises():
    s = WeaponskillVfxSystem()
    with pytest.raises(ValueError):
        s.register_ws("savage_blade", _make_chain())


def test_register_duplicate_raises():
    s = WeaponskillVfxSystem()
    s.register_ws("vorpal_blade", _make_chain())
    with pytest.raises(ValueError):
        s.register_ws("vorpal_blade", _make_chain())


def test_resolve_unknown_raises():
    s = WeaponskillVfxSystem()
    with pytest.raises(KeyError):
        s.resolve_ws_vfx("missing")


# ---- glyphs ----

def test_register_and_get_glyph():
    s = WeaponskillVfxSystem()
    g = SkillchainGlyph(
        attribute=SkillchainAttribute.LIQUEFACTION,
        color="red_orange",
        runic_pattern_id="runic_liquefaction",
        sustain_duration_s=2.5,
        magic_burst_extends_duration_s=1.5,
    )
    s.register_glyph(g)
    assert s.glyph_for(SkillchainAttribute.LIQUEFACTION) is g


def test_glyph_missing_raises():
    s = WeaponskillVfxSystem()
    with pytest.raises(KeyError):
        s.glyph_for(SkillchainAttribute.LIQUEFACTION)


def test_default_glyphs_all_16():
    s = WeaponskillVfxSystem()
    n = populate_default_glyphs(s)
    assert n == 16
    assert s.glyph_count() == 16


def test_default_glyphs_level3_longer_sustain():
    s = WeaponskillVfxSystem()
    populate_default_glyphs(s)
    light = s.glyph_for(SkillchainAttribute.LIGHT)
    liq = s.glyph_for(SkillchainAttribute.LIQUEFACTION)
    assert light.sustain_duration_s > liq.sustain_duration_s


def test_default_glyphs_level4_longest_sustain():
    s = WeaponskillVfxSystem()
    populate_default_glyphs(s)
    crystal = s.glyph_for(SkillchainAttribute.CRYSTAL)
    light = s.glyph_for(SkillchainAttribute.LIGHT)
    assert crystal.sustain_duration_s > light.sustain_duration_s


def test_default_glyphs_mb_extends_duration():
    s = WeaponskillVfxSystem()
    populate_default_glyphs(s)
    g = s.glyph_for(SkillchainAttribute.LIQUEFACTION)
    assert g.magic_burst_extends_duration_s > 0


# ---- chains_for_weapon ----

def test_chains_for_weapon():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    swords = s.chains_for_weapon(WeaponClass.SWORD)
    assert len(swords) >= 3
    assert all(c.weapon_class == WeaponClass.SWORD
               for c in swords)


def test_chains_for_weapon_great_axe():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    axes = s.chains_for_weapon(WeaponClass.GREAT_AXE)
    assert any(c.ws_id == "ukko_fury" for c in axes)


# ---- default ws library ----

def test_default_ws_count_at_least_25():
    s = WeaponskillVfxSystem()
    n = populate_default_ws_library(s)
    assert n >= 25
    assert s.ws_count() == n


def test_default_ws_iconic_present():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    for ws in (
        "vorpal_blade", "savage_blade", "knights_of_round",
        "ukko_fury", "tachi_shoha", "rudras_storm",
        "leaden_salute", "wildfire",
    ):
        assert s.resolve_ws_vfx(ws).ws_id == ws


def test_default_ultra_ws_has_250ms_hitstop():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    assert s.resolve_ws_vfx("knights_of_round").hitstop_ms == 250
    assert s.resolve_ws_vfx("ukko_fury").hitstop_ms == 250


def test_default_light_ws_has_40ms_hitstop():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    # blade_of_jin = LIGHT katana
    assert s.resolve_ws_vfx("blade_of_jin").hitstop_ms == 40


def test_default_heavy_ws_has_150ms_hitstop():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    assert s.resolve_ws_vfx("savage_blade").hitstop_ms == 150


def test_default_ultra_camera_axis_xyz():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    c = s.resolve_ws_vfx("ukko_fury")
    assert c.camera_shake_axis == "xyz"


def test_default_blade_trail_sword_thin():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    sword_c = s.resolve_ws_vfx("vorpal_blade")
    axe_c = s.resolve_ws_vfx("ukko_fury")
    assert sword_c.blade_trail_thickness < (
        axe_c.blade_trail_thickness
    )


def test_default_heavy_blood_count_higher():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    light_c = s.resolve_ws_vfx("blade_of_jin")
    heavy_c = s.resolve_ws_vfx("savage_blade")
    assert heavy_c.blood_arc_count > light_c.blood_arc_count


def test_all_ws_ids_sorted():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    ids = s.all_ws_ids()
    assert list(ids) == sorted(ids)


def test_ws_count_zero_at_init():
    s = WeaponskillVfxSystem()
    assert s.ws_count() == 0


def test_default_heavy_uses_dust_explosion():
    s = WeaponskillVfxSystem()
    populate_default_ws_library(s)
    assert s.resolve_ws_vfx("savage_blade").dust_burst_id == (
        "dust_explosion"
    )
