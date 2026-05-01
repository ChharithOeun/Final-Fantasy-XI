"""Tests for server.cinematic_grammar."""
from __future__ import annotations

import pytest

from server.cinematic_grammar import (
    PPV_PRESETS,
    REACTIONS,
    SHOT_PROFILES,
    TEMPLATES,
    CameraEvent,
    CameraTimeline,
    PostProcessVolume,
    PpvPreset,
    SequencerTemplate,
    ShotType,
    TemplateId,
    clone_for_boss,
    estimate_total_authoring_hours,
    get_preset,
    get_profile,
    get_reaction,
    get_template,
    is_within_band,
    midpoint_duration,
    shots_with_use_case,
    stack_presets,
    total_reaction_seconds,
)


class TestShotGrammar:

    def test_five_shots(self):
        assert len(SHOT_PROFILES) == 5

    def test_establishing_4_to_6s(self):
        # Doc: 'ESTABLISHING (4-6 seconds)'
        p = get_profile(ShotType.ESTABLISHING)
        assert p.min_duration_s == 4.0
        assert p.max_duration_s == 6.0
        assert p.music_behavior == "swell"

    def test_hero_entry_low_angle(self):
        # Doc: 'low-angle (camera at boss waist level looking up)'
        p = get_profile(ShotType.HERO_ENTRY)
        assert p.camera_height == "low_angle"
        assert p.min_duration_s == 3.0
        assert p.max_duration_s == 5.0

    def test_exchange_chest_level_held(self):
        p = get_profile(ShotType.EXCHANGE)
        assert p.camera_height == "chest_level"
        assert p.is_handheld is False

    def test_chaos_handheld(self):
        # Doc: 'Handheld camera tracks combat'
        p = get_profile(ShotType.CHAOS)
        assert p.is_handheld is True

    def test_aftermath_8_to_12s(self):
        # Doc: 'AFTERMATH (8-12 seconds)'
        p = get_profile(ShotType.AFTERMATH)
        assert p.min_duration_s == 8.0
        assert p.max_duration_s == 12.0
        assert p.music_behavior == "fade"

    def test_is_within_band(self):
        assert is_within_band(ShotType.ESTABLISHING, 5.0) is True
        assert is_within_band(ShotType.ESTABLISHING, 7.0) is False
        assert is_within_band(ShotType.AFTERMATH, 10.0) is True

    def test_midpoint(self):
        assert midpoint_duration(ShotType.ESTABLISHING) == 5.0
        assert midpoint_duration(ShotType.AFTERMATH) == 10.0

    def test_use_case_lookup(self):
        ss = shots_with_use_case("tier3_boss_entrance")
        assert ShotType.HERO_ENTRY in ss


class TestTemplates:

    def test_seven_templates(self):
        # Doc: 7 named templates
        assert len(TEMPLATES) == 7

    def test_entrance_establishing_combo(self):
        # Doc: 'establishing + hero-entry combo'
        t = get_template(TemplateId.ENTRANCE_ESTABLISHING)
        assert ShotType.ESTABLISHING in t.shot_sequence
        assert ShotType.HERO_ENTRY in t.shot_sequence

    def test_phase_transition_short(self):
        # Doc: 'short cut for visible armor-drop' ~1s
        t = get_template(TemplateId.PHASE_TRANSITION)
        assert t.total_seconds <= 2.0

    def test_aftermath_lore_multi_line(self):
        # Doc: 'multi-line soliloquy template'
        t = get_template(TemplateId.AFTERMATH_LORE)
        assert t.has_voice_track is True
        assert t.total_seconds >= 12.0

    def test_clone_for_boss(self):
        c = clone_for_boss(
            template_id=TemplateId.ENTRANCE_ESTABLISHING,
            boss_id="maat", voice_clip_id="maat_intro",
            music_cue_id="maat_theme", nation="Bastok",
        )
        assert c.target_actor_id == "maat"
        assert "Bastok" in c.output_asset_path
        assert "maat" in c.output_asset_path.lower()

    def test_clone_unknown_template_raises(self):
        with pytest.raises(ValueError):
            # Pass a string instead of TemplateId enum to bypass enum
            # validation; real code uses the enum.
            clone_for_boss(template_id="ST_FAKE",   # type: ignore
                              boss_id="x",
                              voice_clip_id="x",
                              music_cue_id="x")

    def test_authoring_hours_50_bosses(self):
        # Doc: '~50 cinematics = ~25 hours'
        hours = estimate_total_authoring_hours(50)
        assert hours == 25.0

    def test_authoring_hours_negative_rejected(self):
        with pytest.raises(ValueError):
            estimate_total_authoring_hours(-1)

    def test_template_paths_use_cinematics_root(self):
        for t in TEMPLATES.values():
            assert t.asset_path.startswith("/Game/Demoncore/Cinematics/")


class TestChaosCamera:

    def test_six_events(self):
        # Doc: DEFAULT + 5 reactions = 6 entries
        assert len(REACTIONS) == 6

    def test_skillchain_50ms_whip(self):
        # Doc: '50ms whip toward halo, 200ms pause'
        r = get_reaction(CameraEvent.SKILLCHAIN_DETONATION)
        assert r.pre_motion_seconds == 0.050
        assert r.hold_seconds == 0.200

    def test_mb_landed_100ms_zoom(self):
        # Doc: '100ms zoom-in, 300ms pause'
        r = get_reaction(CameraEvent.MB_LANDED)
        assert r.pre_motion_seconds == 0.100
        assert r.hold_seconds == 0.300

    def test_phase_transition_slowmo(self):
        # Doc: '1-second slow-mo + camera tilt'
        r = get_reaction(CameraEvent.BOSS_PHASE_TRANSITION)
        assert r.use_slowmo is True
        assert r.pre_motion_seconds == 1.0

    def test_intervention_pulse_200ms(self):
        # Doc: '200ms pulse toward the intervening healer'
        r = get_reaction(CameraEvent.INTERVENTION_MB_SUCCEEDED)
        assert r.pre_motion_seconds == 0.200

    def test_player_wipe_tilt_to_sky(self):
        # Doc: '1.5s tilt up to sky as screen fades'
        r = get_reaction(CameraEvent.PLAYER_WIPE)
        assert r.pre_motion_seconds == 1.5
        assert r.fade_target == "sky"

    def test_total_reaction_seconds(self):
        # skillchain_detonation: 0.050 + 0.200 = 0.250
        assert total_reaction_seconds(CameraEvent.SKILLCHAIN_DETONATION) == 0.250
        # default: 0
        assert total_reaction_seconds(CameraEvent.DEFAULT) == 0.0

    def test_timeline_in_window(self):
        tl = CameraTimeline()
        tl.push(at_time=1.0, event=CameraEvent.SKILLCHAIN_DETONATION)
        tl.push(at_time=5.0, event=CameraEvent.MB_LANDED)
        tl.push(at_time=10.0, event=CameraEvent.SKILLCHAIN_DETONATION)
        # Window 0-6: catches events at 1.0 and 5.0
        # = 0.250 (chain) + 0.400 (mb) = 0.650
        total = tl.total_camera_time_in_window(start=0.0, end=6.0)
        assert abs(total - 0.650) < 1e-9

    def test_timeline_event_count(self):
        tl = CameraTimeline()
        tl.push(at_time=1.0, event=CameraEvent.SKILLCHAIN_DETONATION)
        tl.push(at_time=2.0, event=CameraEvent.SKILLCHAIN_DETONATION)
        tl.push(at_time=3.0, event=CameraEvent.MB_LANDED)
        assert tl.event_count(CameraEvent.SKILLCHAIN_DETONATION) == 2
        assert tl.event_count(CameraEvent.MB_LANDED) == 1


class TestPostProcess:

    def test_five_presets(self):
        assert len(PPV_PRESETS) == 5

    def test_maat_tea_set(self):
        # Doc: 'warmth +20%, contrast +10%, slight orange tint'
        p = get_preset(PpvPreset.MAAT_TEA_SET)
        assert p.warmth_delta == 0.20
        assert p.contrast_delta == 0.10
        assert p.color_tint == "orange"

    def test_defeat_cool(self):
        # Doc: 'saturation -30%, slight desaturated cool shift'
        p = get_preset(PpvPreset.DEFEAT_COOL)
        assert p.saturation_delta == -0.30
        assert p.color_tint == "cool"

    def test_stack_additive(self):
        stacked = stack_presets((PpvPreset.MAAT_TEA_SET,
                                       PpvPreset.AFTERMATH_LORE))
        # warmth: 0.20 + 0.05 = 0.25
        assert abs(stacked.warmth_delta - 0.25) < 1e-9
        # contrast: 0.10 + 0.05 = 0.15
        assert abs(stacked.contrast_delta - 0.15) < 1e-9
        # tint of LAST preset wins
        assert stacked.color_tint == "neutral"

    def test_stack_empty(self):
        stacked = stack_presets(())
        assert stacked.warmth_delta == 0.0
        assert stacked.color_tint == "neutral"


class TestComposition:

    def test_maat_full_pipeline_entrance_to_aftermath(self):
        """Doc Maat scenario: warm establishing entrance with PPV +
        ChaosMode reactions + lore aftermath."""
        # Entrance: clone the establishing template for Maat
        entrance = clone_for_boss(
            template_id=TemplateId.ENTRANCE_ESTABLISHING,
            boss_id="maat",
            voice_clip_id="maat_intro_v1",
            music_cue_id="balgas_dais_theme",
            nation="Bastok",
        )
        assert entrance.template_id == TemplateId.ENTRANCE_ESTABLISHING

        # PPV during entrance: Maat tea set
        ppv = get_preset(PpvPreset.MAAT_TEA_SET)
        assert ppv.color_tint == "orange"

        # ChaosMode during fight: a chain detonation + intervention save
        tl = CameraTimeline()
        tl.push(at_time=10.0,
                  event=CameraEvent.SKILLCHAIN_DETONATION)
        tl.push(at_time=11.0,
                  event=CameraEvent.INTERVENTION_MB_SUCCEEDED)
        tl.push(at_time=20.0,
                  event=CameraEvent.BOSS_PHASE_TRANSITION)
        assert tl.event_count(CameraEvent.SKILLCHAIN_DETONATION) == 1
        assert tl.event_count(CameraEvent.INTERVENTION_MB_SUCCEEDED) == 1

        # Aftermath: lore template (Maat is impressed)
        aftermath = clone_for_boss(
            template_id=TemplateId.AFTERMATH_BOSS_IMPRESSED,
            boss_id="maat", voice_clip_id="maat_lightchain_outro",
            music_cue_id="balgas_outro", nation="Bastok",
        )
        assert "boss_impressed" in aftermath.template_id.value.lower() \
            or "BossImpressed" in aftermath.template_id.value

    def test_defeat_pipeline_player_lost(self):
        # Player wipe during Maat: 1.5s tilt to sky + fade
        tl = CameraTimeline()
        tl.push(at_time=45.0, event=CameraEvent.PLAYER_WIPE)
        # Wipe reaction is 1.5s tilt
        assert total_reaction_seconds(CameraEvent.PLAYER_WIPE) == 1.5

        # Followed by defeat-player-lost cinematic with cool PPV
        defeat = clone_for_boss(
            template_id=TemplateId.DEFEAT_PLAYER_LOST,
            boss_id="maat", voice_clip_id="maat_disappointed",
            music_cue_id="defeat_theme", nation="Bastok",
        )
        assert defeat.template_id == TemplateId.DEFEAT_PLAYER_LOST

        ppv = get_preset(PpvPreset.DEFEAT_COOL)
        assert ppv.saturation_delta < 0
