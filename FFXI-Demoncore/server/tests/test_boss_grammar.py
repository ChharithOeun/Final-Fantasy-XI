"""Tests for server.boss_grammar — 5-layer recipe DSL."""
from __future__ import annotations

import pytest

from server.boss_grammar import (
    AOE_SIZE_BANDS,
    BOSS_PHASE_ORDER,
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
    classify_attack_size,
    phase_for_hp_fraction,
    validate_recipe,
    validate_repertoire,
)
from server.boss_grammar.repertoire import (
    MAX_REPERTOIRE_SIZE,
    MIN_REPERTOIRE_SIZE,
    AttackSize,
)
from server.boss_grammar.phases import get_rule


# ----------------------------------------------------------------------
# Repertoire
# ----------------------------------------------------------------------

class TestRepertoire:

    def test_size_bands(self):
        assert AOE_SIZE_BANDS[AttackSize.SMALL].typical_radius_m == 8.0
        assert AOE_SIZE_BANDS[AttackSize.MEDIUM].typical_radius_m == 15.0
        assert AOE_SIZE_BANDS[AttackSize.HUGE].typical_radius_m == 25.0

    def test_classify_small(self):
        assert classify_attack_size(radius_m=8.0,
                                          cast_seconds=1.5) == AttackSize.SMALL

    def test_classify_medium(self):
        assert classify_attack_size(radius_m=15.0,
                                          cast_seconds=3.0) == AttackSize.MEDIUM

    def test_classify_huge(self):
        assert classify_attack_size(radius_m=25.0,
                                          cast_seconds=5.0) == AttackSize.HUGE

    def test_classify_signature_ws(self):
        assert classify_attack_size(radius_m=0.0,
                                          cast_seconds=2.0,
                                          has_chain_property=True) == AttackSize.SIGNATURE_WS

    def test_min_max_repertoire(self):
        assert MIN_REPERTOIRE_SIZE == 7
        assert MAX_REPERTOIRE_SIZE == 12

    def _full_attacks(self) -> tuple[BossAttack, ...]:
        atks: list[BossAttack] = []
        # 3 small
        for i in range(3):
            atks.append(BossAttack(
                attack_id=f"s{i}", label=f"Small {i}",
                size=AttackSize.SMALL, radius_m=8.0,
                cast_seconds=1.5, aoe_shape="circle",
                element="physical", damage_profile="flat"))
        # 2 medium
        for i in range(2):
            atks.append(BossAttack(
                attack_id=f"m{i}", label=f"Medium {i}",
                size=AttackSize.MEDIUM, radius_m=15.0,
                cast_seconds=3.0, aoe_shape="cone",
                element="fire", damage_profile="falloff"))
        # 1 huge
        atks.append(BossAttack(
            attack_id="h0", label="Ultimate",
            size=AttackSize.HUGE, radius_m=25.0,
            cast_seconds=5.0, aoe_shape="circle",
            element="dark", damage_profile="flat"))
        # 1 signature
        atks.append(BossAttack(
            attack_id="ws0", label="Signature",
            size=AttackSize.SIGNATURE_WS, radius_m=0.0,
            cast_seconds=2.0, aoe_shape="line",
            element="none", damage_profile="flat",
            chain_property="distortion"))
        return tuple(atks)

    def test_validate_clean(self):
        rep = Repertoire(boss_id="hero", attacks=self._full_attacks())
        assert validate_repertoire(rep) == []

    def test_validate_too_few_complaints(self):
        rep = Repertoire(boss_id="dud",
                            attacks=self._full_attacks()[:5])
        complaints = validate_repertoire(rep)
        assert any("requires" in c for c in complaints)

    def test_validate_duplicate_id(self):
        atks = list(self._full_attacks())
        atks.append(BossAttack(
            attack_id="s0",   # duplicate
            label="Dupe", size=AttackSize.SMALL, radius_m=8.0,
            cast_seconds=1.5, aoe_shape="circle",
            element="physical", damage_profile="flat"))
        rep = Repertoire(boss_id="dupe", attacks=tuple(atks))
        complaints = validate_repertoire(rep)
        assert any("duplicate" in c for c in complaints)

    def test_repertoire_by_size(self):
        rep = Repertoire(boss_id="x", attacks=self._full_attacks())
        assert len(rep.by_size(AttackSize.SMALL)) == 3
        assert len(rep.by_size(AttackSize.MEDIUM)) == 2
        assert len(rep.by_size(AttackSize.HUGE)) == 1
        assert len(rep.by_size(AttackSize.SIGNATURE_WS)) == 1


# ----------------------------------------------------------------------
# Phases
# ----------------------------------------------------------------------

class TestPhases:

    def test_six_phases(self):
        assert len(BOSS_PHASE_ORDER) == 6

    def test_phase_for_hp_pristine(self):
        assert phase_for_hp_fraction(1.0) == BossPhase.PRISTINE
        assert phase_for_hp_fraction(0.95) == BossPhase.PRISTINE

    def test_phase_for_hp_scuffed(self):
        assert phase_for_hp_fraction(0.85) == BossPhase.SCUFFED

    def test_phase_for_hp_bloodied(self):
        assert phase_for_hp_fraction(0.60) == BossPhase.BLOODIED

    def test_phase_for_hp_wounded(self):
        assert phase_for_hp_fraction(0.40) == BossPhase.WOUNDED

    def test_phase_for_hp_grievous(self):
        assert phase_for_hp_fraction(0.20) == BossPhase.GRIEVOUS

    def test_phase_for_hp_broken(self):
        assert phase_for_hp_fraction(0.05) == BossPhase.BROKEN
        assert phase_for_hp_fraction(0.0) == BossPhase.BROKEN

    def test_bloodied_drops_helmet(self):
        # Doc: 'drops one piece of armor (visible — say the helmet
        # falls off)'
        rule = get_rule(BossPhase.BLOODIED)
        assert rule.drops_armor_piece == "helmet"

    def test_wounded_enrages(self):
        rule = get_rule(BossPhase.WOUNDED)
        assert rule.is_enraged is True

    def test_grievous_panic(self):
        # Doc: 'panic moves; arena-wide AOE every 5 seconds'
        rule = get_rule(BossPhase.GRIEVOUS)
        assert rule.is_panic is True
        # 12 AOEs/min == 1 every 5s
        assert rule.extra_aoe_per_minute == 12.0

    def test_castspeed_increases_with_phase(self):
        prev = 0.0
        for phase in BOSS_PHASE_ORDER:
            rule = get_rule(phase)
            assert rule.castspeed_multiplier >= prev
            prev = rule.castspeed_multiplier


# ----------------------------------------------------------------------
# Cinematic
# ----------------------------------------------------------------------

class TestCinematic:

    def test_default_durations(self):
        # Doc: ~10s entrance, ~8s intro, ~8s defeat, ~5s aftermath
        cin = BossCinematic(
            entrance=EntranceBeat(),
            intro=IntroBeat(),
            defeat=DefeatBeat(),
            aftermath=AftermathBeat(),
        )
        assert cin.entrance.duration_seconds == 10.0
        assert cin.intro.duration_seconds == 8.0
        assert cin.defeat.duration_seconds == 8.0
        assert cin.aftermath.duration_seconds == 5.0
        assert cin.total_seconds == 31.0


# ----------------------------------------------------------------------
# BossRecipe — full 5-layer composition
# ----------------------------------------------------------------------

class TestBossRecipe:

    def _full_recipe(self, *, hero=True) -> BossRecipe:
        atks: list[BossAttack] = []
        for i in range(3):
            atks.append(BossAttack(
                attack_id=f"s{i}", label=f"Small {i}",
                size=AttackSize.SMALL, radius_m=8.0,
                cast_seconds=1.5, aoe_shape="circle",
                element="physical", damage_profile="flat"))
        for i in range(2):
            atks.append(BossAttack(
                attack_id=f"m{i}", label=f"Medium {i}",
                size=AttackSize.MEDIUM, radius_m=15.0,
                cast_seconds=3.0, aoe_shape="cone",
                element="fire", damage_profile="falloff"))
        atks.append(BossAttack(
            attack_id="h0", label="Ultimate",
            size=AttackSize.HUGE, radius_m=25.0,
            cast_seconds=5.0, aoe_shape="circle",
            element="dark", damage_profile="flat"))
        atks.append(BossAttack(
            attack_id="ws0", label="Sig",
            size=AttackSize.SIGNATURE_WS, radius_m=0.0,
            cast_seconds=2.0, aoe_shape="line",
            element="none", damage_profile="flat",
            chain_property="distortion"))
        rep = Repertoire(boss_id="boss_x", attacks=tuple(atks))
        from server.boss_grammar.phases import PHASE_RULES
        return BossRecipe(
            boss_id="boss_x", label="Test Boss",
            body=BodyLayer(skeletal_mesh_id="m1",
                              animation_set="warrior",
                              visible_health_archetype="humanoid",
                              mood_axes=("furious", "alert"),
                              is_hero_tier=hero),
            repertoire=rep,
            phase_rules=dict(PHASE_RULES),
            mind=MindLayer(agent_profile_id="ag_x",
                              has_critic_llm=hero),
            cinematic=BossCinematic(
                entrance=EntranceBeat(),
                intro=IntroBeat(voice_line="Don't disappoint me."),
                defeat=DefeatBeat(voice_line="...you've earned this."),
                aftermath=AftermathBeat()),
        )

    def test_validate_clean_recipe(self):
        recipe = self._full_recipe(hero=True)
        assert validate_recipe(recipe) == []

    def test_hero_tier_must_have_critic(self):
        # Hero body but no critic LLM -> complaint
        recipe = self._full_recipe(hero=True)
        # mutate copy
        recipe = BossRecipe(
            boss_id=recipe.boss_id, label=recipe.label,
            body=recipe.body, repertoire=recipe.repertoire,
            phase_rules=recipe.phase_rules,
            mind=MindLayer(agent_profile_id="x", has_critic_llm=False),
            cinematic=recipe.cinematic,
        )
        complaints = validate_recipe(recipe)
        assert any("critic LLM" in c for c in complaints)

    def test_reskin_boss_doesnt_need_critic(self):
        recipe = self._full_recipe(hero=False)
        # is_hero_tier=False AND has_critic_llm=False is fine
        complaints = validate_recipe(recipe)
        assert all("critic LLM" not in c for c in complaints)

    def test_missing_phase_complaint(self):
        recipe = self._full_recipe(hero=True)
        broken_phases = dict(recipe.phase_rules)
        del broken_phases[BossPhase.WOUNDED]
        recipe = BossRecipe(
            boss_id=recipe.boss_id, label=recipe.label,
            body=recipe.body, repertoire=recipe.repertoire,
            phase_rules=broken_phases,
            mind=recipe.mind, cinematic=recipe.cinematic,
        )
        complaints = validate_recipe(recipe)
        assert any("missing phase" in c for c in complaints)
