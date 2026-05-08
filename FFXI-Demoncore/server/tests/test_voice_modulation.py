"""Tests for voice_modulation."""
from __future__ import annotations

from server.voice_modulation import (
    AccentPreset, VoiceModulation,
)


def test_default_profile_neutral():
    v = VoiceModulation()
    p = v.profile(player_id="bob")
    assert p.pitch_semitones == 0
    assert p.timbre_warm_cool == 0.0
    assert p.speed_multiplier == 1.0
    assert p.accent == AccentPreset.NEUTRAL


def test_set_pitch():
    v = VoiceModulation()
    assert v.set_pitch(
        player_id="bob", semitones=-5,
    ) is True
    assert v.profile(
        player_id="bob",
    ).pitch_semitones == -5


def test_set_pitch_too_low_blocked():
    v = VoiceModulation()
    assert v.set_pitch(
        player_id="bob", semitones=-13,
    ) is False


def test_set_pitch_too_high_blocked():
    v = VoiceModulation()
    assert v.set_pitch(
        player_id="bob", semitones=13,
    ) is False


def test_set_pitch_blank_blocked():
    v = VoiceModulation()
    assert v.set_pitch(
        player_id="", semitones=0,
    ) is False


def test_set_timbre_in_range():
    v = VoiceModulation()
    assert v.set_timbre(
        player_id="bob", warm_cool=0.5,
    ) is True


def test_set_timbre_out_of_range_blocked():
    v = VoiceModulation()
    assert v.set_timbre(
        player_id="bob", warm_cool=1.5,
    ) is False


def test_set_speed():
    v = VoiceModulation()
    assert v.set_speed(
        player_id="bob", multiplier=1.1,
    ) is True


def test_set_speed_too_slow_blocked():
    v = VoiceModulation()
    assert v.set_speed(
        player_id="bob", multiplier=0.5,
    ) is False


def test_set_speed_too_fast_blocked():
    v = VoiceModulation()
    assert v.set_speed(
        player_id="bob", multiplier=2.0,
    ) is False


def test_set_breathiness():
    v = VoiceModulation()
    assert v.set_breathiness(
        player_id="bob", level=0.4,
    ) is True


def test_set_breathiness_negative_blocked():
    v = VoiceModulation()
    assert v.set_breathiness(
        player_id="bob", level=-0.1,
    ) is False


def test_set_accent():
    v = VoiceModulation()
    assert v.set_accent(
        player_id="bob", accent=AccentPreset.GALKA_GROWL,
    ) is True
    assert v.profile(
        player_id="bob",
    ).accent == AccentPreset.GALKA_GROWL


def test_set_aggression_lift():
    v = VoiceModulation()
    assert v.set_aggression_lift(
        player_id="bob", level=0.6,
    ) is True


def test_set_aggression_lift_above_1_blocked():
    v = VoiceModulation()
    assert v.set_aggression_lift(
        player_id="bob", level=1.5,
    ) is False


def test_reset():
    v = VoiceModulation()
    v.set_pitch(player_id="bob", semitones=-5)
    assert v.reset(player_id="bob") is True
    assert v.profile(
        player_id="bob",
    ).pitch_semitones == 0


def test_reset_unknown_blocked():
    v = VoiceModulation()
    assert v.reset(player_id="ghost") is False


def test_settings_compose():
    v = VoiceModulation()
    v.set_pitch(player_id="bob", semitones=-3)
    v.set_speed(player_id="bob", multiplier=1.05)
    v.set_accent(
        player_id="bob", accent=AccentPreset.HUME_BASTOK,
    )
    p = v.profile(player_id="bob")
    assert p.pitch_semitones == -3
    assert p.speed_multiplier == 1.05
    assert p.accent == AccentPreset.HUME_BASTOK


def test_isolated_per_player():
    v = VoiceModulation()
    v.set_pitch(player_id="bob", semitones=-5)
    assert v.profile(
        player_id="cara",
    ).pitch_semitones == 0


def test_six_accent_presets():
    assert len(list(AccentPreset)) == 6
