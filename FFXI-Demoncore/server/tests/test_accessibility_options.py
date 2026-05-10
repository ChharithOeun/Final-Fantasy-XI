"""Tests for accessibility_options."""
from __future__ import annotations

import pytest

from server.accessibility_options import (
    AccessibilityFlag,
    AccessibilityOptionsSystem,
    FlagMetadata,
    SettingsCategory,
)


def _sys() -> AccessibilityOptionsSystem:
    return AccessibilityOptionsSystem()


# ---- enum coverage ----

def test_flag_count_at_least_22():
    assert len(list(AccessibilityFlag)) >= 22


def test_flag_has_arachnophobia():
    assert AccessibilityFlag.ARACHNOPHOBIA_MODE in list(
        AccessibilityFlag,
    )


def test_flag_has_reduced_flash():
    assert AccessibilityFlag.REDUCED_FLASH in list(
        AccessibilityFlag,
    )


def test_flag_has_one_hand_mode():
    assert AccessibilityFlag.ONE_HAND_MODE in list(
        AccessibilityFlag,
    )


def test_flag_has_screen_reader_hooks():
    assert AccessibilityFlag.SCREEN_READER_HOOKS in list(
        AccessibilityFlag,
    )


def test_settings_category_count():
    assert len(list(SettingsCategory)) == 5


# ---- metadata ----

def test_metadata_for_reduced_motion():
    s = _sys()
    md = s.metadata_for(AccessibilityFlag.REDUCED_MOTION)
    assert isinstance(md, FlagMetadata)
    assert md.default_off is True


def test_metadata_for_unknown_raises():
    s = _sys()
    s._metadata.pop(AccessibilityFlag.AUTO_LOOT, None)
    with pytest.raises(KeyError):
        s.metadata_for(AccessibilityFlag.AUTO_LOOT)


def test_protanopia_interferes_with_other_colorblind():
    s = _sys()
    md = s.metadata_for(
        AccessibilityFlag.COLORBLIND_PROTANOPIA,
    )
    assert AccessibilityFlag.COLORBLIND_DEUTERANOPIA in (
        md.interferes_with
    )


def test_reduced_motion_recommends_reduced_flash():
    s = _sys()
    md = s.metadata_for(AccessibilityFlag.REDUCED_MOTION)
    assert AccessibilityFlag.REDUCED_FLASH in (
        md.recommended_with
    )


def test_all_flags_count_matches_enum():
    s = _sys()
    assert len(s.all_flags()) == len(list(AccessibilityFlag))


def test_flags_in_visual_category():
    s = _sys()
    out = s.flags_in_category(SettingsCategory.VISUAL)
    assert AccessibilityFlag.COLORBLIND_PROTANOPIA in out
    assert AccessibilityFlag.HIGH_CONTRAST in out


def test_flags_in_motor_category():
    s = _sys()
    out = s.flags_in_category(SettingsCategory.MOTOR)
    assert AccessibilityFlag.STICKY_KEYS in out
    assert AccessibilityFlag.HOLD_TO_TOGGLE in out


def test_flags_in_cognitive_category():
    s = _sys()
    out = s.flags_in_category(SettingsCategory.COGNITIVE)
    assert AccessibilityFlag.TUTORIAL_SLOW_PACE in out


# ---- set / is_active ----

def test_set_flag_enable():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_MOTION, True,
    )
    assert s.is_active(
        "p1", AccessibilityFlag.REDUCED_MOTION,
    )


def test_set_flag_disable():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_MOTION, True,
    )
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_MOTION, False,
    )
    assert not s.is_active(
        "p1", AccessibilityFlag.REDUCED_MOTION,
    )


def test_set_flag_empty_player_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.set_flag(
            "", AccessibilityFlag.REDUCED_MOTION, True,
        )


def test_enabling_interferer_disables_other():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.COLORBLIND_PROTANOPIA, True,
    )
    s.set_flag(
        "p1", AccessibilityFlag.COLORBLIND_DEUTERANOPIA, True,
    )
    assert s.is_active(
        "p1", AccessibilityFlag.COLORBLIND_DEUTERANOPIA,
    )
    assert not s.is_active(
        "p1", AccessibilityFlag.COLORBLIND_PROTANOPIA,
    )


def test_active_flags_for_player():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_MOTION, True,
    )
    s.set_flag(
        "p1", AccessibilityFlag.SUBTITLES_LARGE, True,
    )
    active = s.active_flags_for("p1")
    assert AccessibilityFlag.REDUCED_MOTION in active
    assert AccessibilityFlag.SUBTITLES_LARGE in active
    assert len(active) == 2


# ---- color filter ----

def test_color_filter_default_passthrough():
    s = _sys()
    rgb = (0.5, 0.4, 0.3)
    out = s.apply_color_filter(rgb, "p1")
    assert out == rgb


def test_color_filter_monochromat_returns_grey():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.COLORBLIND_MONOCHROMAT, True,
    )
    out = s.apply_color_filter((1.0, 0.0, 0.0), "p1")
    # All channels should equal the luma (0.299).
    assert abs(out[0] - 0.299) < 1e-6
    assert abs(out[0] - out[1]) < 1e-6
    assert abs(out[1] - out[2]) < 1e-6


def test_color_filter_protanopia_changes_red():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.COLORBLIND_PROTANOPIA, True,
    )
    out = s.apply_color_filter((1.0, 0.0, 0.0), "p1")
    # Red is no longer pure red.
    assert out[0] != 1.0


# ---- screen effects ----

def test_should_show_effect_default_true():
    s = _sys()
    assert s.should_show_screen_effect(
        "p1", "hit_shake_heavy",
    )


def test_reduced_motion_suppresses_hit_shake():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_MOTION, True,
    )
    assert not s.should_show_screen_effect(
        "p1", "hit_shake_heavy",
    )


def test_reduced_motion_does_not_suppress_mb_flash():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_MOTION, True,
    )
    # mb_flash is FLASH not MOTION.
    assert s.should_show_screen_effect("p1", "mb_flash")


def test_reduced_flash_suppresses_mb_flash():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_FLASH, True,
    )
    assert not s.should_show_screen_effect("p1", "mb_flash")


def test_reduced_flash_suppresses_paralyze_crackle():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_FLASH, True,
    )
    assert not s.should_show_screen_effect(
        "p1", "paralyze_static_crackle",
    )


def test_both_flags_combine():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_MOTION, True,
    )
    s.set_flag(
        "p1", AccessibilityFlag.REDUCED_FLASH, True,
    )
    assert not s.should_show_screen_effect(
        "p1", "hit_shake_ultra",
    )
    assert not s.should_show_screen_effect("p1", "mb_flash")


# ---- subtitles ----

def test_subtitle_default():
    s = _sys()
    out = s.subtitle_renderable("p1", "Hello, hero.")
    assert out["text"] == "Hello, hero."
    assert out["size"] == "normal"
    assert out["backplate"] is False
    assert out["always_on"] is False


def test_subtitle_large():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.SUBTITLES_LARGE, True,
    )
    out = s.subtitle_renderable("p1", "Hi.")
    assert out["size"] == "large"


def test_subtitle_high_contrast():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.SUBTITLES_HIGH_CONTRAST, True,
    )
    out = s.subtitle_renderable("p1", "Hi.")
    assert out["backplate"] is True


def test_subtitle_always_on():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.SUBTITLES_ALWAYS_ON, True,
    )
    out = s.subtitle_renderable("p1", "Hi.")
    assert out["always_on"] is True


# ---- TTS ----

def test_narrate_default_off():
    s = _sys()
    assert not s.narrate_to_player("p1", "Hello.")


def test_narrate_tts_enabled():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.TTS_DIALOGUE, True,
    )
    assert s.narrate_to_player("p1", "Hello.")


def test_narrate_screen_reader_enabled():
    s = _sys()
    s.set_flag(
        "p1", AccessibilityFlag.SCREEN_READER_HOOKS, True,
    )
    assert s.narrate_to_player("p1", "Hello.")


# ---- suggestions ----

def test_suggest_for_camera_shake():
    s = _sys()
    out = s.suggest_flags_for(["camera_shake_complaint"])
    assert AccessibilityFlag.REDUCED_MOTION in out


def test_suggest_for_flashing_lights():
    s = _sys()
    out = s.suggest_flags_for(["flashing_lights"])
    assert AccessibilityFlag.REDUCED_FLASH in out


def test_suggest_for_text_too_small():
    s = _sys()
    out = s.suggest_flags_for(["text_too_small"])
    assert AccessibilityFlag.SUBTITLES_LARGE in out


def test_suggest_for_no_complaints_empty():
    s = _sys()
    out = s.suggest_flags_for([])
    assert out == ()


def test_suggest_for_arachnophobia():
    s = _sys()
    out = s.suggest_flags_for(["arachnophobia"])
    assert AccessibilityFlag.ARACHNOPHOBIA_MODE in out


def test_suggest_for_blind_player():
    s = _sys()
    out = s.suggest_flags_for(["blind_player"])
    assert AccessibilityFlag.SCREEN_READER_HOOKS in out


def test_register_flag_replaces():
    s = _sys()
    s.register_flag(
        FlagMetadata(
            flag=AccessibilityFlag.AUTO_LOOT,
            default_off=False,
            settings_panel_category=SettingsCategory.CONTROL,
            interferes_with=frozenset(),
            recommended_with=frozenset(),
            description="custom",
            suggested_by=frozenset(),
        ),
    )
    md = s.metadata_for(AccessibilityFlag.AUTO_LOOT)
    assert md.default_off is False
    assert md.description == "custom"
