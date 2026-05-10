"""Tests for dialogue_lipsync."""
from __future__ import annotations

import pytest

from server.dialogue_lipsync import (
    DialogueLipsyncSystem, LipsyncEngine, LipsyncTrack,
    PHONEME_TO_VISEME, SUPPORTED_LANGUAGES,
    TrackState, VISEMES,
    engine_for, list_engines,
)


def test_visemes_count_14():
    assert len(VISEMES) == 14


def test_phoneme_map_includes_silence_and_vowels():
    assert PHONEME_TO_VISEME["sil"] == "sil"
    assert PHONEME_TO_VISEME["AA"] == "aa"
    assert PHONEME_TO_VISEME["IY"] == "I"


def test_phoneme_map_lips_closed_family():
    # P/B/M all collapse to PP viseme
    for p in ("P", "B", "M"):
        assert PHONEME_TO_VISEME[p] == "PP"


def test_engine_for_hero_npc_audio2face():
    assert engine_for("curilla") == LipsyncEngine.AUDIO2FACE


def test_engine_for_ambient_default_rhubarb():
    assert engine_for("random_villager") == LipsyncEngine.RHUBARB


def test_engine_for_named_oculus():
    assert (
        engine_for("named_quest_giver", "named")
        == LipsyncEngine.OCULUS
    )


def test_engine_for_hero_importance_audio2face():
    assert (
        engine_for("__no_override__", "hero")
        == LipsyncEngine.AUDIO2FACE
    )


def test_list_engines_sorted():
    names = list_engines()
    assert names == tuple(sorted(names))


def test_queue_track_happy():
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="line_001.wav",
        npc_id="curilla",
        language="en",
    )
    assert isinstance(rec, LipsyncTrack)
    assert rec.engine == LipsyncEngine.AUDIO2FACE
    assert rec.state == TrackState.PENDING


def test_queue_track_empty_audio_raises():
    s = DialogueLipsyncSystem()
    with pytest.raises(ValueError):
        s.queue_track(audio_file="", npc_id="curilla")


def test_queue_track_empty_npc_raises():
    s = DialogueLipsyncSystem()
    with pytest.raises(ValueError):
        s.queue_track(audio_file="a.wav", npc_id="")


def test_queue_track_unsupported_language_falls_back_rhubarb():
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav", npc_id="curilla",
        language="klingon",
    )
    assert rec.engine == LipsyncEngine.RHUBARB
    assert rec.language == "en"


def test_queue_track_rhubarb_for_japanese_falls_back():
    # Rhubarb only speaks English. Asking for Japanese ambient
    # should land on Rhubarb-en (engine demotion).
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav",
        npc_id="random_taru_villager",
        language="ja",
    )
    # importance defaults to ambient → wants Rhubarb anyway.
    assert rec.engine == LipsyncEngine.RHUBARB


def test_queue_track_oculus_for_french_demotes():
    # Oculus doesn't list fr → demote to Rhubarb-en.
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav",
        npc_id="named_npc",
        language="fr",
        dialogue_importance="named",
    )
    assert rec.engine == LipsyncEngine.RHUBARB
    assert rec.language == "en"


def test_queue_track_hero_japanese_audio2face_speaks_ja():
    # Audio2Face supports JA, so hero+ja stays on Audio2Face.
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav",
        npc_id="ayame",
        language="ja",
    )
    assert rec.engine == LipsyncEngine.AUDIO2FACE
    assert rec.language == "ja"


def test_get_track_unknown_raises():
    s = DialogueLipsyncSystem()
    with pytest.raises(KeyError):
        s.get_track("track_99")


def test_analyze_emits_visemes():
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav", npc_id="curilla",
    )
    new = s.analyze(rec.track_id, [
        (0.0, "sil"),
        (0.10, "M"),
        (0.20, "AA"),
        (0.35, "T"),
    ])
    assert new.state == TrackState.READY
    visemes = [v for _, v in new.visemes]
    assert visemes == ["sil", "PP", "aa", "DD"]


def test_analyze_unknown_phoneme_falls_back_silence():
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav", npc_id="curilla",
    )
    new = s.analyze(rec.track_id, [
        (0.0, "qrx"),
    ])
    assert new.visemes[0][1] == "sil"


def test_get_visemes_round_trip():
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav", npc_id="curilla",
    )
    s.analyze(rec.track_id, [(0.0, "AA"), (0.1, "M")])
    got = s.get_visemes(rec.track_id)
    assert got == ((0.0, "aa"), (0.1, "PP"))


def test_bake_curve_happy():
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav", npc_id="curilla",
    )
    s.analyze(rec.track_id, [(0.0, "M"), (0.1, "AA")])
    baked = s.bake_curve(rec.track_id)
    assert baked.state == TrackState.BAKED
    assert len(baked.baked_curve) == 2
    t0, w0 = baked.baked_curve[0]
    assert t0 == 0.0
    assert w0["PP"] == 1.0
    assert w0["aa"] == 0.0


def test_bake_curve_requires_ready():
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav", npc_id="curilla",
    )
    # didn't call analyze
    with pytest.raises(RuntimeError):
        s.bake_curve(rec.track_id)


def test_analyze_after_bake_blocked():
    s = DialogueLipsyncSystem()
    rec = s.queue_track(
        audio_file="x.wav", npc_id="curilla",
    )
    s.analyze(rec.track_id, [(0.0, "M")])
    s.bake_curve(rec.track_id)
    with pytest.raises(RuntimeError):
        s.analyze(rec.track_id, [(0.0, "M")])


def test_supported_languages_has_en_ja_fr_de():
    assert {"en", "ja", "fr", "de"}.issubset(
        set(SUPPORTED_LANGUAGES),
    )


def test_engine_for_named_aldo_override_wins():
    # Aldo is in override map → AUDIO2FACE regardless of
    # importance.
    assert (
        engine_for("aldo", "ambient")
        == LipsyncEngine.AUDIO2FACE
    )


def test_tracks_listed():
    s = DialogueLipsyncSystem()
    s.queue_track(audio_file="a.wav", npc_id="maat")
    s.queue_track(audio_file="b.wav", npc_id="curilla")
    assert len(s.tracks()) == 2


def test_baked_weights_sum_to_one_per_keyframe():
    # Single-viseme baking → each frame's weights sum to 1.0.
    s = DialogueLipsyncSystem()
    rec = s.queue_track(audio_file="x.wav", npc_id="maat")
    s.analyze(rec.track_id, [
        (0.0, "M"), (0.1, "AA"), (0.2, "S"),
    ])
    baked = s.bake_curve(rec.track_id)
    for _, w in baked.baked_curve:
        assert sum(w.values()) == pytest.approx(1.0)
