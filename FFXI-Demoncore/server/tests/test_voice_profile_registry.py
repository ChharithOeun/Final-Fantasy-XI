"""Tests for the voice profile registry."""
from __future__ import annotations

from server.voice_profile_registry import (
    VoiceAccent,
    VoiceEmotion,
    VoiceGender,
    VoiceProfile,
    VoiceProfileRegistry,
    VoiceTimbre,
    seed_default_voice_profiles,
)


def test_register_faction_default():
    reg = VoiceProfileRegistry()
    p = VoiceProfile(
        pitch_hz_low=100, pitch_hz_high=200,
        accent=VoiceAccent.BASTOKAN,
    )
    reg.register_faction_default(
        faction_id="bastok", profile=p,
    )
    assert reg.total_faction_defaults() == 1


def test_register_npc_override():
    reg = VoiceProfileRegistry()
    p = VoiceProfile(
        accent=VoiceAccent.BASTOKAN,
        gender=VoiceGender.MASCULINE,
    )
    reg.register_npc(npc_id="cooper", profile=p)
    assert reg.has_override("cooper")
    assert reg.voice_for(npc_id="cooper") is p


def test_voice_for_falls_back_to_faction():
    reg = VoiceProfileRegistry()
    fac = VoiceProfile(
        accent=VoiceAccent.BASTOKAN,
        gender=VoiceGender.MASCULINE,
    )
    reg.register_faction_default(
        faction_id="bastok", profile=fac,
    )
    res = reg.voice_for(
        npc_id="random_bastokan",
        faction_id="bastok",
    )
    assert res is fac


def test_voice_for_unknown_returns_none():
    reg = VoiceProfileRegistry()
    assert reg.voice_for(npc_id="ghost") is None


def test_npc_override_beats_faction_default():
    reg = VoiceProfileRegistry()
    fac = VoiceProfile(accent=VoiceAccent.BASTOKAN)
    npc = VoiceProfile(
        accent=VoiceAccent.JEUNOAN,
        gender=VoiceGender.FEMININE,
    )
    reg.register_faction_default(
        faction_id="bastok", profile=fac,
    )
    reg.register_npc(npc_id="curilla_visit", profile=npc)
    # Curilla is in Bastok but has her own profile
    res = reg.voice_for(
        npc_id="curilla_visit", faction_id="bastok",
    )
    assert res is npc


def test_resolve_for_speech_applies_emotion():
    reg = VoiceProfileRegistry()
    fac = VoiceProfile(
        emotional_default=VoiceEmotion.CALM,
    )
    reg.register_faction_default(
        faction_id="bastok", profile=fac,
    )
    res = reg.resolve_for_speech(
        npc_id="x", faction_id="bastok",
        override_emotion=VoiceEmotion.MENACING,
    )
    assert res.emotional_default == VoiceEmotion.MENACING


def test_resolve_for_speech_no_emotion_default():
    reg = VoiceProfileRegistry()
    fac = VoiceProfile(
        emotional_default=VoiceEmotion.SOLEMN,
    )
    reg.register_faction_default(
        faction_id="bastok", profile=fac,
    )
    res = reg.resolve_for_speech(
        npc_id="x", faction_id="bastok",
    )
    assert res.emotional_default == VoiceEmotion.SOLEMN


def test_resolve_for_speech_unknown_returns_none():
    reg = VoiceProfileRegistry()
    res = reg.resolve_for_speech(
        npc_id="ghost", faction_id="ghost_faction",
    )
    assert res is None


def test_seed_default_profiles_count():
    reg = seed_default_voice_profiles(VoiceProfileRegistry())
    assert reg.total_faction_defaults() >= 9


def test_default_seed_bastok_gravelly():
    reg = seed_default_voice_profiles(VoiceProfileRegistry())
    res = reg.voice_for(
        npc_id="x", faction_id="bastok",
    )
    assert res.timbre == VoiceTimbre.GRAVELLY
    assert res.accent == VoiceAccent.BASTOKAN


def test_default_seed_windurst_melodic():
    reg = seed_default_voice_profiles(VoiceProfileRegistry())
    res = reg.voice_for(
        npc_id="x", faction_id="windurst",
    )
    assert res.timbre == VoiceTimbre.MELODIC
    assert res.gender == VoiceGender.FEMININE


def test_default_seed_orc_monstrous():
    reg = seed_default_voice_profiles(VoiceProfileRegistry())
    res = reg.voice_for(
        npc_id="x", faction_id="orc",
    )
    assert res.timbre == VoiceTimbre.MONSTROUS
    assert res.accent == VoiceAccent.BEASTMEN


def test_default_seed_dragon_low_pitch():
    reg = seed_default_voice_profiles(VoiceProfileRegistry())
    res = reg.voice_for(
        npc_id="x", faction_id="dragon",
    )
    assert res.pitch_hz_low <= 50
    assert res.gender == VoiceGender.MONSTROUS


def test_with_emotion_returns_new_profile():
    p = VoiceProfile()
    e = p.with_emotion(VoiceEmotion.CHEERFUL)
    assert e is not p
    assert e.emotional_default == VoiceEmotion.CHEERFUL


def test_full_lifecycle_curilla_voice():
    """Curilla is a flagship Sandorian NPC; she uses the
    default Sandorian voice. A second visit to a different
    NPC should use the same Sandorian voice."""
    reg = seed_default_voice_profiles(VoiceProfileRegistry())
    curilla = reg.voice_for(
        npc_id="curilla", faction_id="san_doria",
    )
    other = reg.voice_for(
        npc_id="random_guard", faction_id="san_doria",
    )
    assert curilla is other
    # Same voice both times -> consistency across game-days
    again = reg.voice_for(
        npc_id="curilla", faction_id="san_doria",
    )
    assert again is curilla
