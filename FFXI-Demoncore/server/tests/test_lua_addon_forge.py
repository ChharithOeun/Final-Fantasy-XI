"""Tests for lua_addon_forge."""
from __future__ import annotations

from server.addon_intent_spec import (
    AddonIntentSpec, GearSetEntry, OffenseMode, SpellRule,
)
from server.addon_template_registry import AddonShape
from server.lua_addon_forge import (
    ForgeError, ForgeOutput, LuaAddonForge,
)


def _spec():
    return AddonIntentSpec(
        addon_id="rdm_chharith", job="RDM",
        weapon_sets={
            "Death Blossom": GearSetEntry(
                set_name="Death Blossom",
                slot_to_item={
                    "main": "Murgleis", "sub": "Sakpata's Sword",
                },
            ),
            "Savage Blade": GearSetEntry(
                set_name="Savage Blade",
                slot_to_item={
                    "main": "Naegling", "sub": "Machaera +2",
                },
            ),
        },
        offense_modes=[
            OffenseMode(mode_name="TP", weaponskill_target="Death Blossom"),
            OffenseMode(mode_name="DT", weaponskill_target="Death Blossom"),
        ],
        idle_set=GearSetEntry(
            set_name="idle",
            slot_to_item={
                "ammo": "Staunch Tathlum +1",
                "body": "Lethargy Sayon +2",
            },
        ),
        food_item="Tropical Crepe",
        lockstyle_pallet="20",
        macro_book="3", macro_set="1",
        default_offense_mode="DT",
    )


def test_render_gearswap_happy():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert isinstance(out, ForgeOutput)
    assert out.success is True
    assert out.shape == AddonShape.GEARSWAP


def test_render_includes_addon_id_header():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert "rdm_chharith" in out.lua_source


def test_render_includes_lockstyle():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert 'LockStylePallet = "20"' in out.lua_source


def test_render_includes_food():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert 'Food = "Tropical Crepe"' in out.lua_source


def test_render_includes_offense_modes():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert "OffenseMode:options" in out.lua_source
    assert '"TP"' in out.lua_source
    assert '"DT"' in out.lua_source


def test_render_includes_default_offense_mode():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert 'OffenseMode:set("DT")' in out.lua_source


def test_render_emits_weapon_sets():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert "Murgleis" in out.lua_source
    assert "Naegling" in out.lua_source


def test_render_emits_idle_set():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert "Idle" in out.lua_source
    assert "Staunch Tathlum +1" in out.lua_source


def test_render_quotes_escaped():
    """Items with quotes/backslashes are properly escaped."""
    s = _spec()
    s.weapon_sets["Test"] = GearSetEntry(
        set_name="Test",
        slot_to_item={"main": 'Item "with quotes"'},
    )
    f = LuaAddonForge()
    out = f.render(spec=s, shape=AddonShape.GEARSWAP)
    # Properly escaped — \" inside the lua string
    assert '\\"with quotes\\"' in out.lua_source


def test_render_invalid_spec_returns_error():
    s = _spec()
    s.addon_id = ""
    f = LuaAddonForge()
    out = f.render(spec=s, shape=AddonShape.GEARSWAP)
    assert isinstance(out, ForgeError)
    assert out.success is False
    assert out.reason == "spec_invalid"


def test_render_unknown_shape_returns_error():
    """Pick an enum value the default registry doesn't know about
    by stripping the registry."""
    f = LuaAddonForge()
    # Remove all registered manifests to simulate unknown shape
    f._registry._manifests.clear()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert isinstance(out, ForgeError)
    assert out.reason == "unknown_shape"


def test_render_non_gearswap_uses_skeleton():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.DPSMETER)
    assert isinstance(out, ForgeOutput)
    assert "on_load" in out.lua_source
    assert "on_event" in out.lua_source


def test_render_custom_renderer_used():
    f = LuaAddonForge()
    f.register_renderer(
        shape=AddonShape.HEALBOT,
        fn=lambda spec: "-- custom healbot renderer\n",
    )
    s = _spec()
    s.spell_rules.append(SpellRule(
        spell_id="cure_iv", auto_cast_when="hp_low",
        target="lowest_hp_party",
    ))
    out = f.render(spec=s, shape=AddonShape.HEALBOT)
    assert "custom healbot renderer" in out.lua_source


def test_register_renderer_duplicate_blocked():
    f = LuaAddonForge()
    f.register_renderer(
        shape=AddonShape.HEALBOT, fn=lambda s: "",
    )
    out = f.register_renderer(
        shape=AddonShape.HEALBOT, fn=lambda s: "x",
    )
    assert out is False


def test_render_deterministic():
    """Same spec → byte-identical output."""
    f1 = LuaAddonForge()
    f2 = LuaAddonForge()
    out1 = f1.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    out2 = f2.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    assert out1.lua_source == out2.lua_source


def test_render_gearswap_direct_helper():
    f = LuaAddonForge()
    src = f.render_gearswap(spec=_spec())
    assert "Murgleis" in src


def test_line_count_matches_source():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.GEARSWAP)
    # line_count is source.count("\n") + 1
    assert out.line_count == out.lua_source.count("\n") + 1


def test_minimal_spec_no_optional_fields():
    s = AddonIntentSpec(
        addon_id="x", job="WHM",
        weapon_sets={
            "Default": GearSetEntry(
                set_name="Default",
                slot_to_item={"main": "Yagrush"},
            ),
        },
    )
    f = LuaAddonForge()
    out = f.render(spec=s, shape=AddonShape.GEARSWAP)
    assert isinstance(out, ForgeOutput)
    assert "Yagrush" in out.lua_source


def test_render_skeleton_carries_addon_id():
    f = LuaAddonForge()
    out = f.render(spec=_spec(), shape=AddonShape.DPSMETER)
    assert "rdm_chharith" in out.lua_source


def test_no_food_no_food_line():
    s = _spec()
    s.food_item = ""
    f = LuaAddonForge()
    out = f.render(spec=s, shape=AddonShape.GEARSWAP)
    assert "Food = " not in out.lua_source
