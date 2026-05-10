"""Tests for spell_vfx_resolver."""
from __future__ import annotations

import pytest

from server.spell_vfx_resolver import (
    Element,
    MbOverlay,
    ResolvedSpellVfx,
    SpellTier,
    SpellVfxChain,
    SpellVfxResolver,
    populate_default_library,
)


# ---- enums ----

def test_eight_elements_plus_none():
    elements = {e for e in Element}
    assert Element.FIRE in elements
    assert Element.EARTH in elements
    assert Element.WATER in elements
    assert Element.WIND in elements
    assert Element.ICE in elements
    assert Element.LIGHTNING in elements
    assert Element.LIGHT in elements
    assert Element.DARK in elements
    assert Element.NONE in elements


def test_seven_tiers():
    assert {t for t in SpellTier} == {
        SpellTier.I, SpellTier.II, SpellTier.III, SpellTier.IV,
        SpellTier.V, SpellTier.AM, SpellTier.UTIL,
    }


# ---- register / lookup ----

def _make_chain(spell_id="fire_i", element=Element.FIRE,
                tier=SpellTier.I):
    return SpellVfxChain(
        spell_id=spell_id,
        casting_circle_vfx="casting_circle_white",
        hand_glow_left_vfx="hand_glow_warm",
        hand_glow_right_vfx="hand_glow_warm",
        projectile_or_aoe_vfx="fire_tier_i",
        impact_vfx="impact_flash_med",
        lingering_vfx=None,
        screen_shake_intensity=0.1,
        light_pulse_lux=800.0,
        sound_event_id="sfx_fire_i",
        element=element,
        tier=tier,
    )


def test_register_and_get_chain():
    r = SpellVfxResolver()
    c = _make_chain()
    r.register_spell("fire_i", c)
    assert r.get_chain("fire_i") is c


def test_register_empty_id_raises():
    r = SpellVfxResolver()
    with pytest.raises(ValueError):
        r.register_spell("", _make_chain())


def test_register_mismatched_id_raises():
    r = SpellVfxResolver()
    with pytest.raises(ValueError):
        r.register_spell("water_i", _make_chain())


def test_register_duplicate_raises():
    r = SpellVfxResolver()
    r.register_spell("fire_i", _make_chain())
    with pytest.raises(ValueError):
        r.register_spell("fire_i", _make_chain())


def test_get_chain_missing_raises():
    r = SpellVfxResolver()
    with pytest.raises(KeyError):
        r.get_chain("missing")


# ---- resolve ----

def test_resolve_returns_chain_fields():
    r = SpellVfxResolver()
    r.register_spell("fire_i", _make_chain())
    out = r.resolve("fire_i")
    assert out.spell_id == "fire_i"
    assert out.casting_circle_vfx == "casting_circle_white"
    assert out.element == Element.FIRE


def test_resolve_unknown_raises():
    r = SpellVfxResolver()
    with pytest.raises(KeyError):
        r.resolve("missing")


def test_resolve_tier_ii_scales_up():
    r = SpellVfxResolver()
    r.register_spell("fire_ii", _make_chain(
        spell_id="fire_ii", tier=SpellTier.II,
    ))
    out = r.resolve("fire_ii", element_tier=SpellTier.II)
    # tier II shake mult = 1.4x, light = 1.5x
    assert out.screen_shake_intensity == pytest.approx(0.14)
    assert out.light_pulse_lux == pytest.approx(1200.0)


def test_resolve_tier_v_triggers_cinematic_override():
    r = SpellVfxResolver()
    r.register_spell("fire_v", _make_chain(
        spell_id="fire_v", tier=SpellTier.V,
    ))
    out = r.resolve("fire_v", element_tier=SpellTier.V)
    assert out.cinematic_tier_override is True


def test_resolve_tier_iv_no_override():
    r = SpellVfxResolver()
    r.register_spell("fire_iv", _make_chain(
        spell_id="fire_iv", tier=SpellTier.IV,
    ))
    out = r.resolve("fire_iv", element_tier=SpellTier.IV)
    assert out.cinematic_tier_override is False


def test_resolve_mb_active_adds_halo():
    r = SpellVfxResolver()
    r.register_spell("fire_iii", _make_chain(
        spell_id="fire_iii", tier=SpellTier.III,
    ))
    out = r.resolve(
        "fire_iii", element_tier=SpellTier.III, is_mb_active=True,
    )
    assert out.mb_active is True
    assert out.mb_halo_vfx == "mb_halo_default"


def test_resolve_mb_inactive_no_halo():
    r = SpellVfxResolver()
    r.register_spell("fire_iii", _make_chain(
        spell_id="fire_iii", tier=SpellTier.III,
    ))
    out = r.resolve("fire_iii", is_mb_active=False)
    assert out.mb_active is False
    assert out.mb_halo_vfx is None


def test_resolve_mb_multiplies_shake_by_1p5():
    r = SpellVfxResolver()
    r.register_spell("fire_iii", _make_chain(
        spell_id="fire_iii", tier=SpellTier.III,
    ))
    base = r.resolve("fire_iii", element_tier=SpellTier.III)
    mb = r.resolve(
        "fire_iii", element_tier=SpellTier.III,
        is_mb_active=True,
    )
    assert mb.screen_shake_intensity == pytest.approx(
        base.screen_shake_intensity * 1.5,
    )


def test_resolve_mb_multiplies_light_by_1p5():
    r = SpellVfxResolver()
    r.register_spell("fire_iii", _make_chain(
        spell_id="fire_iii", tier=SpellTier.III,
    ))
    base = r.resolve("fire_iii", element_tier=SpellTier.III)
    mb = r.resolve(
        "fire_iii", element_tier=SpellTier.III,
        is_mb_active=True,
    )
    assert mb.light_pulse_lux == pytest.approx(
        base.light_pulse_lux * 1.5,
    )


def test_resolve_mb_chromatic_aberration_spike():
    r = SpellVfxResolver()
    r.register_spell("fire_i", _make_chain())
    base = r.resolve("fire_i")
    mb = r.resolve("fire_i", is_mb_active=True)
    assert base.chromatic_aberration_spike == 0.0
    assert mb.chromatic_aberration_spike > 0.0


# ---- chains_for_element / tier ----

def test_chains_for_element():
    r = SpellVfxResolver()
    populate_default_library(r)
    fires = r.chains_for_element(Element.FIRE)
    # 5 elemental tiers + flare AM = 6
    assert len(fires) >= 5
    assert all(c.element == Element.FIRE for c in fires)


def test_chains_for_tier_i():
    r = SpellVfxResolver()
    populate_default_library(r)
    tier_i = r.chains_for_tier(SpellTier.I)
    # 8 elements at tier I
    assert len(tier_i) == 8


def test_chains_for_tier_am():
    r = SpellVfxResolver()
    populate_default_library(r)
    am = r.chains_for_tier(SpellTier.AM)
    # 8 AM spells
    assert len(am) == 8


# ---- mb_overlay ----

def test_mb_overlay_default():
    r = SpellVfxResolver()
    ov = r.mb_overlay()
    assert ov.shake_multiplier == pytest.approx(1.5)
    assert ov.light_multiplier == pytest.approx(1.5)
    assert ov.halo_vfx == "mb_halo_default"


def test_set_mb_overlay():
    r = SpellVfxResolver()
    custom = MbOverlay(
        halo_vfx="mb_halo_custom",
        shake_multiplier=2.0, light_multiplier=2.0,
        chromatic_aberration_spike=0.5,
    )
    r.set_mb_overlay(custom)
    assert r.mb_overlay().halo_vfx == "mb_halo_custom"


def test_set_mb_overlay_applied_in_resolve():
    r = SpellVfxResolver()
    r.register_spell("fire_i", _make_chain())
    custom = MbOverlay(
        halo_vfx="mb_halo_custom",
        shake_multiplier=2.0, light_multiplier=2.0,
        chromatic_aberration_spike=0.5,
    )
    r.set_mb_overlay(custom)
    out = r.resolve("fire_i", is_mb_active=True)
    assert out.mb_halo_vfx == "mb_halo_custom"
    assert out.chromatic_aberration_spike == pytest.approx(0.5)


# ---- ancient_magic_chain ----

def test_ancient_magic_chain():
    r = SpellVfxResolver()
    populate_default_library(r)
    out = r.ancient_magic_chain("flare")
    assert out.tier == SpellTier.AM
    assert out.cinematic_tier_override is True


def test_ancient_magic_on_non_am_raises():
    r = SpellVfxResolver()
    populate_default_library(r)
    with pytest.raises(ValueError):
        r.ancient_magic_chain("fire_i")


def test_ancient_magic_unknown_raises():
    r = SpellVfxResolver()
    with pytest.raises(KeyError):
        r.ancient_magic_chain("missing")


# ---- default library ----

def test_default_library_at_least_40_spells():
    r = SpellVfxResolver()
    n = populate_default_library(r)
    assert n >= 40
    assert r.chain_count() == n


def test_default_library_covers_8_elements_5_tiers():
    r = SpellVfxResolver()
    populate_default_library(r)
    for elem in (
        Element.FIRE, Element.EARTH, Element.WATER, Element.WIND,
        Element.ICE, Element.LIGHTNING, Element.LIGHT, Element.DARK,
    ):
        for tier in (SpellTier.I, SpellTier.II, SpellTier.III,
                     SpellTier.IV, SpellTier.V):
            chains = [
                c for c in r.chains_for_element(elem)
                if c.tier == tier
            ]
            assert len(chains) == 1, (
                f"missing {elem.value} {tier.value}"
            )


def test_default_library_has_cure_i_to_v():
    r = SpellVfxResolver()
    populate_default_library(r)
    for sid in ("cure_i", "cure_ii", "cure_iii",
                "cure_iv", "cure_v"):
        assert r.get_chain(sid) is not None


def test_default_library_has_raise_i_to_iii():
    r = SpellVfxResolver()
    populate_default_library(r)
    for sid in ("raise_i", "raise_ii", "raise_iii"):
        assert r.get_chain(sid) is not None


def test_default_library_has_status_set():
    r = SpellVfxResolver()
    populate_default_library(r)
    for sid in ("sleep", "silence", "slow", "haste",
                "protect", "shell", "drain", "aspir"):
        assert r.get_chain(sid) is not None


def test_default_library_fire_iii_has_lingering_ember():
    r = SpellVfxResolver()
    populate_default_library(r)
    c = r.get_chain("fire_iii")
    assert c.lingering_vfx == "ember_drift"


def test_default_library_water_iii_no_lingering():
    r = SpellVfxResolver()
    populate_default_library(r)
    c = r.get_chain("water_iii")
    assert c.lingering_vfx is None


def test_default_library_dark_uses_dark_circle():
    r = SpellVfxResolver()
    populate_default_library(r)
    c = r.get_chain("sleep")
    assert c.casting_circle_vfx == "casting_circle_dark"


def test_default_library_ancient_magic_set():
    r = SpellVfxResolver()
    populate_default_library(r)
    for sid in ("flare", "freeze", "burst", "flood",
                "quake", "tornado", "holy_ii", "comet"):
        c = r.get_chain(sid)
        assert c.tier == SpellTier.AM


def test_default_library_flare_lingers_with_ember_storm():
    r = SpellVfxResolver()
    populate_default_library(r)
    c = r.get_chain("flare")
    assert c.lingering_vfx == "ember_storm"


def test_default_library_haste_is_neutral_element():
    r = SpellVfxResolver()
    populate_default_library(r)
    c = r.get_chain("haste")
    assert c.element == Element.NONE


def test_chain_count_zero_at_init():
    r = SpellVfxResolver()
    assert r.chain_count() == 0
