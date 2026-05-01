"""Tests for server.visible_health — 7-stage HP grammar + reveal skills."""
from __future__ import annotations

import pytest

from server.visible_health import (
    AILMENT_CUES,
    MAGIC_BURST_REVEAL_DAMAGE_THRESHOLD,
    MOOD_DESCRIPTOR,
    REVEAL_SKILLS,
    STAGE_BANDS,
    Ailment,
    CheckResult,
    DamageStage,
    LevelDescriptor,
    MobClass,
    PartyStageSummary,
    Race,
    RevealKind,
    RevealManager,
    RevealScope,
    attack_speed_multiplier,
    audible_cue,
    blood_visibility_multiplier,
    cues_for,
    get_cue,
    get_mob_class_override,
    get_race_override,
    get_skill,
    get_stage_band,
    has_mob_class_override,
    is_reveal_skill,
    is_visible_to_others,
    level_descriptor_for,
    magic_burst_grants_reveal,
    mood_descriptor_for,
    mug_reveal_proc,
    perform_check,
    render_layers_for,
    resolve_stage,
    stage_for_check_descriptor,
    summarize_party,
    visible_ailments_for_observer,
    voice_pitch_multiplier,
)


# ----------------------------------------------------------------------
# damage_stages
# ----------------------------------------------------------------------

class TestDamageStages:

    def test_seven_stages(self):
        # Doc: 7 visible damage stages
        stages = [b.stage for b in STAGE_BANDS]
        assert len(stages) == 7
        assert stages == [
            DamageStage.PRISTINE, DamageStage.SCUFFED,
            DamageStage.BLOODIED, DamageStage.WOUNDED,
            DamageStage.GRIEVOUS, DamageStage.BROKEN,
            DamageStage.DEAD,
        ]

    def test_pristine_band(self):
        # 100-90% HP -> pristine
        assert resolve_stage(100, 100) == DamageStage.PRISTINE
        assert resolve_stage(95, 100) == DamageStage.PRISTINE
        assert resolve_stage(90, 100) == DamageStage.PRISTINE

    def test_scuffed_band(self):
        # 90-70% -> scuffed
        assert resolve_stage(89, 100) == DamageStage.SCUFFED
        assert resolve_stage(70, 100) == DamageStage.SCUFFED

    def test_bloodied_band(self):
        # 70-50%
        assert resolve_stage(69, 100) == DamageStage.BLOODIED
        assert resolve_stage(50, 100) == DamageStage.BLOODIED

    def test_wounded_band(self):
        # 50-30%
        assert resolve_stage(49, 100) == DamageStage.WOUNDED
        assert resolve_stage(30, 100) == DamageStage.WOUNDED

    def test_grievous_band(self):
        # 30-10%
        assert resolve_stage(29, 100) == DamageStage.GRIEVOUS
        assert resolve_stage(10, 100) == DamageStage.GRIEVOUS

    def test_broken_band(self):
        # 10-1%
        assert resolve_stage(9, 100) == DamageStage.BROKEN
        assert resolve_stage(1, 100) == DamageStage.BROKEN

    def test_dead(self):
        assert resolve_stage(0, 100) == DamageStage.DEAD
        assert resolve_stage(-5, 100) == DamageStage.DEAD

    def test_zero_hpmax_dead(self):
        assert resolve_stage(0, 0) == DamageStage.DEAD
        assert resolve_stage(50, 0) == DamageStage.DEAD

    def test_hp_over_max_clamped_pristine(self):
        # Defensive: HP > max should still resolve pristine
        assert resolve_stage(150, 100) == DamageStage.PRISTINE

    def test_attack_speed_decays(self):
        # Pristine 1.0 -> Broken 0.60 -> Dead 0.0
        assert attack_speed_multiplier(DamageStage.PRISTINE) == 1.0
        assert attack_speed_multiplier(DamageStage.WOUNDED) < 1.0
        assert attack_speed_multiplier(DamageStage.BROKEN) < attack_speed_multiplier(DamageStage.WOUNDED)
        assert attack_speed_multiplier(DamageStage.DEAD) == 0.0

    def test_humanoid_cues_additive(self):
        # Doc: 'Cues are additive — at wounded the entity has all of:
        # clean armor scuffed, minor scratches, blood on armor,
        # limp, heavy blood, slower attacks, labored breathing'
        wounded = cues_for(DamageStage.WOUNDED, is_humanoid=True)
        assert "limp" in wounded
        assert "heavy blood" in wounded
        assert "slower attacks" in wounded
        assert "labored breathing" in wounded

    def test_mob_cues_distinct(self):
        # Mobs get different cues than humanoids
        m_wounded = cues_for(DamageStage.WOUNDED, is_humanoid=False)
        h_wounded = cues_for(DamageStage.WOUNDED, is_humanoid=True)
        assert m_wounded != h_wounded
        assert "wing or tail droops" in m_wounded

    def test_audible_cues(self):
        # Doc: 'audible labored breathing'
        assert audible_cue(DamageStage.WOUNDED) == "labored_breathing"
        assert audible_cue(DamageStage.BROKEN) == "shrill_cry"
        assert audible_cue(DamageStage.PRISTINE) == ""

    def test_check_descriptor_buckets(self):
        # Doc: '(unharmed)' / '(slightly hurt)' / '(badly wounded)'
        assert stage_for_check_descriptor(DamageStage.PRISTINE) == "unharmed"
        assert stage_for_check_descriptor(DamageStage.SCUFFED) == "unharmed"
        assert stage_for_check_descriptor(DamageStage.BLOODIED) == "slightly hurt"
        assert stage_for_check_descriptor(DamageStage.WOUNDED) == "slightly hurt"
        assert stage_for_check_descriptor(DamageStage.GRIEVOUS) == "badly wounded"
        assert stage_for_check_descriptor(DamageStage.BROKEN) == "badly wounded"


# ----------------------------------------------------------------------
# status_ailments
# ----------------------------------------------------------------------

class TestStatusAilments:

    def test_seventeen_ailments(self):
        # Doc: 17 ailments named in the table
        assert len(AILMENT_CUES) == 17

    def test_doom_self_only(self):
        # Doc: 'visible ONLY to the afflicted'
        assert is_visible_to_others(Ailment.DOOM) is False

    def test_other_ailments_visible_to_observers(self):
        for a in Ailment:
            if a == Ailment.DOOM:
                continue
            assert is_visible_to_others(a) is True

    def test_visible_ailments_for_observer_filters_doom(self):
        active = [Ailment.POISON, Ailment.DOOM, Ailment.PARALYZE]
        observed = visible_ailments_for_observer(active)
        assert Ailment.POISON in observed
        assert Ailment.PARALYZE in observed
        assert Ailment.DOOM not in observed

    def test_render_layers_stacks_three_ailments(self):
        # Doc: 'three ailments looks genuinely sick — green tinge,
        # pustules, jerky walk all at once'
        layers = render_layers_for([Ailment.POISON, Ailment.PLAGUE,
                                       Ailment.PARALYZE])
        assert "green_sweat_drift" in layers["particles"]
        assert "mp_drain_aspir_visible" in layers["particles"]
        assert "paralyze_arc" in layers["particles"]
        assert "poison_green" in layers["material_tints"]
        assert "pustule_decals" in layers["material_tints"]

    def test_silence_audio_override(self):
        # Doc: 'cast animation plays but NO audio'
        cue = get_cue(Ailment.SILENCE)
        assert cue.audio_override == "mute_cast_sfx"

    def test_disease_ui_gating(self):
        # Doc: "can't eat food (UI gating)"
        cue = get_cue(Ailment.DISEASE)
        assert cue.ui_gating == "cannot_eat_food"

    def test_amnesia_no_special_abilities(self):
        cue = get_cue(Ailment.AMNESIA)
        assert cue.ui_gating == "no_special_abilities"

    def test_petrify_progressive_stone(self):
        cue = get_cue(Ailment.PETRIFY)
        assert "stone" in cue.material_tint
        assert "progressive" in cue.anim_override

    def test_charm_pink_gaze(self):
        cue = get_cue(Ailment.CHARM)
        assert cue.material_tint == "pink_eye_tint"


# ----------------------------------------------------------------------
# race_overrides
# ----------------------------------------------------------------------

class TestRaceOverrides:

    def test_galka_dark_hide_blood(self):
        # Doc: 'blood is harder to see on dark hide'
        assert blood_visibility_multiplier(Race.GALKA, DamageStage.WOUNDED) == 0.5

    def test_tarutaru_blood_more_visible(self):
        # Doc: 'blood is more visible (smaller body, larger relative
        # wounds)'
        assert blood_visibility_multiplier(Race.TARUTARU, DamageStage.WOUNDED) == 1.5

    def test_hume_no_overrides(self):
        # Hume is the reference — no overrides
        assert blood_visibility_multiplier(Race.HUME, DamageStage.WOUNDED) == 1.0
        assert get_race_override(Race.HUME, DamageStage.WOUNDED) is None

    def test_tarutaru_voice_climbs(self):
        # Doc: 'voice gets higher and faster at low HP'
        wounded_pitch = voice_pitch_multiplier(Race.TARUTARU, DamageStage.WOUNDED)
        broken_pitch = voice_pitch_multiplier(Race.TARUTARU, DamageStage.BROKEN)
        assert wounded_pitch > 1.0
        assert broken_pitch > wounded_pitch

    def test_galka_voice_drops(self):
        # Doc: 'breathing becomes a low growl'
        wounded_pitch = voice_pitch_multiplier(Race.GALKA, DamageStage.WOUNDED)
        broken_pitch = voice_pitch_multiplier(Race.GALKA, DamageStage.BROKEN)
        assert wounded_pitch < 1.0
        assert broken_pitch < wounded_pitch

    def test_mithra_ear_flatten_progressive(self):
        # Doc: 'ears flatten progressively'
        scuffed = get_race_override(Race.MITHRA, DamageStage.SCUFFED)
        wounded = get_race_override(Race.MITHRA, DamageStage.WOUNDED)
        broken = get_race_override(Race.MITHRA, DamageStage.BROKEN)
        assert scuffed is not None
        assert wounded is not None
        assert broken is not None
        assert "ears" in scuffed.extra_cues[0].lower()

    def test_mithra_tail_twitch_under_30(self):
        # Doc: 'tail gets twitchy at <30%' — that's GRIEVOUS or BROKEN
        grievous = get_race_override(Race.MITHRA, DamageStage.GRIEVOUS)
        assert grievous is not None
        joined = " ".join(grievous.extra_cues).lower()
        assert "tail" in joined

    def test_elvaan_posture_collapse(self):
        # Doc: 'proud-stance erodes into hunched shoulders by wounded'
        wounded = get_race_override(Race.ELVAAN, DamageStage.WOUNDED)
        assert wounded is not None
        assert any("hunched" in c for c in wounded.extra_cues)


# ----------------------------------------------------------------------
# mob_class_overrides
# ----------------------------------------------------------------------

class TestMobClassOverrides:

    def test_dragon_wing_droop_progression(self):
        # Doc: at WOUNDED wing droops; at BROKEN drags ground
        wounded = get_mob_class_override(MobClass.DRAGON, DamageStage.WOUNDED)
        broken = get_mob_class_override(MobClass.DRAGON, DamageStage.BROKEN)
        assert wounded.geometry_change == "wing_droop"
        assert "drag" in broken.geometry_change

    def test_dragon_fire_breath_slows(self):
        # Doc: 'fire-breath windup is visibly slower'
        wounded = get_mob_class_override(MobClass.DRAGON, DamageStage.WOUNDED)
        broken = get_mob_class_override(MobClass.DRAGON, DamageStage.BROKEN)
        assert wounded.cast_speed_multiplier < 1.0
        assert broken.cast_speed_multiplier < wounded.cast_speed_multiplier

    def test_slime_translucency_loss(self):
        # Doc: 'lose translucency progressively; at broken fully opaque'
        scuffed = get_mob_class_override(MobClass.SLIME, DamageStage.SCUFFED)
        broken = get_mob_class_override(MobClass.SLIME, DamageStage.BROKEN)
        assert scuffed.translucency_multiplier > broken.translucency_multiplier
        assert broken.translucency_multiplier == 0.0

    def test_goblin_drops_sack_at_grievous(self):
        # Doc: 'limp + drop sack of stolen junk by GRIEVOUS'
        gri = get_mob_class_override(MobClass.GOBLIN, DamageStage.GRIEVOUS)
        assert gri.drop_decoration == "goblin_sack"

    def test_quadav_shield_at_wounded_helmet_at_broken(self):
        # Doc: 'shield drops by WOUNDED; helmet falls off at BROKEN'
        w = get_mob_class_override(MobClass.QUADAV, DamageStage.WOUNDED)
        b = get_mob_class_override(MobClass.QUADAV, DamageStage.BROKEN)
        assert w.drop_decoration == "quadav_shield"
        assert b.drop_decoration == "quadav_helmet"

    def test_yagudo_feathers_progressive(self):
        # Doc: 'feathers fall progressively across stages'
        scuffed = get_mob_class_override(MobClass.YAGUDO, DamageStage.SCUFFED)
        broken = get_mob_class_override(MobClass.YAGUDO, DamageStage.BROKEN)
        assert scuffed.feathers_lost_count < broken.feathers_lost_count

    def test_worm_segments_split_from_wounded(self):
        # Doc: 'segments visibly split apart from WOUNDED onward'
        bloodied = get_mob_class_override(MobClass.WORM, DamageStage.BLOODIED)
        wounded = get_mob_class_override(MobClass.WORM, DamageStage.WOUNDED)
        assert bloodied is None
        assert wounded is not None
        assert wounded.geometry_change == "segment_split"

    def test_has_override_helper(self):
        assert has_mob_class_override("dragon", DamageStage.WOUNDED) is True
        assert has_mob_class_override("dragon", DamageStage.PRISTINE) is False
        assert has_mob_class_override("unknown_class", DamageStage.WOUNDED) is False


# ----------------------------------------------------------------------
# reveal_skills + magic burst gating
# ----------------------------------------------------------------------

class TestRevealSkills:

    def test_check_no_numbers(self):
        # Doc: '/check vague descriptor only — no numbers'
        skill = get_skill("check")
        assert skill.kind == RevealKind.DESCRIPTOR_ONLY
        assert skill.cooldown_seconds == 5.0

    def test_scan_5s_25mp(self):
        # Doc: 'Reveals exact HP and MP for 5 seconds. ~25 MP.
        # Cooldown: 30 seconds.'
        skill = get_skill("scan")
        assert skill.kind == RevealKind.HP_AND_MP_NUMERIC
        assert skill.duration_seconds == 5.0
        assert skill.mp_cost == 25
        assert skill.cooldown_seconds == 30.0

    def test_drain_2s_after_land(self):
        skill = get_skill("drain")
        assert skill.kind == RevealKind.HP_NUMERIC
        assert skill.duration_seconds == 2.0

    def test_aspir_2s_mp(self):
        skill = get_skill("aspir")
        assert skill.kind == RevealKind.MP_NUMERIC
        assert skill.duration_seconds == 2.0

    def test_mug_30pct_chance(self):
        # Doc: '30% chance'
        skill = get_skill("mug")
        assert skill.proc_chance == 0.30
        assert skill.duration_seconds == 3.0

    def test_glee_tango_3min_party(self):
        # Doc: '~3 minutes duration. ~30 MP cost.'
        skill = get_skill("glee_tango")
        assert skill.duration_seconds == 180.0
        assert skill.mp_cost == 30
        assert skill.kind == RevealKind.PARTY_HP_AND_MP_NUMERIC
        assert skill.scope == RevealScope.PARTY

    def test_cure_target_peek(self):
        skill = get_skill("cure_target_peek")
        assert skill.duration_seconds == 2.0
        assert skill.kind == RevealKind.HP_NUMERIC

    def test_magic_burst_threshold(self):
        # Doc: '>100 burst damage'
        assert MAGIC_BURST_REVEAL_DAMAGE_THRESHOLD == 100
        assert magic_burst_grants_reveal(150) is True
        assert magic_burst_grants_reveal(100) is False
        assert magic_burst_grants_reveal(99) is False

    def test_pol_command(self):
        skill = get_skill("pol_command")
        assert skill.kind == RevealKind.PARTY_STAGE_SUMMARY

    def test_indicolure_aspir_passive_long(self):
        skill = get_skill("indicolure_aspir")
        assert skill.duration_seconds >= 60.0

    def test_stoneskin_self_only(self):
        skill = get_skill("stoneskin_attacker_read")
        assert skill.scope == RevealScope.SELF
        assert skill.kind == RevealKind.SURFACE_STAGE_LESS_PRECISE

    def test_mug_proc_with_sneak_attack(self):
        # Doc: 'SA-Mug guarantees the reveal'
        always, chance = mug_reveal_proc(sneak_attack_active=True)
        assert always is True
        assert chance == 1.0
        always, chance = mug_reveal_proc(sneak_attack_active=False)
        assert always is False
        assert chance == 0.30

    def test_is_reveal_skill(self):
        assert is_reveal_skill("scan") is True
        assert is_reveal_skill("not_a_skill") is False


# ----------------------------------------------------------------------
# reveal_handle — RevealManager lifecycle
# ----------------------------------------------------------------------

class TestRevealManager:

    def test_grant_returns_handle(self):
        m = RevealManager()
        h = m.grant(observer_id="caster", target_id="goblin",
                      source_skill="scan", now=10.0)
        assert h.target_id == "goblin"
        assert h.expires_at == 15.0
        assert h.kind == RevealKind.HP_AND_MP_NUMERIC

    def test_unknown_skill_rejected(self):
        m = RevealManager()
        with pytest.raises(ValueError):
            m.grant(observer_id="x", target_id="y",
                       source_skill="not_a_skill", now=0.0)

    def test_peek_within_window(self):
        m = RevealManager()
        m.grant(observer_id="caster", target_id="g",
                  source_skill="scan", now=0.0)
        readout = m.peek(observer_id="caster", target_id="g", now=2.0)
        assert readout.hp_visible is True
        assert readout.mp_visible is True
        assert readout.expires_at == 5.0
        assert "scan" in readout.sources

    def test_peek_after_expiry(self):
        m = RevealManager()
        m.grant(observer_id="caster", target_id="g",
                  source_skill="scan", now=0.0)
        readout = m.peek(observer_id="caster", target_id="g", now=10.0)
        assert readout.hp_visible is False
        assert readout.mp_visible is False

    def test_peek_with_no_handle(self):
        m = RevealManager()
        readout = m.peek(observer_id="x", target_id="y", now=0.0)
        assert readout.hp_visible is False
        assert readout.mp_visible is False

    def test_drain_plus_aspir_unions(self):
        # Drain gives HP only; Aspir gives MP only. Both grants give
        # both — the doc's intent.
        m = RevealManager()
        m.grant(observer_id="caster", target_id="g",
                  source_skill="drain", now=0.0)
        m.grant(observer_id="caster", target_id="g",
                  source_skill="aspir", now=0.0)
        readout = m.peek(observer_id="caster", target_id="g", now=1.0)
        assert readout.hp_visible is True
        assert readout.mp_visible is True

    def test_grant_refreshes_same_source(self):
        # Two Scans don't stack — second refreshes
        m = RevealManager()
        m.grant(observer_id="c", target_id="g",
                  source_skill="scan", now=0.0)
        m.grant(observer_id="c", target_id="g",
                  source_skill="scan", now=4.0)
        # At t=8 (only 4s after second grant), scan still active
        readout = m.peek(observer_id="c", target_id="g", now=8.0)
        assert readout.hp_visible is True
        assert readout.expires_at == 9.0   # 4 + 5

    def test_expire_all_collects(self):
        m = RevealManager()
        m.grant(observer_id="c", target_id="g1",
                  source_skill="scan", now=0.0)
        m.grant(observer_id="c", target_id="g2",
                  source_skill="drain", now=0.0)
        # Past both scan (5s) and drain (2s)
        removed = m.expire_all(now=10.0)
        assert removed == 2

    def test_party_scope_via_party_id(self):
        # Glee Tango: register with party_id as observer; any party
        # member peeking with party_id sees the readout.
        m = RevealManager()
        m.grant(observer_id="party_42", target_id="party_member_a",
                  source_skill="glee_tango", now=0.0)
        readout = m.peek(observer_id="party_42",
                            target_id="party_member_a", now=60.0)
        assert readout.hp_visible is True
        assert readout.mp_visible is True

    def test_duration_override(self):
        m = RevealManager()
        h = m.grant(observer_id="c", target_id="g",
                       source_skill="scan", now=0.0,
                       duration_override=1.0)
        # Override 1 second instead of default 5
        assert h.expires_at == 1.0
        readout = m.peek(observer_id="c", target_id="g", now=2.0)
        assert readout.hp_visible is False


# ----------------------------------------------------------------------
# check_descriptor
# ----------------------------------------------------------------------

class TestCheckDescriptor:

    def test_too_weak(self):
        assert level_descriptor_for(50, 40) == LevelDescriptor.TOO_WEAK

    def test_easy_prey(self):
        assert level_descriptor_for(50, 47) == LevelDescriptor.EASY_PREY

    def test_decent_challenge(self):
        assert level_descriptor_for(50, 50) == LevelDescriptor.DECENT_CHALLENGE
        assert level_descriptor_for(50, 49) == LevelDescriptor.DECENT_CHALLENGE

    def test_tough(self):
        assert level_descriptor_for(50, 51) == LevelDescriptor.TOUGH
        assert level_descriptor_for(50, 52) == LevelDescriptor.TOUGH

    def test_very_tough(self):
        assert level_descriptor_for(50, 53) == LevelDescriptor.VERY_TOUGH
        assert level_descriptor_for(50, 54) == LevelDescriptor.VERY_TOUGH

    def test_incredibly_tough(self):
        assert level_descriptor_for(50, 55) == LevelDescriptor.INCREDIBLY_TOUGH
        assert level_descriptor_for(50, 99) == LevelDescriptor.INCREDIBLY_TOUGH

    def test_impossible_to_gauge_override(self):
        # NM/HNM flag override
        result = level_descriptor_for(50, 99, impossible_to_gauge=True)
        assert result == LevelDescriptor.IMPOSSIBLE_TO_GAUGE

    def test_mood_descriptor(self):
        # Doc: '(seems content)' / '(seems agitated)' / '(looks furious)'
        assert mood_descriptor_for("content") == "(seems content)"
        assert mood_descriptor_for("agitated") == "(seems agitated)"
        assert mood_descriptor_for("furious") == "(looks furious)"

    def test_mood_descriptor_unknown_falls_back(self):
        assert mood_descriptor_for("not_a_mood") == "(seems content)"

    def test_perform_check_full(self):
        result = perform_check(
            player_level=50, target_level=52,
            mood_label="furious",
            damage_stage=DamageStage.WOUNDED,
        )
        assert result.level_descriptor == LevelDescriptor.TOUGH
        assert result.mood_descriptor == "(looks furious)"
        assert result.damage_descriptor == "slightly hurt"
        rendered = result.render()
        assert "Tough" in rendered
        assert "furious" in rendered
        assert "slightly hurt" in rendered

    def test_perform_check_for_nm(self):
        result = perform_check(
            player_level=75, target_level=99,
            mood_label="agitated",
            damage_stage=DamageStage.PRISTINE,
            impossible_to_gauge=True,
        )
        assert result.level_descriptor == LevelDescriptor.IMPOSSIBLE_TO_GAUGE
        assert result.damage_descriptor == "unharmed"


# ----------------------------------------------------------------------
# party_summary — /pol command
# ----------------------------------------------------------------------

class TestPartySummary:

    def test_doc_example_render(self):
        # Doc: 'Party: 3 pristine, 1 wounded, 1 broken'
        stages = [
            DamageStage.PRISTINE, DamageStage.PRISTINE,
            DamageStage.PRISTINE, DamageStage.WOUNDED,
            DamageStage.BROKEN,
        ]
        summary = summarize_party(stages)
        rendered = summary.render()
        assert rendered == "Party: 3 pristine, 1 wounded, 1 broken"
        assert summary.party_size == 5

    def test_empty_party(self):
        summary = summarize_party([])
        assert summary.render() == "Party: empty"
        assert summary.party_size == 0

    def test_render_skips_zero_count_stages(self):
        # Only includes stages with non-zero counts
        stages = [DamageStage.PRISTINE, DamageStage.PRISTINE]
        summary = summarize_party(stages)
        assert summary.render() == "Party: 2 pristine"


# ----------------------------------------------------------------------
# Composition: full visible-health pipeline end-to-end
# ----------------------------------------------------------------------

class TestComposition:
    """Worked scenarios from the doc — the BPC pipeline'd-through path."""

    def test_galka_warrior_at_wounded_renders_correctly(self):
        # 40 HP / 100 max -> wounded (50-30% band; 50% itself is BLOODIED)
        stage = resolve_stage(40, 100)
        assert stage == DamageStage.WOUNDED
        # Galka override at WOUNDED: low growl, dark hide blood reduction
        override = get_race_override(Race.GALKA, DamageStage.WOUNDED)
        assert override is not None
        assert any("growl" in c for c in override.extra_cues)
        # Voice pitch dropped
        assert voice_pitch_multiplier(Race.GALKA, DamageStage.WOUNDED) < 1.0
        # Blood visibility halved
        assert blood_visibility_multiplier(Race.GALKA, DamageStage.WOUNDED) == 0.5

    def test_dragon_nm_phase_change_at_broken(self):
        # Dragon at 5% HP -> broken stage; wing tip drags ground
        stage = resolve_stage(5, 100)
        assert stage == DamageStage.BROKEN
        override = get_mob_class_override(MobClass.DRAGON,
                                              DamageStage.BROKEN)
        assert override.geometry_change == "wing_drag_ground"
        # And the fire breath is dramatically slower
        assert override.cast_speed_multiplier == 0.55

    def test_thf_sa_mug_guarantees_reveal(self):
        # Doc: 'SA-Mug guarantees the reveal'
        always, _ = mug_reveal_proc(sneak_attack_active=True)
        assert always is True
        # Once the reveal happens, the manager grants a 3-second window
        m = RevealManager()
        m.grant(observer_id="thf", target_id="goblin",
                  source_skill="mug", now=0.0)
        readout = m.peek(observer_id="thf", target_id="goblin", now=2.0)
        assert readout.hp_visible is True
        # Past 3 seconds, gone
        readout = m.peek(observer_id="thf", target_id="goblin", now=4.0)
        assert readout.hp_visible is False

    def test_magic_burst_party_reveal_after_150_dmg(self):
        # Doc: '>100 burst damage reveals target's HP for 2 seconds
        # to the entire party'
        assert magic_burst_grants_reveal(150) is True
        m = RevealManager()
        m.grant(observer_id="party_7", target_id="boss",
                  source_skill="magic_burst_reveal", now=0.0)
        readout = m.peek(observer_id="party_7", target_id="boss", now=1.0)
        assert readout.hp_visible is True
        assert readout.mp_visible is False

    def test_check_on_furious_wounded_humanoid(self):
        # Player fights a tough goblin at WOUNDED with mood furious
        result = perform_check(
            player_level=15, target_level=16,
            mood_label="furious",
            damage_stage=DamageStage.WOUNDED,
        )
        assert result.level_descriptor == LevelDescriptor.TOUGH
        assert "furious" in result.mood_descriptor
        assert result.damage_descriptor == "slightly hurt"

    def test_three_ailments_layered_render(self):
        # Doc: 'A player with three ailments looks genuinely sick —
        # green tinge, pustules, jerky walk all at once'
        layers = render_layers_for([Ailment.POISON, Ailment.PLAGUE,
                                       Ailment.PARALYZE])
        # green tinge (poison material_tint)
        assert "poison_green" in layers["material_tints"]
        # pustules (plague)
        assert "pustule_decals" in layers["material_tints"]
        # jerky walk (paralyze anim)
        assert "jerky_swings_with_stagger" in layers["anim_overrides"]
