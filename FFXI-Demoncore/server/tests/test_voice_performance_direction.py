"""Tests for voice_performance_direction."""
from __future__ import annotations

import pytest

from server.voice_performance_direction import (
    Direction, Intent, PerformanceDirection,
)


def _pd_with_line() -> PerformanceDirection:
    pd = PerformanceDirection()
    pd.register_line(
        "L1", "curilla", "Hold the line!",
    )
    return pd


def test_intent_has_at_least_15_tags():
    assert len(list(Intent)) >= 15


def test_register_line_basic():
    pd = _pd_with_line()
    rec = pd.direction_packet_for("curilla")
    assert len(rec) == 1


def test_register_line_blank_id_raises():
    pd = PerformanceDirection()
    with pytest.raises(ValueError):
        pd.register_line("", "curilla", "x")


def test_register_line_blank_role_raises():
    pd = PerformanceDirection()
    with pytest.raises(ValueError):
        pd.register_line("L1", "", "x")


def test_register_line_duplicate_raises():
    pd = _pd_with_line()
    with pytest.raises(ValueError):
        pd.register_line("L1", "curilla", "again")


def test_set_direction_basic():
    pd = _pd_with_line()
    d = pd.set_direction(
        "L1", [Intent.SHOUT, Intent.DEFIANT],
        tempo_mod=0.5, pitch_mod=-0.5,
        pause_before_ms=200, pause_after_ms=400,
    )
    assert Intent.SHOUT in d.intent_tags


def test_set_direction_unknown_line_raises():
    pd = PerformanceDirection()
    with pytest.raises(KeyError):
        pd.set_direction(
            "L1", [Intent.SHOUT], 0.0, 0.0, 0, 0,
        )


def test_set_direction_tempo_out_of_range():
    pd = _pd_with_line()
    with pytest.raises(ValueError):
        pd.set_direction(
            "L1", [], tempo_mod=3.0, pitch_mod=0.0,
            pause_before_ms=0, pause_after_ms=0,
        )


def test_set_direction_pitch_out_of_range():
    pd = _pd_with_line()
    with pytest.raises(ValueError):
        pd.set_direction(
            "L1", [], tempo_mod=0.0, pitch_mod=-3.0,
            pause_before_ms=0, pause_after_ms=0,
        )


def test_set_direction_negative_pause_raises():
    pd = _pd_with_line()
    with pytest.raises(ValueError):
        pd.set_direction(
            "L1", [], tempo_mod=0.0, pitch_mod=0.0,
            pause_before_ms=-1, pause_after_ms=0,
        )


def test_get_direction_default_when_unset():
    pd = _pd_with_line()
    d = pd.get_direction("L1")
    assert isinstance(d, Direction)
    assert d.intent_tags == frozenset()


def test_get_direction_unknown_line_raises():
    pd = PerformanceDirection()
    with pytest.raises(KeyError):
        pd.get_direction("L1")


def test_lines_with_intent_filters():
    pd = _pd_with_line()
    pd.register_line("L2", "curilla", "Whisper line")
    pd.set_direction(
        "L1", [Intent.SHOUT], 0.0, 0.0, 0, 0,
    )
    pd.set_direction(
        "L2", [Intent.WHISPER], 0.0, 0.0, 0, 0,
    )
    out = pd.lines_with_intent(Intent.WHISPER)
    assert len(out) == 1
    assert out[0].line_id == "L2"


def test_lines_with_intent_skips_undirected():
    pd = _pd_with_line()
    out = pd.lines_with_intent(Intent.SHOUT)
    assert out == ()


def test_direction_packet_for_role():
    pd = _pd_with_line()
    pd.register_line("L2", "trion", "x")
    pd.register_line("L3", "curilla", "y")
    out = pd.direction_packet_for("curilla")
    assert len(out) == 2
    assert {r.line_id for r in out} == {"L1", "L3"}


def test_to_murch_emotion_score_no_tags_is_low():
    pd = PerformanceDirection()
    d = Direction(
        intent_tags=frozenset(),
        tempo_modifier=0.0,
        pitch_modifier_semitones=0.0,
        pause_before_ms=0, pause_after_ms=0,
    )
    assert pd.to_murch_emotion_score(d) <= 0.2


def test_to_murch_emotion_score_whisper_high():
    pd = PerformanceDirection()
    d = Direction(
        intent_tags=frozenset({Intent.WHISPER}),
        tempo_modifier=0.0, pitch_modifier_semitones=0.0,
        pause_before_ms=0, pause_after_ms=0,
    )
    assert pd.to_murch_emotion_score(d) >= 0.85


def test_to_murch_emotion_pause_boost():
    pd = PerformanceDirection()
    d_short = Direction(
        intent_tags=frozenset({Intent.RESIGNED}),
        tempo_modifier=0.0, pitch_modifier_semitones=0.0,
        pause_before_ms=100, pause_after_ms=100,
    )
    d_long = Direction(
        intent_tags=frozenset({Intent.RESIGNED}),
        tempo_modifier=0.0, pitch_modifier_semitones=0.0,
        pause_before_ms=800, pause_after_ms=800,
    )
    assert (
        pd.to_murch_emotion_score(d_long)
        > pd.to_murch_emotion_score(d_short)
    )


def test_emotion_score_for_line_helper():
    pd = _pd_with_line()
    pd.set_direction(
        "L1", [Intent.SHOUT], 0.0, 0.0, 0, 0,
    )
    assert pd.emotion_score_for("L1") > 0.5


def test_ai_inference_kwargs_shape():
    pd = _pd_with_line()
    pd.set_direction(
        "L1", [Intent.SHOUT, Intent.DEFIANT],
        0.5, -0.3, 100, 200,
        reference_clip_uri="ref://clip1",
    )
    out = pd.ai_inference_kwargs("L1")
    assert out["line_id"] == "L1"
    assert out["role_id"] == "curilla"
    assert out["text"] == "Hold the line!"
    assert "shout" in out["intent_tags"]
    assert out["tempo_modifier"] == 0.5
    assert out["pitch_modifier_semitones"] == -0.3
    assert out["reference_clip_uri"] == "ref://clip1"


def test_ai_inference_kwargs_default_when_no_direction():
    pd = _pd_with_line()
    out = pd.ai_inference_kwargs("L1")
    assert out["intent_tags"] == []
    assert out["tempo_modifier"] == 0.0


def test_human_va_brief_includes_text_and_role():
    pd = _pd_with_line()
    pd.set_direction(
        "L1", [Intent.SHOUT], 0.0, 0.0, 0, 0,
    )
    md = pd.human_va_brief("L1")
    assert "curilla" in md
    assert "Hold the line!" in md
    assert "shout" in md


def test_human_va_brief_no_tags_message():
    pd = _pd_with_line()
    md = pd.human_va_brief("L1")
    assert "neutral read" in md or "no tags" in md


def test_human_va_brief_unknown_line_raises():
    pd = PerformanceDirection()
    with pytest.raises(KeyError):
        pd.human_va_brief("L1")


def test_intent_enum_includes_break_fourth_wall():
    assert Intent.BREAK_FOURTH_WALL in Intent


def test_set_direction_rejects_non_intent():
    pd = _pd_with_line()
    with pytest.raises(TypeError):
        pd.set_direction(
            "L1", ["shout"],  # type: ignore[list-item]
            0.0, 0.0, 0, 0,
        )


def test_direction_dataclass_frozen():
    import dataclasses as _d
    d = Direction(
        intent_tags=frozenset(),
        tempo_modifier=0.0, pitch_modifier_semitones=0.0,
        pause_before_ms=0, pause_after_ms=0,
    )
    with pytest.raises(_d.FrozenInstanceError):
        d.tempo_modifier = 1.0  # type: ignore[misc]


def test_set_direction_sets_allow_alt_takes():
    pd = _pd_with_line()
    d = pd.set_direction(
        "L1", [Intent.TENDER], 0.0, 0.0, 0, 0,
        allow_alt_takes=False,
    )
    assert d.allow_alt_takes is False
