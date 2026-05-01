"""Tests for server.boss_registry — composition over mob_class_library
+ boss_grammar + cinematic_grammar."""
from __future__ import annotations

import pytest

from server.boss_grammar import (
    AftermathBeat,
    BodyLayer,
    BossAttack,
    BossCinematic,
    BossPhase,
    BossRecipe,
    DefeatBeat,
    EntranceBeat,
    IntroBeat,
    MindLayer,
    Repertoire,
)
from server.boss_grammar.repertoire import AttackSize
from server.boss_grammar.phases import PHASE_RULES
from server.boss_registry import (
    BossBuildPlan,
    BossRegistry,
    DeployableBoss,
    build,
    family_for_plan,
    global_registry,
    reset_global_registry,
    validate_deployable,
)
from server.cinematic_grammar import TemplateId, clone_for_boss
from server.mob_class_library import FamilyId


def _full_repertoire(boss_id: str = "goblin_smithy_tutorial") -> Repertoire:
    """Build a doc-conformant repertoire (3+2+1+1=7 attacks)."""
    atks = []
    for i in range(3):
        atks.append(BossAttack(
            attack_id=f"s{i}", label=f"Small {i}",
            size=AttackSize.SMALL, radius_m=8.0, cast_seconds=1.5,
            aoe_shape="circle", element="physical",
            damage_profile="flat"))
    for i in range(2):
        atks.append(BossAttack(
            attack_id=f"m{i}", label=f"Medium {i}",
            size=AttackSize.MEDIUM, radius_m=15.0, cast_seconds=3.0,
            aoe_shape="cone", element="fire",
            damage_profile="falloff"))
    atks.append(BossAttack(
        attack_id="h0", label="Ult", size=AttackSize.HUGE,
        radius_m=25.0, cast_seconds=5.0, aoe_shape="circle",
        element="dark", damage_profile="flat"))
    atks.append(BossAttack(
        attack_id="ws0", label="Sig",
        size=AttackSize.SIGNATURE_WS, radius_m=0.0,
        cast_seconds=2.0, aoe_shape="line", element="none",
        damage_profile="flat", chain_property="distortion"))
    return Repertoire(boss_id=boss_id, attacks=tuple(atks))


def _stub_recipe(boss_id: str, *, hero=False) -> BossRecipe:
    return BossRecipe(
        boss_id=boss_id, label=f"Test {boss_id}",
        body=BodyLayer(skeletal_mesh_id="m",
                          animation_set="warrior",
                          visible_health_archetype="humanoid",
                          mood_axes=("alert",),
                          is_hero_tier=hero),
        repertoire=_full_repertoire(boss_id),
        phase_rules=dict(PHASE_RULES),
        mind=MindLayer(agent_profile_id=f"ag_{boss_id}",
                          has_critic_llm=hero),
        cinematic=BossCinematic(
            entrance=EntranceBeat(),
            intro=IntroBeat(),
            defeat=DefeatBeat(),
            aftermath=AftermathBeat()),
    )


def _stub_plan(*,
                  boss_id: str = "goblin_smithy_tutorial",
                  sub_variant_id: str = "goblin_smithy",
                  nation: str = "Bastok",
                  hero: bool = False
                  ) -> BossBuildPlan:
    return BossBuildPlan(
        boss_id=boss_id,
        label="Goblin Smithy",
        sub_variant_id=sub_variant_id,
        nation=nation,
        recipe=_stub_recipe(boss_id, hero=hero),
        entrance_template=TemplateId.ENTRANCE_DIRECT_REVEAL,
        defeat_template=TemplateId.DEFEAT_PLAYER_WON,
        voice_clip_intro="goblin_smithy_intro",
        voice_clip_defeat="goblin_smithy_defeat",
        music_cue_intro="bastok_mines_theme",
        music_cue_defeat="defeat_theme",
    )


# ----------------------------------------------------------------------
# Builder
# ----------------------------------------------------------------------

class TestBuilder:

    def test_build_basic(self):
        boss = build(_stub_plan())
        assert boss.boss_id == "goblin_smithy_tutorial"
        assert boss.sub_variant_id == "goblin_smithy"
        assert boss.nation == "Bastok"
        # Cinematics targeting the boss
        assert boss.entrance_cinematic.target_actor_id == "goblin_smithy_tutorial"
        assert boss.defeat_cinematic.target_actor_id == "goblin_smithy_tutorial"
        # No aftermath unless requested
        assert boss.optional_aftermath is None

    def test_build_with_aftermath(self):
        plan = _stub_plan()
        plan.aftermath_template = TemplateId.AFTERMATH_BOSS_IMPRESSED
        plan.voice_clip_aftermath = "smithy_outro"
        plan.music_cue_aftermath = "outro_theme"
        boss = build(plan)
        assert boss.optional_aftermath is not None
        assert boss.optional_aftermath.target_actor_id == "goblin_smithy_tutorial"

    def test_build_unknown_sub_variant_raises(self):
        plan = _stub_plan(sub_variant_id="not_in_catalog")
        with pytest.raises(KeyError):
            build(plan)

    def test_family_for_plan(self):
        assert family_for_plan(_stub_plan()) == FamilyId.GOBLIN

    def test_family_resolves_per_sub_variant(self):
        p_quadav = _stub_plan(sub_variant_id="quadav_helmsman",
                                  boss_id="quadav_warlord")
        assert family_for_plan(p_quadav) == FamilyId.QUADAV


# ----------------------------------------------------------------------
# DeployableBoss properties
# ----------------------------------------------------------------------

class TestDeployable:

    def test_family_property(self):
        boss = build(_stub_plan())
        assert boss.family == FamilyId.GOBLIN

    def test_level_band_from_sub_variant(self):
        boss = build(_stub_plan())
        # Goblin Smithy is 10-20 per the catalog
        assert boss.level_band == (10, 20)

    def test_quadav_helmsman_band(self):
        plan = _stub_plan(sub_variant_id="quadav_helmsman",
                              boss_id="quadav_warlord")
        boss = build(plan)
        # Quadav Helmsman is 18-28
        assert boss.level_band == (18, 28)
        assert boss.family == FamilyId.QUADAV


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------

class TestValidation:

    def test_validate_clean(self):
        boss = build(_stub_plan())
        assert validate_deployable(boss) == []

    def test_recipe_boss_id_mismatch_complaint(self):
        # Build the boss, then mutate to inject a mismatch
        boss = build(_stub_plan())
        broken = DeployableBoss(
            boss_id="different_id",
            label=boss.label,
            sub_variant_id=boss.sub_variant_id,
            nation=boss.nation,
            recipe=boss.recipe,                 # still has the OLD boss_id
            entrance_cinematic=boss.entrance_cinematic,
            defeat_cinematic=boss.defeat_cinematic,
        )
        complaints = validate_deployable(broken)
        assert any("differs from deployable boss_id" in c for c in complaints)

    def test_unknown_sub_variant_complaint(self):
        boss = build(_stub_plan())
        broken = DeployableBoss(
            boss_id=boss.boss_id, label=boss.label,
            sub_variant_id="phantom_class",
            nation=boss.nation, recipe=boss.recipe,
            entrance_cinematic=boss.entrance_cinematic,
            defeat_cinematic=boss.defeat_cinematic,
        )
        complaints = validate_deployable(broken)
        assert any("not in catalog" in c for c in complaints)

    def test_recipe_validation_propagates(self):
        # Recipe with too few attacks should bubble up
        plan = _stub_plan()
        plan.recipe.repertoire.attacks  # type: ignore
        # Mutate the recipe to have empty repertoire
        from server.boss_grammar import Repertoire as _R
        broken_recipe = BossRecipe(
            boss_id=plan.recipe.boss_id, label=plan.recipe.label,
            body=plan.recipe.body,
            repertoire=_R(boss_id=plan.recipe.boss_id, attacks=()),
            phase_rules=plan.recipe.phase_rules,
            mind=plan.recipe.mind,
            cinematic=plan.recipe.cinematic,
        )
        plan.recipe = broken_recipe
        boss = build(plan)
        complaints = validate_deployable(boss)
        assert any("requires" in c.lower() or "doc" in c.lower()
                      for c in complaints)


# ----------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------

class TestRegistry:

    def test_register_and_get(self):
        reg = BossRegistry()
        reg.register(build(_stub_plan()))
        assert len(reg) == 1
        assert "goblin_smithy_tutorial" in reg
        boss = reg.get("goblin_smithy_tutorial")
        assert boss is not None

    def test_register_duplicate_raises(self):
        reg = BossRegistry()
        reg.register(build(_stub_plan()))
        with pytest.raises(ValueError):
            reg.register(build(_stub_plan()))

    def test_register_invalid_raises_unless_skipped(self):
        reg = BossRegistry()
        # Make a boss with mismatched cinematic target
        boss = build(_stub_plan())
        # Inject a cinematic targeting a different actor
        from server.cinematic_grammar import clone_for_boss as _clone
        bad_entrance = _clone(template_id=TemplateId.ENTRANCE_DIRECT_REVEAL,
                                  boss_id="someone_else",
                                  voice_clip_id="x", music_cue_id="y",
                                  nation="Bastok")
        broken = DeployableBoss(
            boss_id=boss.boss_id, label=boss.label,
            sub_variant_id=boss.sub_variant_id, nation=boss.nation,
            recipe=boss.recipe,
            entrance_cinematic=bad_entrance,
            defeat_cinematic=boss.defeat_cinematic,
        )
        with pytest.raises(ValueError):
            reg.register(broken)
        # Skip-validation flag bypasses
        reg.register(broken, skip_validation=True)
        assert boss.boss_id in reg

    def test_unregister(self):
        reg = BossRegistry()
        reg.register(build(_stub_plan()))
        assert reg.unregister("goblin_smithy_tutorial") is True
        assert "goblin_smithy_tutorial" not in reg
        assert reg.unregister("never_added") is False

    def test_by_nation(self):
        reg = BossRegistry()
        reg.register(build(_stub_plan(boss_id="b1")))
        reg.register(build(_stub_plan(boss_id="b2",
                                            nation="Sandy",
                                            sub_variant_id="orc_footsoldier")))
        bastok = reg.by_nation("Bastok")
        sandy = reg.by_nation("Sandy")
        assert len(bastok) == 1
        assert len(sandy) == 1

    def test_by_family(self):
        reg = BossRegistry()
        reg.register(build(_stub_plan(boss_id="b1")))
        reg.register(build(_stub_plan(boss_id="b2",
                                            sub_variant_id="quadav_helmsman")))
        goblins = reg.by_family(FamilyId.GOBLIN)
        quadavs = reg.by_family(FamilyId.QUADAV)
        assert len(goblins) == 1
        assert len(quadavs) == 1

    def test_by_level_band(self):
        reg = BossRegistry()
        # Goblin Smithy 10-20
        reg.register(build(_stub_plan(boss_id="b1")))
        # Master Tonberry 80-90
        reg.register(build(_stub_plan(boss_id="b2",
                                            sub_variant_id="master_tonberry")))
        # Lvl 15: only Smithy
        out = reg.by_level_band(level_min=15, level_max=15)
        assert len(out) == 1
        assert out[0].boss_id == "b1"
        # Lvl 85: only Master Tonberry
        out = reg.by_level_band(level_min=85, level_max=85)
        assert len(out) == 1
        assert out[0].boss_id == "b2"

    def test_by_level_band_invalid(self):
        reg = BossRegistry()
        with pytest.raises(ValueError):
            reg.by_level_band(level_min=20, level_max=10)

    def test_hero_tier_filter(self):
        reg = BossRegistry()
        reg.register(build(_stub_plan(boss_id="b1", hero=True)))
        reg.register(build(_stub_plan(boss_id="b2",
                                            sub_variant_id="orc_footsoldier",
                                            hero=False)))
        heroes = reg.hero_tier_bosses()
        assert len(heroes) == 1
        assert heroes[0].boss_id == "b1"

    def test_global_registry_singleton(self):
        reset_global_registry()
        a = global_registry()
        b = global_registry()
        assert a is b
        a.register(build(_stub_plan()))
        assert len(global_registry()) == 1
        reset_global_registry()
        assert len(global_registry()) == 0


# ----------------------------------------------------------------------
# Composition: full doc workflow end-to-end
# ----------------------------------------------------------------------

class TestComposition:

    def test_doc_workflow_smithy_tutorial_boss(self):
        """Doc workflow: pick sub-variant, author recipe, clone
        cinematics, register. Smithy is the lvl-5 boss for the
        TUTORIAL_BASTOK_MINES gate-7 fight."""
        plan = _stub_plan()
        plan.aftermath_template = TemplateId.AFTERMATH_BOSS_IMPRESSED
        plan.voice_clip_aftermath = "cid_smithy_outro"
        plan.music_cue_aftermath = "bastok_outro"
        boss = build(plan)
        complaints = validate_deployable(boss)
        assert complaints == []

        reg = BossRegistry()
        reg.register(boss)
        assert boss.family == FamilyId.GOBLIN
        # Tutorial level band overlaps gate-7 expectation (lvl 5)
        assert boss.level_band[0] <= 10

        # The aftermath cinematic correctly targets the boss
        assert boss.optional_aftermath is not None
        assert boss.optional_aftermath.target_actor_id == "goblin_smithy_tutorial"
        assert boss.optional_aftermath.template_id == TemplateId.AFTERMATH_BOSS_IMPRESSED

    def test_master_tonberry_endgame_boss(self):
        plan = _stub_plan(
            boss_id="master_tonberry_apex",
            sub_variant_id="master_tonberry",
            nation="Sky",
            hero=True,
        )
        plan.entrance_template = TemplateId.ENTRANCE_ESTABLISHING
        plan.aftermath_template = TemplateId.AFTERMATH_LORE
        plan.voice_clip_aftermath = "master_lore"
        plan.music_cue_aftermath = "sky_lore"
        boss = build(plan)
        # Endgame band
        assert boss.level_band[0] >= 80
        assert boss.recipe.body.is_hero_tier is True
