"""Tests for destructible_props."""
from __future__ import annotations

import pytest

from server.destructible_props import (
    ArmorClass,
    BARREL_EXPLOSION_DAMAGE,
    DestructibleProp,
    DestructiblePropSystem,
    Element,
    FracturePattern,
    FractureEvent,
)


# ---- enums ----

def test_armor_classes_seven():
    assert {a for a in ArmorClass} == {
        ArmorClass.WOOD, ArmorClass.MASONRY, ArmorClass.GLASS,
        ArmorClass.METAL, ArmorClass.CRATE_LIGHT,
        ArmorClass.BARREL_OIL, ArmorClass.CLOTH_AWNING,
    }


def test_fracture_patterns_five():
    assert {p for p in FracturePattern} == {
        FracturePattern.CRACK, FracturePattern.SHATTER,
        FracturePattern.EXPLODE, FracturePattern.TOPPLE,
        FracturePattern.BURN,
    }


# ---- register / hp defaults ----

def test_register_wood_default_hp_50():
    s = DestructiblePropSystem()
    p = s.register_prop("crate1", "src_crate1", ArmorClass.WOOD)
    assert p.hp == 50


def test_register_masonry_default_hp_200():
    s = DestructiblePropSystem()
    p = s.register_prop("wall1", "src_wall1", ArmorClass.MASONRY)
    assert p.hp == 200


def test_register_glass_default_hp_10():
    s = DestructiblePropSystem()
    p = s.register_prop("win1", "src_win1", ArmorClass.GLASS)
    assert p.hp == 10


def test_register_metal_default_hp_500():
    s = DestructiblePropSystem()
    p = s.register_prop("anvil1", "src_anvil1", ArmorClass.METAL)
    assert p.hp == 500


def test_register_crate_light_default_hp_15():
    s = DestructiblePropSystem()
    p = s.register_prop("c1", "src_c1", ArmorClass.CRATE_LIGHT)
    assert p.hp == 15


def test_register_barrel_oil_default_hp_8():
    s = DestructiblePropSystem()
    p = s.register_prop("oil1", "src_oil1", ArmorClass.BARREL_OIL)
    assert p.hp == 8


def test_register_cloth_awning_default_hp_5():
    s = DestructiblePropSystem()
    p = s.register_prop("aw1", "src_aw1", ArmorClass.CLOTH_AWNING)
    assert p.hp == 5


def test_register_custom_hp():
    s = DestructiblePropSystem()
    p = s.register_prop("c", "src_c", ArmorClass.WOOD, custom_hp=200)
    assert p.hp == 200


def test_register_zero_custom_hp_raises():
    s = DestructiblePropSystem()
    with pytest.raises(ValueError):
        s.register_prop("c", "src_c", ArmorClass.WOOD, custom_hp=0)


def test_register_empty_id_raises():
    s = DestructiblePropSystem()
    with pytest.raises(ValueError):
        s.register_prop("", "src", ArmorClass.WOOD)


def test_register_duplicate_raises():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    with pytest.raises(ValueError):
        s.register_prop("c", "src", ArmorClass.WOOD)


def test_register_default_pattern_oil_explode():
    s = DestructiblePropSystem()
    p = s.register_prop("oil", "src_oil", ArmorClass.BARREL_OIL)
    assert p.fracture_pattern == FracturePattern.EXPLODE


def test_register_default_pattern_glass_shatter():
    s = DestructiblePropSystem()
    p = s.register_prop("g", "src_g", ArmorClass.GLASS)
    assert p.fracture_pattern == FracturePattern.SHATTER


def test_register_default_replaces_with():
    s = DestructiblePropSystem()
    p = s.register_prop("c", "src_crate", ArmorClass.WOOD)
    assert p.replaces_with == "src_crate_broken"


def test_register_explicit_replaces_with():
    s = DestructiblePropSystem()
    p = s.register_prop(
        "c", "src", ArmorClass.WOOD,
        replaces_with="custom_broken",
    )
    assert p.replaces_with == "custom_broken"


# ---- get / hp ----

def test_get_returns_prop():
    s = DestructiblePropSystem()
    p = s.register_prop("c", "src", ArmorClass.WOOD)
    assert s.get("c") is p


def test_get_unknown_raises():
    s = DestructiblePropSystem()
    with pytest.raises(KeyError):
        s.get("missing")


def test_hp_initial_matches_register():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD, custom_hp=100)
    assert s.hp("c") == 100


def test_hp_unknown_raises():
    s = DestructiblePropSystem()
    with pytest.raises(KeyError):
        s.hp("missing")


# ---- damage ----

def test_damage_partial_keeps_alive():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    cascade = s.damage("c", 30)
    assert cascade == []
    assert s.hp("c") == 20
    assert not s.is_destroyed("c")


def test_damage_full_destroys():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    cascade = s.damage("c", 50)
    assert cascade == ["c"]
    assert s.is_destroyed("c")
    assert s.hp("c") == 0


def test_damage_overkill_destroys():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    cascade = s.damage("c", 999)
    assert cascade == ["c"]


def test_damage_already_destroyed_returns_empty():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    s.damage("c", 50)
    cascade = s.damage("c", 999)
    assert cascade == []


def test_damage_zero_raises():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    with pytest.raises(ValueError):
        s.damage("c", 0)


def test_damage_negative_raises():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    with pytest.raises(ValueError):
        s.damage("c", -5)


def test_damage_unknown_raises():
    s = DestructiblePropSystem()
    with pytest.raises(KeyError):
        s.damage("missing", 5)


def test_damage_glass_with_fire_shatters():
    s = DestructiblePropSystem()
    s.register_prop("win", "src", ArmorClass.GLASS)
    # 1 fire damage shatters glass instantly.
    cascade = s.damage("win", 1, element=Element.FIRE)
    assert cascade == ["win"]


def test_damage_cloth_takes_double_fire():
    s = DestructiblePropSystem()
    s.register_prop(
        "aw", "src", ArmorClass.CLOTH_AWNING, custom_hp=10,
    )
    # 5 fire damage on cloth = 10 effective, exactly destroys.
    cascade = s.damage("aw", 5, element=Element.FIRE)
    assert cascade == ["aw"]


def test_damage_cloth_partial_with_fire():
    s = DestructiblePropSystem()
    s.register_prop(
        "aw", "src", ArmorClass.CLOTH_AWNING, custom_hp=20,
    )
    # 5 fire = 10 effective; cloth still has 10 hp.
    cascade = s.damage("aw", 5, element=Element.FIRE)
    assert cascade == []
    assert s.hp("aw") == 10


# ---- explosion cascade ----

def test_oil_barrel_explosion_chains_neighbors():
    s = DestructiblePropSystem()
    s.register_prop("oil", "src_oil", ArmorClass.BARREL_OIL)
    s.register_prop("c1", "src_c1", ArmorClass.CRATE_LIGHT)
    s.register_prop("c2", "src_c2", ArmorClass.CRATE_LIGHT)
    s.link_neighbors("oil", "c1")
    s.link_neighbors("oil", "c2")
    cascade = s.damage("oil", 8)
    # oil destroys, then both crates take 30 fire dmg
    # (CRATE_LIGHT hp=15) and break.
    assert "oil" in cascade
    assert "c1" in cascade
    assert "c2" in cascade


def test_oil_barrel_does_not_chain_to_metal():
    s = DestructiblePropSystem()
    s.register_prop("oil", "src", ArmorClass.BARREL_OIL)
    s.register_prop("anvil", "src_a", ArmorClass.METAL)
    s.link_neighbors("oil", "anvil")
    cascade = s.damage("oil", 8)
    assert "oil" in cascade
    assert "anvil" not in cascade
    assert not s.is_destroyed("anvil")


def test_oil_barrel_chains_cloth_with_2x_multiplier():
    s = DestructiblePropSystem()
    s.register_prop("oil", "src", ArmorClass.BARREL_OIL)
    s.register_prop("aw", "src_aw", ArmorClass.CLOTH_AWNING)
    s.link_neighbors("oil", "aw")
    cascade = s.damage("oil", 8)
    assert "oil" in cascade
    assert "aw" in cascade  # 30 fire dmg * 2 = 60 vs 5 hp


def test_oil_chain_to_oil_chains_again():
    s = DestructiblePropSystem()
    s.register_prop("oil1", "src_o1", ArmorClass.BARREL_OIL)
    s.register_prop("oil2", "src_o2", ArmorClass.BARREL_OIL)
    s.register_prop("c", "src_c", ArmorClass.CRATE_LIGHT)
    s.link_neighbors("oil1", "oil2")
    s.link_neighbors("oil2", "c")
    cascade = s.damage("oil1", 8)
    assert "oil1" in cascade
    assert "oil2" in cascade
    assert "c" in cascade


def test_link_unknown_raises():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    with pytest.raises(KeyError):
        s.link_neighbors("c", "missing")


def test_link_self_raises():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    with pytest.raises(ValueError):
        s.link_neighbors("c", "c")


# ---- fracture event ----

def test_fracture_event_basic():
    s = DestructiblePropSystem()
    s.register_prop("c", "src_crate", ArmorClass.WOOD)
    ev = s.fracture_event("c")
    assert isinstance(ev, FractureEvent)
    assert ev.prop_id == "c"
    assert ev.pattern == FracturePattern.CRACK
    assert ev.replaces_with == "src_crate_broken"


def test_fracture_event_oil_explode():
    s = DestructiblePropSystem()
    s.register_prop("oil", "src", ArmorClass.BARREL_OIL)
    ev = s.fracture_event("oil")
    assert ev.pattern == FracturePattern.EXPLODE


# ---- props_in_zone ----

def test_props_in_zone_filtered():
    s = DestructiblePropSystem()
    s.register_prop("a", "src", ArmorClass.WOOD,
                    zone_id="bastok_markets")
    s.register_prop("b", "src", ArmorClass.WOOD,
                    zone_id="bastok_markets")
    s.register_prop("c", "src", ArmorClass.WOOD,
                    zone_id="north_gustaberg")
    out = s.props_in_zone("bastok_markets")
    assert {p.prop_id for p in out} == {"a", "b"}


def test_props_in_zone_empty_for_unknown():
    s = DestructiblePropSystem()
    assert s.props_in_zone("nowhere") == ()


# ---- can_be_destroyed_by ----

def test_dagger_cannot_destroy_masonry():
    s = DestructiblePropSystem()
    s.register_prop("w", "src", ArmorClass.MASONRY)
    assert not s.can_be_destroyed_by("w", "dagger")


def test_great_axe_destroys_anything():
    s = DestructiblePropSystem()
    s.register_prop("w", "src", ArmorClass.METAL)
    assert s.can_be_destroyed_by("w", "great_axe")


def test_h2h_destroys_wood():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    assert s.can_be_destroyed_by("c", "h2h")


def test_h2h_cannot_destroy_metal():
    s = DestructiblePropSystem()
    s.register_prop("a", "src", ArmorClass.METAL)
    assert not s.can_be_destroyed_by("a", "h2h")


def test_unknown_weapon_returns_false():
    s = DestructiblePropSystem()
    s.register_prop("c", "src", ArmorClass.WOOD)
    assert not s.can_be_destroyed_by("c", "noodle_arm")


def test_can_be_destroyed_unknown_prop_raises():
    s = DestructiblePropSystem()
    with pytest.raises(KeyError):
        s.can_be_destroyed_by("missing", "sword")


# ---- misc ----

def test_prop_count_zero_at_init():
    s = DestructiblePropSystem()
    assert s.prop_count() == 0


def test_all_prop_ids_sorted():
    s = DestructiblePropSystem()
    s.register_prop("zzz", "src", ArmorClass.WOOD)
    s.register_prop("aaa", "src", ArmorClass.WOOD)
    assert s.all_prop_ids() == ("aaa", "zzz")


def test_barrel_explosion_damage_constant_present():
    assert BARREL_EXPLOSION_DAMAGE > 0
