"""Tests for addon_template_registry."""
from __future__ import annotations

from server.addon_template_registry import (
    AddonShape, AddonTemplateRegistry, ApiTarget,
    TemplateManifest, default_registry,
)


def _t(shape=AddonShape.GEARSWAP, name="GearSwap",
       api=ApiTarget.BOTH,
       required=("job", "weapon_sets"),
       optional=()):
    return TemplateManifest(
        shape=shape, name=name, api_target=api,
        required_fields=required, optional_fields=optional,
        description="x",
    )


def test_register_happy():
    r = AddonTemplateRegistry()
    assert r.register(manifest=_t()) is True


def test_register_blank_name_blocked():
    r = AddonTemplateRegistry()
    out = r.register(manifest=_t(name=""))
    assert out is False


def test_register_no_required_blocked():
    r = AddonTemplateRegistry()
    out = r.register(manifest=_t(required=()))
    assert out is False


def test_register_duplicate_blocked():
    r = AddonTemplateRegistry()
    r.register(manifest=_t())
    out = r.register(manifest=_t())
    assert out is False


def test_lookup_returns_manifest():
    r = AddonTemplateRegistry()
    r.register(manifest=_t())
    m = r.lookup(shape=AddonShape.GEARSWAP)
    assert m is not None
    assert m.name == "GearSwap"


def test_lookup_unknown():
    r = AddonTemplateRegistry()
    assert r.lookup(shape=AddonShape.HEALBOT) is None


def test_required_fields():
    r = AddonTemplateRegistry()
    r.register(manifest=_t())
    out = r.required_fields(shape=AddonShape.GEARSWAP)
    assert out == ("job", "weapon_sets")


def test_required_fields_unknown_empty():
    r = AddonTemplateRegistry()
    assert r.required_fields(shape=AddonShape.HEALBOT) == ()


def test_shapes_for_target_windower():
    r = AddonTemplateRegistry()
    r.register(manifest=_t(shape=AddonShape.GEARSWAP, api=ApiTarget.BOTH))
    r.register(manifest=_t(
        shape=AddonShape.SPELLCAST, name="SpellCast",
        api=ApiTarget.WINDOWER, required=("x",),
    ))
    r.register(manifest=_t(
        shape=AddonShape.HEALBOT, name="Healbot",
        api=ApiTarget.ASHITA, required=("x",),
    ))
    out = r.shapes_for_target(target=ApiTarget.WINDOWER)
    # GearSwap (BOTH) + SpellCast (WINDOWER); Healbot excluded
    assert AddonShape.GEARSWAP in out
    assert AddonShape.SPELLCAST in out
    assert AddonShape.HEALBOT not in out


def test_shapes_for_target_both_returns_all():
    r = AddonTemplateRegistry()
    r.register(manifest=_t(shape=AddonShape.GEARSWAP))
    r.register(manifest=_t(
        shape=AddonShape.SPELLCAST, name="SpellCast",
        api=ApiTarget.WINDOWER, required=("x",),
    ))
    out = r.shapes_for_target(target=ApiTarget.BOTH)
    assert len(out) == 2


def test_default_registry_includes_all_canonical_shapes():
    r = default_registry()
    # All 12 canonical shapes from the enum
    assert r.total_registered() == 12


def test_default_registry_gearswap_requires_job_and_weapons():
    r = default_registry()
    fields = r.required_fields(shape=AddonShape.GEARSWAP)
    assert "job" in fields
    assert "weapon_sets" in fields


def test_default_registry_healbot_requires_spell_rules():
    r = default_registry()
    fields = r.required_fields(shape=AddonShape.HEALBOT)
    assert "spell_rules" in fields


def test_default_registry_spellcast_is_windower_only():
    r = default_registry()
    m = r.lookup(shape=AddonShape.SPELLCAST)
    assert m.api_target == ApiTarget.WINDOWER


def test_default_registry_dpsmeter_is_both():
    r = default_registry()
    m = r.lookup(shape=AddonShape.DPSMETER)
    assert m.api_target == ApiTarget.BOTH


def test_default_registry_lists_for_ashita():
    r = default_registry()
    out = r.shapes_for_target(target=ApiTarget.ASHITA)
    # SPELLCAST is windower-only and should NOT appear
    assert AddonShape.SPELLCAST not in out
    # GEARSWAP is BOTH and should appear
    assert AddonShape.GEARSWAP in out


def test_total_registered():
    r = AddonTemplateRegistry()
    r.register(manifest=_t())
    r.register(manifest=_t(
        shape=AddonShape.HEALBOT, name="Healbot",
        required=("x",),
    ))
    assert r.total_registered() == 2


def test_twelve_addon_shapes():
    assert len(list(AddonShape)) == 12


def test_three_api_targets():
    assert len(list(ApiTarget)) == 3
