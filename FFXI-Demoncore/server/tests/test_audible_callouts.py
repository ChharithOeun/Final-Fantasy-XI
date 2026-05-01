"""Tests for server.audible_callouts."""
from __future__ import annotations

import pytest

from server.audible_callouts import (
    CALLOUT_TEMPLATES,
    GRUNT_VOCAB,
    MOOD_VOICE_PROFILES,
    CalloutKind,
    CalloutPipeline,
    GruntCategory,
    SpatialAudio,
    apply_mood_tone,
    chain_close_callout,
    emit_callout,
    grunt_for_event,
    light_or_darkness_callout,
    mb_ailment_callout,
    mb_callout,
    profile_for_mood,
    setup_callout,
    skillchain_open_callout,
)


class TestGrammar:

    def test_skillchain_open(self):
        assert skillchain_open_callout() == "Skillchain open!"

    def test_chain_close(self):
        assert chain_close_callout("Fusion") == "Closing — Fusion!"
        assert chain_close_callout("Distortion") == "Closing — Distortion!"

    def test_lv3_light_uppercase(self):
        assert light_or_darkness_callout("light") == "LIGHT!"
        assert light_or_darkness_callout("Darkness") == "DARKNESS!"

    def test_lv3_only_light_or_darkness(self):
        with pytest.raises(ValueError):
            light_or_darkness_callout("Fusion")

    def test_mb_damage(self):
        assert mb_callout("Fire") == "Magic Burst — Fire!"
        assert mb_callout("Blizzard IV") == "Magic Burst — Blizzard IV!"

    def test_mb_ailment(self):
        # Doc: 'Magic Burst — Slow!' / 'Magic Burst — Bind!'
        assert mb_ailment_callout("Slow") == "Magic Burst — Slow!"
        assert mb_ailment_callout("Bind") == "Magic Burst — Bind!"

    def test_setup(self):
        assert setup_callout() == "Setting up — close on me!"

    def test_template_table_complete(self):
        for k in CalloutKind:
            assert k in CALLOUT_TEMPLATES


class TestGrunts:

    def test_eight_categories(self):
        assert len(GRUNT_VOCAB) == 8

    def test_exertion_on_swing(self):
        assert grunt_for_event("auto_attack_swing") == GruntCategory.EXERTION

    def test_pain_on_hp_decrease(self):
        assert grunt_for_event("hp_decrease") == GruntCategory.PAIN

    def test_low_hp_gasp_on_broken_stage(self):
        assert grunt_for_event("stage_broken") == GruntCategory.LOW_HP_GASP

    def test_death_rattle(self):
        assert grunt_for_event("death") == GruntCategory.DEATH_RATTLE

    def test_relief_on_heal(self):
        assert grunt_for_event("heal_received") == GruntCategory.RELIEF

    def test_frustration_on_interrupt(self):
        assert grunt_for_event("cast_interrupted") == GruntCategory.FRUSTRATION
        assert grunt_for_event("intervention_failed") == GruntCategory.FRUSTRATION

    def test_effort_on_two_hour(self):
        assert grunt_for_event("two_hour_ability") == GruntCategory.EFFORT

    def test_unknown_event_returns_none(self):
        assert grunt_for_event("not_a_real_event") is None


class TestMoodVoice:

    def test_eight_mood_profiles(self):
        assert len(MOOD_VOICE_PROFILES) == 8

    def test_content_baseline(self):
        p = profile_for_mood("content")
        assert p.pitch_multiplier == 1.0
        assert p.pace_multiplier == 1.0

    def test_furious_fastest(self):
        p = profile_for_mood("furious")
        assert p.pace_multiplier > 1.0
        assert p.intensity_multiplier > 1.0

    def test_weary_slowest(self):
        p = profile_for_mood("weary")
        assert p.pace_multiplier < 1.0
        assert p.intensity_multiplier < 1.0

    def test_fearful_higher_pitch_lower_intensity(self):
        p = profile_for_mood("fearful")
        assert p.pitch_multiplier > 1.0
        assert p.intensity_multiplier < 1.0

    def test_unknown_mood_falls_back_to_content(self):
        p = profile_for_mood("not_a_mood")
        assert p.mood == "content"

    def test_apply_mood_tone(self):
        result = apply_mood_tone(line="Skillchain open!",
                                       mood_label="furious")
        assert result["line"] == "Skillchain open!"
        assert result["mood"] == "furious"
        assert result["pace_multiplier"] > 1.0
        assert result["intensity_multiplier"] > 1.0


class TestPipeline:

    def test_emit_and_collect(self):
        p = CalloutPipeline()
        spk = SpatialAudio(actor_id="war",
                              position=(10.0, 0.0, 0.0))
        p.emit(line="Skillchain open!", speaker=spk,
                  mood_label="alert", now=10.0)
        assert len(p) == 1
        em = p.emissions()[0]
        assert em.line == "Skillchain open!"
        assert em.speaker.actor_id == "war"
        assert em.synthesizer_input["mood"] == "alert"
        assert em.synthesizer_input["spatial"] == [10.0, 0.0, 0.0]

    def test_emissions_in_window(self):
        p = CalloutPipeline()
        spk = SpatialAudio(actor_id="war", position=(0.0, 0.0, 0.0))
        p.emit(line="A", speaker=spk, mood_label="content", now=1.0)
        p.emit(line="B", speaker=spk, mood_label="content", now=5.0)
        p.emit(line="C", speaker=spk, mood_label="content", now=10.0)
        lines = p.lines_in_window(start=2.0, end=8.0)
        assert lines == ["B"]

    def test_emissions_by_speaker(self):
        p = CalloutPipeline()
        war = SpatialAudio(actor_id="war", position=(0.0, 0.0, 0.0))
        whm = SpatialAudio(actor_id="whm", position=(5.0, 0.0, 0.0))
        p.emit(line="open!", speaker=war, mood_label="alert", now=1.0)
        p.emit(line="cure!", speaker=whm, mood_label="content", now=2.0)
        war_emits = p.emissions_by_speaker("war")
        assert len(war_emits) == 1
        assert war_emits[0].line == "open!"

    def test_clear(self):
        p = CalloutPipeline()
        spk = SpatialAudio(actor_id="x", position=(0.0, 0.0, 0.0))
        p.emit(line="x", speaker=spk, mood_label="content", now=0.0)
        p.clear()
        assert len(p) == 0


class TestComposition:

    def test_doc_example_chain_sequence(self):
        """Doc worked example: WAR opens chain, NIN closes Distortion,
        BLM bursts Slow."""
        p = CalloutPipeline()
        war = SpatialAudio(actor_id="war", position=(0.0, 0.0, 0.0))
        nin = SpatialAudio(actor_id="nin", position=(2.0, 0.0, 0.0))
        blm = SpatialAudio(actor_id="blm", position=(5.0, 0.0, 0.0))
        p.emit(line=skillchain_open_callout(), speaker=war,
                  mood_label="alert", now=0.0)
        p.emit(line=chain_close_callout("Distortion"), speaker=nin,
                  mood_label="alert", now=1.5)
        p.emit(line=mb_ailment_callout("Slow"), speaker=blm,
                  mood_label="furious", now=2.0)
        lines = [e.line for e in p.emissions()]
        assert lines == ["Skillchain open!", "Closing — Distortion!",
                            "Magic Burst — Slow!"]
        # furious BLM emission should have intensity_multiplier > 1
        blm_em = p.emissions_by_speaker("blm")[0]
        assert blm_em.synthesizer_input["intensity_multiplier"] > 1.0

    def test_lv3_light_apex_emission(self):
        p = CalloutPipeline()
        spk = SpatialAudio(actor_id="hero", position=(0.0, 0.0, 0.0))
        p.emit(line=light_or_darkness_callout("Light"), speaker=spk,
                  mood_label="furious", now=10.0)
        em = p.emissions()[0]
        assert em.line == "LIGHT!"
        assert em.synthesizer_input["intensity_multiplier"] > 1.0
