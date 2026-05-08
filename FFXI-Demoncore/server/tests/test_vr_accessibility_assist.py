"""Tests for vr_accessibility_assist."""
from __future__ import annotations

from server.vr_accessibility_assist import (
    ActiveHand, VrAccessibilityAssist,
)


def test_default_profile_neutral():
    a = VrAccessibilityAssist()
    p = a.profile(player_id="bob")
    assert p.one_handed is None
    assert p.height_offset_m == 0.0
    assert p.aim_assist_strength == 0.0
    assert p.cast_dwell_ms == 0
    assert p.motion_safe_shrink_m == 0.0
    assert p.auto_recenter_after_s == 0


def test_set_one_handed_left():
    a = VrAccessibilityAssist()
    assert a.set_one_handed(
        player_id="bob", active_hand=ActiveHand.LEFT,
    ) is True
    assert a.profile(player_id="bob").one_handed == ActiveHand.LEFT


def test_set_one_handed_blank_blocked():
    a = VrAccessibilityAssist()
    assert a.set_one_handed(
        player_id="", active_hand=ActiveHand.LEFT,
    ) is False


def test_clear_one_handed():
    a = VrAccessibilityAssist()
    a.set_one_handed(
        player_id="bob", active_hand=ActiveHand.RIGHT,
    )
    assert a.clear_one_handed(player_id="bob") is True
    assert a.profile(player_id="bob").one_handed is None


def test_clear_one_handed_no_change():
    a = VrAccessibilityAssist()
    assert a.clear_one_handed(player_id="bob") is False


def test_set_height_offset_in_range():
    a = VrAccessibilityAssist()
    assert a.set_height_offset(
        player_id="bob", meters=0.4,
    ) is True
    assert a.profile(
        player_id="bob",
    ).height_offset_m == 0.4


def test_set_height_offset_too_low_blocked():
    a = VrAccessibilityAssist()
    assert a.set_height_offset(
        player_id="bob", meters=-2.0,
    ) is False


def test_set_height_offset_too_high_blocked():
    a = VrAccessibilityAssist()
    assert a.set_height_offset(
        player_id="bob", meters=2.0,
    ) is False


def test_set_aim_assist():
    a = VrAccessibilityAssist()
    assert a.set_aim_assist(
        player_id="bob", strength=0.5,
    ) is True
    assert a.profile(
        player_id="bob",
    ).aim_assist_strength == 0.5


def test_set_aim_assist_clamped():
    a = VrAccessibilityAssist()
    assert a.set_aim_assist(
        player_id="bob", strength=1.5,
    ) is False
    assert a.set_aim_assist(
        player_id="bob", strength=-0.1,
    ) is False


def test_set_cast_dwell():
    a = VrAccessibilityAssist()
    assert a.set_cast_dwell(
        player_id="bob", ms=1500,
    ) is True
    assert a.profile(
        player_id="bob",
    ).cast_dwell_ms == 1500


def test_set_cast_dwell_too_high_blocked():
    a = VrAccessibilityAssist()
    assert a.set_cast_dwell(
        player_id="bob", ms=5000,
    ) is False


def test_set_cast_dwell_negative_blocked():
    a = VrAccessibilityAssist()
    assert a.set_cast_dwell(
        player_id="bob", ms=-100,
    ) is False


def test_set_motion_safe_shrink():
    a = VrAccessibilityAssist()
    assert a.set_motion_safe_shrink(
        player_id="bob", m=0.5,
    ) is True
    assert a.profile(
        player_id="bob",
    ).motion_safe_shrink_m == 0.5


def test_set_motion_safe_shrink_too_high_blocked():
    a = VrAccessibilityAssist()
    assert a.set_motion_safe_shrink(
        player_id="bob", m=2.0,
    ) is False


def test_set_auto_recenter_after():
    a = VrAccessibilityAssist()
    assert a.set_auto_recenter_after(
        player_id="bob", seconds=120,
    ) is True


def test_set_auto_recenter_too_high_blocked():
    a = VrAccessibilityAssist()
    assert a.set_auto_recenter_after(
        player_id="bob", seconds=9999,
    ) is False


def test_setters_compose():
    """Multiple setters compose into one profile."""
    a = VrAccessibilityAssist()
    a.set_one_handed(
        player_id="bob", active_hand=ActiveHand.LEFT,
    )
    a.set_height_offset(player_id="bob", meters=0.3)
    a.set_aim_assist(player_id="bob", strength=0.4)
    p = a.profile(player_id="bob")
    assert p.one_handed == ActiveHand.LEFT
    assert p.height_offset_m == 0.3
    assert p.aim_assist_strength == 0.4


def test_reset():
    a = VrAccessibilityAssist()
    a.set_one_handed(
        player_id="bob", active_hand=ActiveHand.LEFT,
    )
    assert a.reset(player_id="bob") is True
    p = a.profile(player_id="bob")
    assert p.one_handed is None


def test_reset_unknown():
    a = VrAccessibilityAssist()
    assert a.reset(player_id="ghost") is False


def test_two_active_hands():
    assert len(list(ActiveHand)) == 2


def test_isolated_per_player():
    a = VrAccessibilityAssist()
    a.set_one_handed(
        player_id="bob", active_hand=ActiveHand.LEFT,
    )
    # Cara still on default
    assert a.profile(player_id="cara").one_handed is None
