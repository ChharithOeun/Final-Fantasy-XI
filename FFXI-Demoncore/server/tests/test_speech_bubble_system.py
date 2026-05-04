"""Tests for the speech bubble system."""
from __future__ import annotations

from server.speech_bubble_system import (
    BubbleEmotion,
    BubbleKind,
    DEFAULT_EARSHOT_RADIUS,
    MAX_BUBBLE_DURATION,
    MIN_BUBBLE_DURATION,
    SpeechBubbleSystem,
)


def test_speak_creates_bubble():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="merchant_a", zone_id="bastok",
        x=10, y=10, z=0,
        line="Welcome to my shop.",
    )
    assert bub is not None
    assert bub.kind == BubbleKind.DIALOGUE


def test_empty_line_rejected():
    s = SpeechBubbleSystem()
    assert s.speak(
        speaker_id="x", zone_id="z",
        x=0, y=0, z=0, line="",
    ) is None


def test_duration_floor():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="x", zone_id="z",
        x=0, y=0, z=0, line="!",
        now_seconds=0.0,
    )
    assert bub.expires_at_seconds >= MIN_BUBBLE_DURATION


def test_duration_ceiling_for_long_line():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="x", zone_id="z",
        x=0, y=0, z=0,
        line="a" * 5000,
        now_seconds=0.0,
    )
    assert bub.expires_at_seconds <= MAX_BUBBLE_DURATION


def test_listener_in_earshot():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="merchant_a", zone_id="bastok",
        x=10, y=10, z=0,
        line="Welcome to my shop.",
    )
    overhears = s.listeners_in_earshot(
        bubble_id=bub.bubble_id,
        listeners=(
            ("alice", "bastok", 12, 10, 0),
            ("bob", "bastok", 100, 100, 0),
        ),
    )
    ids = {o.listener_id for o in overhears}
    assert "alice" in ids
    assert "bob" not in ids


def test_listener_other_zone_excluded():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="m", zone_id="bastok",
        x=0, y=0, z=0, line="hi",
    )
    overhears = s.listeners_in_earshot(
        bubble_id=bub.bubble_id,
        listeners=(
            ("alice", "san_doria", 0, 0, 0),
        ),
    )
    assert overhears == ()


def test_listener_3d_distance_includes_z():
    s = SpeechBubbleSystem(earshot_radius=10.0)
    bub = s.speak(
        speaker_id="m", zone_id="z",
        x=0, y=0, z=0, line="hi",
    )
    overhears = s.listeners_in_earshot(
        bubble_id=bub.bubble_id,
        listeners=(
            ("alice", "z", 0, 0, 50),
        ),
    )
    assert overhears == ()


def test_side_quest_tag_propagates():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="m", zone_id="z",
        x=0, y=0, z=0,
        line="The ravens fly at midnight.",
        side_quest_tag="ravens_of_zilart",
    )
    overhears = s.listeners_in_earshot(
        bubble_id=bub.bubble_id,
        listeners=(("alice", "z", 1, 1, 0),),
    )
    assert len(overhears) == 1
    assert overhears[0].side_quest_tag == "ravens_of_zilart"


def test_listeners_unknown_bubble_returns_empty():
    s = SpeechBubbleSystem()
    overhears = s.listeners_in_earshot(
        bubble_id="ghost",
        listeners=(("alice", "z", 0, 0, 0),),
    )
    assert overhears == ()


def test_tick_expires_old_bubbles():
    s = SpeechBubbleSystem()
    s.speak(
        speaker_id="m", zone_id="z",
        x=0, y=0, z=0, line="hi",
        now_seconds=0.0,
    )
    expired = s.tick(now_seconds=100.0)
    assert len(expired) == 1
    assert s.total_active() == 0


def test_tick_keeps_active_bubble():
    s = SpeechBubbleSystem()
    s.speak(
        speaker_id="m", zone_id="z",
        x=0, y=0, z=0, line="hi",
        now_seconds=0.0,
    )
    expired = s.tick(now_seconds=0.5)
    assert expired == ()


def test_active_bubbles_in_zone_filter():
    s = SpeechBubbleSystem()
    s.speak(
        speaker_id="m1", zone_id="bastok",
        x=0, y=0, z=0, line="x",
    )
    s.speak(
        speaker_id="m2", zone_id="windurst",
        x=0, y=0, z=0, line="x",
    )
    bubs = s.active_bubbles_in_zone("bastok")
    assert len(bubs) == 1


def test_overhear_distance_reported():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="m", zone_id="z",
        x=0, y=0, z=0, line="hi",
    )
    overhears = s.listeners_in_earshot(
        bubble_id=bub.bubble_id,
        listeners=(("alice", "z", 5, 0, 0),),
    )
    assert overhears[0].distance == 5.0


def test_emotion_propagated():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="m", zone_id="z",
        x=0, y=0, z=0, line="hi",
        emotion=BubbleEmotion.SECRETIVE,
    )
    assert bub.emotion == BubbleEmotion.SECRETIVE


def test_voice_clip_id_propagated():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="m", zone_id="z",
        x=0, y=0, z=0, line="hi",
        voice_clip_id="merchant_greet_01",
    )
    assert bub.voice_clip_id == "merchant_greet_01"


def test_default_earshot_radius_constant():
    assert DEFAULT_EARSHOT_RADIUS == 18.0


def test_explicit_duration_overrides():
    s = SpeechBubbleSystem()
    bub = s.speak(
        speaker_id="m", zone_id="z",
        x=0, y=0, z=0, line="hi",
        now_seconds=0.0, duration_seconds=5.0,
    )
    assert bub.expires_at_seconds == 5.0
