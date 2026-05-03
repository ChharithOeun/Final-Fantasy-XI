"""Tests for the Su recipe-slip catalog."""
from __future__ import annotations

from server.su_progression import (
    SU_LADDER_TIERS,
    SuArchetype,
    SuKind,
    SuSlot,
)
from server.su_recipe_slips import (
    COALITION_VENDOR_TIERS,
    SLIP_BY_ID,
    SU_SLIP_CATALOG,
    all_material_ids,
    materials_for,
    slip_for,
    slips_from_source,
)


def test_catalog_is_non_empty():
    assert len(SU_SLIP_CATALOG) > 0
    assert len(SLIP_BY_ID) == len(SU_SLIP_CATALOG)


def test_catalog_covers_every_tier_for_a_slot_archetype():
    slips = [
        s for s in SU_SLIP_CATALOG
        if s.slot == SuSlot.HEAD and s.archetype == SuArchetype.CASTER
    ]
    tiers = {s.target_tier for s in slips}
    # Every upgrade rung from T1 to T11 represented
    assert tiers == set(range(1, SU_LADDER_TIERS))


def test_slip_for_lookup_works():
    s = slip_for(
        slot=SuSlot.BODY, archetype=SuArchetype.MELEE, tier=5,
    )
    assert s is not None
    assert s.target_tier == 5
    assert s.target_ilvl == 145


def test_slip_for_unknown_returns_none():
    assert slip_for(
        slot=SuSlot.HEAD, archetype=SuArchetype.CASTER, tier=999,
    ) is None


def test_t1_t2_are_vendor_purchasable():
    assert COALITION_VENDOR_TIERS == frozenset({1, 2})
    s_t1 = slip_for(
        slot=SuSlot.HEAD, archetype=SuArchetype.CASTER, tier=1,
    )
    s_t8 = slip_for(
        slot=SuSlot.HEAD, archetype=SuArchetype.CASTER, tier=8,
    )
    assert s_t1.is_vendor_purchasable
    assert not s_t8.is_vendor_purchasable


def test_weapon_slips_have_lower_drop_rate_than_armor():
    """Canonical 'Su weapon mats are rarer' rule."""
    for tier in range(1, SU_LADDER_TIERS):
        armor = slip_for(
            slot=SuSlot.HEAD, archetype=SuArchetype.MELEE, tier=tier,
        )
        weapon = slip_for(
            slot=SuSlot.MAIN_HAND_MELEE,
            archetype=SuArchetype.MELEE, tier=tier,
        )
        assert weapon.drop_rate_pct < armor.drop_rate_pct, (
            f"weapon should drop rarer at tier {tier} "
            f"(armor={armor.drop_rate_pct}, weapon={weapon.drop_rate_pct})"
        )


def test_weapon_materials_have_extra_entries():
    """Weapons add 2 extra mats — alloy + oil."""
    armor_slip = slip_for(
        slot=SuSlot.HEAD, archetype=SuArchetype.MELEE, tier=5,
    )
    weapon_slip = slip_for(
        slot=SuSlot.MAIN_HAND_MELEE,
        archetype=SuArchetype.MELEE, tier=5,
    )
    armor_mats = materials_for(slip_id=armor_slip.slip_id)
    weapon_mats = materials_for(slip_id=weapon_slip.slip_id)
    armor_ids = {m.material_id for m in armor_mats.materials}
    weapon_ids = {m.material_id for m in weapon_mats.materials}
    assert "weapon_grade_alloy" in weapon_ids
    assert "weapon_grade_oil" in weapon_ids
    assert "weapon_grade_alloy" not in armor_ids


def test_all_material_ids_includes_core_and_flavor():
    ids = all_material_ids()
    # Core mats from every tier
    assert "shadow_dust" in ids
    assert "godsblood_essence" in ids
    # Flavor mats per archetype
    for a in SuArchetype:
        assert f"essence_{a.value}" in ids


def test_every_material_is_direct_drop():
    """Anti-monopoly: every material on every slip must drop
    directly somewhere — none crafted-only."""
    for slip in SU_SLIP_CATALOG:
        mats = materials_for(slip_id=slip.slip_id)
        for m in mats.materials:
            assert m.is_direct_drop, (
                f"{slip.slip_id}: {m.material_id} is not a "
                f"direct drop — anti-monopoly violation"
            )


def test_slips_from_source():
    slips = slips_from_source("sortie_boss_low")
    assert len(slips) > 0
    for s in slips:
        assert s.drop_source_id == "sortie_boss_low"


def test_higher_tier_slips_demand_more_core_mats():
    s1 = slip_for(
        slot=SuSlot.HEAD, archetype=SuArchetype.CASTER, tier=1,
    )
    s11 = slip_for(
        slot=SuSlot.HEAD, archetype=SuArchetype.CASTER, tier=11,
    )
    m1 = materials_for(slip_id=s1.slip_id)
    m11 = materials_for(slip_id=s11.slip_id)
    # The first material is the "core mat" — count scales with tier
    assert m1.materials[0].count == 1
    assert m11.materials[0].count == 11


def test_materials_for_unknown_slip():
    assert materials_for(slip_id="not_a_slip_id") is None


def test_t11_is_godsblood_capstone():
    s = slip_for(
        slot=SuSlot.BODY, archetype=SuArchetype.CASTER, tier=11,
    )
    mats = materials_for(slip_id=s.slip_id)
    assert any(
        m.material_id == "godsblood_essence" for m in mats.materials
    )


def test_all_archetypes_represented():
    archetypes = {s.archetype for s in SU_SLIP_CATALOG}
    assert archetypes == set(SuArchetype)


def test_weapon_kinds_only_appear_for_weapon_slots():
    for slip in SU_SLIP_CATALOG:
        if slip.kind == SuKind.WEAPON:
            assert slip.slot in {
                SuSlot.MAIN_HAND_MELEE, SuSlot.MAIN_HAND_MAGIC,
                SuSlot.RANGED, SuSlot.AMMO,
            }
