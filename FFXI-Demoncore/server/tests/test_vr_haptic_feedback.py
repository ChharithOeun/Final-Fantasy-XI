"""Tests for vr_haptic_feedback."""
from __future__ import annotations

from server.vr_haptic_feedback import (
    EventKind, HapticHand, HapticPattern, VrHapticFeedback,
)


def test_emit_default_pattern():
    h = VrHapticFeedback()
    pulse = h.emit(
        player_id="bob",
        event_kind=EventKind.DAMAGE_TAKEN,
    )
    assert pulse is not None
    assert pulse.player_id == "bob"
    assert pulse.event_kind == EventKind.DAMAGE_TAKEN
    assert pulse.amplitude == 0.8
    assert pulse.hand == HapticHand.BOTH


def test_emit_different_kinds():
    h = VrHapticFeedback()
    p1 = h.emit(player_id="bob", event_kind=EventKind.SPELL_CAST_TICK)
    p2 = h.emit(player_id="bob", event_kind=EventKind.WEAPONSKILL_PROC)
    assert p1.hand == HapticHand.LEFT
    assert p2.hand == HapticHand.RIGHT


def test_set_pattern_overrides():
    h = VrHapticFeedback()
    custom = HapticPattern(
        frequency_hz=200.0, amplitude=0.2,
        duration_ms=500, hand=HapticHand.LEFT,
    )
    assert h.set_pattern(
        event_kind=EventKind.DAMAGE_TAKEN, pattern=custom,
    ) is True
    pulse = h.emit(
        player_id="bob",
        event_kind=EventKind.DAMAGE_TAKEN,
    )
    assert pulse.frequency_hz == 200.0
    assert pulse.amplitude == 0.2
    assert pulse.hand == HapticHand.LEFT


def test_set_pattern_blocks_invalid_amplitude():
    h = VrHapticFeedback()
    bad = HapticPattern(
        frequency_hz=100.0, amplitude=1.5,
        duration_ms=100, hand=HapticHand.BOTH,
    )
    assert h.set_pattern(
        event_kind=EventKind.DEATH, pattern=bad,
    ) is False


def test_set_pattern_blocks_negative_amplitude():
    h = VrHapticFeedback()
    bad = HapticPattern(
        frequency_hz=100.0, amplitude=-0.1,
        duration_ms=100, hand=HapticHand.BOTH,
    )
    assert h.set_pattern(
        event_kind=EventKind.DEATH, pattern=bad,
    ) is False


def test_set_pattern_blocks_zero_duration():
    h = VrHapticFeedback()
    bad = HapticPattern(
        frequency_hz=100.0, amplitude=0.5,
        duration_ms=0, hand=HapticHand.BOTH,
    )
    assert h.set_pattern(
        event_kind=EventKind.DEATH, pattern=bad,
    ) is False


def test_reset_pattern():
    h = VrHapticFeedback()
    custom = HapticPattern(
        frequency_hz=200.0, amplitude=0.1,
        duration_ms=50, hand=HapticHand.LEFT,
    )
    h.set_pattern(
        event_kind=EventKind.DAMAGE_TAKEN, pattern=custom,
    )
    assert h.reset_pattern(
        event_kind=EventKind.DAMAGE_TAKEN,
    ) is True
    pulse = h.emit(
        player_id="bob",
        event_kind=EventKind.DAMAGE_TAKEN,
    )
    # Back to default 0.8 amplitude
    assert pulse.amplitude == 0.8


def test_reset_pattern_unknown():
    """Resetting a never-customized pattern is no-op."""
    h = VrHapticFeedback()
    assert h.reset_pattern(
        event_kind=EventKind.DEATH,
    ) is False


def test_intensity_scales_amplitude():
    h = VrHapticFeedback()
    h.set_intensity(player_id="bob", intensity=0.5)
    pulse = h.emit(
        player_id="bob",
        event_kind=EventKind.DAMAGE_TAKEN,
    )
    # 0.8 default * 0.5 = 0.4
    assert pulse.amplitude == 0.4


def test_intensity_zero_emits_nothing():
    h = VrHapticFeedback()
    h.set_intensity(player_id="bob", intensity=0.0)
    pulse = h.emit(
        player_id="bob",
        event_kind=EventKind.DAMAGE_TAKEN,
    )
    assert pulse is None


def test_intensity_invalid_blocked():
    h = VrHapticFeedback()
    assert h.set_intensity(
        player_id="bob", intensity=1.5,
    ) is False
    assert h.set_intensity(
        player_id="bob", intensity=-0.1,
    ) is False


def test_intensity_blank_player_blocked():
    h = VrHapticFeedback()
    assert h.set_intensity(
        player_id="", intensity=0.5,
    ) is False


def test_mute_blocks_emit():
    h = VrHapticFeedback()
    assert h.mute(player_id="bob") is True
    pulse = h.emit(
        player_id="bob",
        event_kind=EventKind.DAMAGE_TAKEN,
    )
    assert pulse is None
    assert h.is_muted(player_id="bob") is True


def test_unmute_restores():
    h = VrHapticFeedback()
    h.mute(player_id="bob")
    assert h.unmute(player_id="bob") is True
    pulse = h.emit(
        player_id="bob",
        event_kind=EventKind.DAMAGE_TAKEN,
    )
    assert pulse is not None


def test_double_mute_blocked():
    h = VrHapticFeedback()
    h.mute(player_id="bob")
    assert h.mute(player_id="bob") is False


def test_unmute_unmuted_blocked():
    h = VrHapticFeedback()
    assert h.unmute(player_id="bob") is False


def test_emit_blank_player_blocked():
    h = VrHapticFeedback()
    pulse = h.emit(
        player_id="",
        event_kind=EventKind.DAMAGE_TAKEN,
    )
    assert pulse is None


def test_pulses_for_returns_player_only():
    h = VrHapticFeedback()
    h.emit(player_id="bob", event_kind=EventKind.DAMAGE_TAKEN)
    h.emit(player_id="cara", event_kind=EventKind.DAMAGE_TAKEN)
    h.emit(player_id="bob", event_kind=EventKind.HEAL_RECEIVED)
    bob_pulses = h.pulses_for(player_id="bob")
    assert len(bob_pulses) == 2
    assert all(p.player_id == "bob" for p in bob_pulses)


def test_clear_pulses():
    h = VrHapticFeedback()
    h.emit(player_id="bob", event_kind=EventKind.DAMAGE_TAKEN)
    assert h.clear_pulses(player_id="bob") is True
    assert h.pulses_for(player_id="bob") == []


def test_clear_pulses_empty():
    h = VrHapticFeedback()
    assert h.clear_pulses(player_id="bob") is False


def test_resolve_pattern_default():
    h = VrHapticFeedback()
    pat = h.resolve_pattern(event_kind=EventKind.DEATH)
    assert pat.amplitude == 1.0
    assert pat.duration_ms == 1000


def test_resolve_pattern_custom_returned():
    h = VrHapticFeedback()
    custom = HapticPattern(
        frequency_hz=99.0, amplitude=0.7,
        duration_ms=200, hand=HapticHand.RIGHT,
    )
    h.set_pattern(
        event_kind=EventKind.LEVEL_UP, pattern=custom,
    )
    pat = h.resolve_pattern(event_kind=EventKind.LEVEL_UP)
    assert pat.frequency_hz == 99.0


def test_twelve_event_kinds():
    assert len(list(EventKind)) == 12


def test_three_hand_options():
    assert len(list(HapticHand)) == 3
