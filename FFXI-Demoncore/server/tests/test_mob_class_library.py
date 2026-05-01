"""Tests for server.mob_class_library."""
from __future__ import annotations

import pytest

from server.mob_class_library import (
    FAMILIES,
    SUB_VARIANTS,
    Element,
    FamilyId,
    MobRole,
    all_families,
    boss_grade_variants,
    encounter_composition,
    families_strong_vs,
    families_weak_to,
    families_with_affinity,
    family_count,
    get_family,
    get_sub_variant,
    healers_for_family,
    sub_variant_count,
    variants_in_family,
    variants_in_level_band,
    variants_with_role,
)


class TestFamilies:

    def test_thirteen_families(self):
        assert family_count() == 13

    def test_quadav_lightning_aligned(self):
        # Doc: 'Affinity: lightning. Weak to: water. Strong vs: wind.'
        f = get_family(FamilyId.QUADAV)
        assert f.affinity == Element.LIGHTNING
        assert Element.WATER in f.weak_to
        assert Element.WIND in f.strong_vs

    def test_yagudo_water_aligned(self):
        f = get_family(FamilyId.YAGUDO)
        assert f.affinity == Element.WATER
        assert Element.LIGHTNING in f.weak_to
        assert Element.FIRE in f.strong_vs

    def test_orc_fire_aligned(self):
        f = get_family(FamilyId.ORC)
        assert f.affinity == Element.FIRE
        assert Element.ICE in f.weak_to

    def test_goblin_earth_aligned(self):
        f = get_family(FamilyId.GOBLIN)
        assert f.affinity == Element.EARTH
        assert Element.WIND in f.weak_to
        assert Element.LIGHTNING in f.strong_vs

    def test_tonberry_dark_aligned(self):
        # Doc: 'Affinity: dark. Weak to: light. Strong vs: nothing'
        f = get_family(FamilyId.TONBERRY)
        assert f.affinity == Element.DARK
        assert Element.LIGHT in f.weak_to
        assert f.strong_vs == ()

    def test_naga_water_aligned(self):
        f = get_family(FamilyId.NAGA)
        assert f.affinity == Element.WATER
        assert Element.LIGHTNING in f.weak_to

    def test_demon_resists_all_except_light(self):
        # Doc: 'resists_all flag — only Light cuts through'
        f = get_family(FamilyId.DEMON)
        assert Element.LIGHT in f.weak_to
        # Most elements in strong_vs (resists_all)
        assert len(f.strong_vs) >= 6

    def test_dragon_variable_affinity(self):
        # Doc: 'Variable, per-individual'
        f = get_family(FamilyId.DRAGON)
        assert f.affinity == Element.VARIABLE

    def test_slime_variable_affinity(self):
        # Doc: 'Element rotates per zone; caller supplies at spawn'
        f = get_family(FamilyId.SLIME)
        assert f.affinity == Element.VARIABLE


class TestReverseLookups:

    def test_families_weak_to_lightning(self):
        # Yagudo, Naga, Sahagin (water-aligned) are weak to lightning
        # per doc. Quadav is itself lightning-aligned, NOT weak to it.
        weak = families_weak_to(Element.LIGHTNING)
        ids = {f.family for f in weak}
        assert FamilyId.YAGUDO in ids
        assert FamilyId.NAGA in ids
        assert FamilyId.SAHAGIN in ids
        assert FamilyId.QUADAV not in ids

    def test_families_strong_vs_fire(self):
        # Yagudo + Sahagin strong vs fire
        strong = families_strong_vs(Element.FIRE)
        ids = {f.family for f in strong}
        assert FamilyId.YAGUDO in ids
        assert FamilyId.SAHAGIN in ids

    def test_families_with_dark_affinity(self):
        # Tonberry + Skeleton + Demon
        dark = families_with_affinity(Element.DARK)
        ids = {f.family for f in dark}
        assert FamilyId.TONBERRY in ids
        assert FamilyId.SKELETON in ids
        assert FamilyId.DEMON in ids

    def test_families_with_water_affinity(self):
        # Yagudo + Naga + Sahagin
        water = families_with_affinity(Element.WATER)
        ids = {f.family for f in water}
        assert FamilyId.YAGUDO in ids
        assert FamilyId.NAGA in ids
        assert FamilyId.SAHAGIN in ids


class TestSubVariants:

    def test_at_least_30_variants(self):
        # Doc: 4-6 sub-variants per family for the named ones
        assert sub_variant_count() >= 30

    def test_quadav_six_variants(self):
        v = variants_in_family(FamilyId.QUADAV)
        assert len(v) == 6

    def test_yagudo_five_variants(self):
        v = variants_in_family(FamilyId.YAGUDO)
        assert len(v) == 5

    def test_get_sub_variant_lookup(self):
        sv = get_sub_variant("quadav_helmsman")
        assert sv.family == FamilyId.QUADAV
        assert sv.role == MobRole.LEADER
        assert sv.signature_skill == "scaled_mail"

    def test_goblin_smithy_is_tutorial_boss(self):
        # Ties to TUTORIAL_BASTOK_MINES
        sv = get_sub_variant("goblin_smithy")
        assert sv.role == MobRole.MID_BOSS
        assert sv.signature_skill == "hammer_slam"
        assert sv.skill_aoe_shape == "cone"

    def test_naga_renja_sprint_nin(self):
        # Per the s1 scenario test
        sv = get_sub_variant("naga_renja")
        assert sv.role == MobRole.SPRINT_NIN
        assert sv.signature_skill == "hyoton_ichi"

    def test_master_tonberry_endgame(self):
        sv = get_sub_variant("master_tonberry")
        assert sv.role == MobRole.ENDGAME_NM
        assert sv.level_min >= 80
        assert sv.skill_aoe_shape == "arena_wide"


class TestQueries:

    def test_level_band_overlap(self):
        # Lvl 12 should hit Quadav Footsoldier (8-15) AND Roundshield
        # (12-20) AND others
        v = variants_in_level_band(level_min=12, level_max=12)
        ids = {sv.sub_variant_id for sv in v}
        assert "quadav_footsoldier" in ids
        assert "quadav_roundshield" in ids

    def test_level_band_invalid_rejected(self):
        with pytest.raises(ValueError):
            variants_in_level_band(level_min=20, level_max=10)

    def test_variants_with_role_healer(self):
        # Quadav Healer + Yagudo Cleric are HEALER role
        healers = variants_with_role(MobRole.HEALER)
        ids = {sv.sub_variant_id for sv in healers}
        assert "quadav_healer" in ids
        assert "yagudo_cleric" in ids

    def test_healers_for_family(self):
        h = healers_for_family(FamilyId.QUADAV)
        assert len(h) == 1
        assert h[0].sub_variant_id == "quadav_healer"

    def test_boss_grade_variants(self):
        bgvs = boss_grade_variants()
        # Includes mid bosses + NMs + endgame
        labels = {sv.sub_variant_id for sv in bgvs}
        assert "yagudo_avatar" in labels      # mid_boss
        assert "tonberry_nm" in labels        # NM
        assert "master_tonberry" in labels    # endgame_nm

    def test_encounter_composition_lvl_25(self):
        # Lvl 25 zones: Quadav Helmsman (18-28) + Yagudo Initiate (15-25)
        # + Quadav Healer (25-35) etc.
        comp = encounter_composition(level=25, size=4)
        assert len(comp) <= 4
        ids = {sv.sub_variant_id for sv in comp}
        # Should include a healer per the bias
        healers_in_comp = [sv for sv in comp if sv.role == MobRole.HEALER]
        if healers_for_family(FamilyId.QUADAV):
            # If a healer was eligible, the bias should include one
            assert len(healers_in_comp) >= 1 or not any(
                sv.role == MobRole.HEALER
                for sv in variants_in_level_band(
                    level_min=25, level_max=25))

    def test_encounter_composition_size_zero_rejected(self):
        with pytest.raises(ValueError):
            encounter_composition(level=20, size=0)

    def test_encounter_composition_no_pool(self):
        # Lvl 200 has no eligible variants
        comp = encounter_composition(level=200, size=4)
        assert comp == ()


class TestComposition:
    """Worked scenarios using the catalog."""

    def test_chain_planning_quadav_pull(self):
        """Doc-mob-symmetry scenario: a player chain on a Quadav
        Helmsman would need a Quadav Healer adjacent for the
        intervention block per INTERVENTION_MB.md."""
        helmsman = get_sub_variant("quadav_helmsman")
        healer = get_sub_variant("quadav_healer")
        assert helmsman.family == healer.family
        assert healer.role == MobRole.HEALER

    def test_lightning_party_planning(self):
        """A water-element party going into a Quadav-heavy zone
        should hit hard (water -> lightning weak)."""
        targets = families_weak_to(Element.WATER)
        # Wait — we want what's weak to LIGHTNING (the player element
        # in this scenario is lightning) — actually what's weak to
        # lightning is what the lightning player hits hard
        lightning_targets = families_weak_to(Element.LIGHTNING)
        names = {f.family for f in lightning_targets}
        # Naga + Sahagin are water-aligned, weak to lightning
        assert FamilyId.NAGA in names
        assert FamilyId.SAHAGIN in names

    def test_master_tonberry_arena_wipe_recipe(self):
        """Doc: Master Tonberry's Everyone's Grudge is wipe-tier.
        The catalog records it as arena_wide."""
        sv = get_sub_variant("master_tonberry")
        assert sv.skill_aoe_shape == "arena_wide"
        assert sv.signature_skill == "everyones_grudge"
