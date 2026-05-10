"""Tests for input_mapping."""
from __future__ import annotations

import pytest

from server.input_mapping import (
    DEFAULT_DOUBLE_TAP_MS,
    DEFAULT_REPEAT_DELAY_MS,
    GameAction,
    InputBinding,
    InputDevice,
    InputMappingSystem,
)


def _sys() -> InputMappingSystem:
    return InputMappingSystem()


# ---- enum coverage ----

def test_input_device_count():
    assert len(list(InputDevice)) == 12


def test_input_device_has_keyboard_jis():
    assert InputDevice.KEYBOARD_JIS in list(InputDevice)


def test_input_device_has_eye_tracking():
    assert InputDevice.EYE_TRACKING in list(InputDevice)


def test_input_device_has_motion_control():
    assert InputDevice.MOTION_CONTROL in list(InputDevice)


def test_input_device_has_steam_deck():
    assert InputDevice.GAMEPAD_STEAM_DECK in list(InputDevice)


def test_game_action_count_at_least_40():
    assert len(list(GameAction)) >= 40


def test_game_action_has_macro_10():
    assert GameAction.MACRO_10 in list(GameAction)


def test_game_action_has_action_bar_10():
    assert GameAction.ACTION_BAR_10 in list(GameAction)


def test_game_action_has_dodge():
    assert GameAction.DODGE in list(GameAction)


# ---- defaults ----

def test_default_profiles_loaded_for_qwerty():
    s = _sys()
    assert s.has_default_for(InputDevice.KEYBOARD_QWERTY)


def test_default_profiles_loaded_for_xbox():
    s = _sys()
    assert s.has_default_for(InputDevice.GAMEPAD_XBOX)


def test_default_profiles_loaded_for_playstation():
    s = _sys()
    assert s.has_default_for(InputDevice.GAMEPAD_PLAYSTATION)


def test_default_profiles_loaded_for_steam_deck():
    s = _sys()
    assert s.has_default_for(InputDevice.GAMEPAD_STEAM_DECK)


def test_no_default_for_eye_tracking():
    s = _sys()
    assert not s.has_default_for(InputDevice.EYE_TRACKING)


def test_default_binding_count_meets_target():
    s = _sys()
    # 4 devices x 48 actions = at least 160.
    assert s.default_binding_count() >= 160


def test_defaults_for_returns_bindings():
    s = _sys()
    out = s.defaults_for(InputDevice.KEYBOARD_QWERTY)
    assert len(out) >= 40
    assert all(isinstance(b, InputBinding) for b in out)


# ---- get_binding ----

def test_get_binding_qwerty_w_for_forward():
    s = _sys()
    b = s.get_binding(
        InputDevice.KEYBOARD_QWERTY,
        GameAction.MOVE_FORWARD,
    )
    assert b.primary_input == "W"


def test_get_binding_xbox_a_for_jump():
    s = _sys()
    b = s.get_binding(
        InputDevice.GAMEPAD_XBOX, GameAction.JUMP,
    )
    assert b.primary_input == "A"


def test_get_binding_playstation_r1_for_attack():
    s = _sys()
    b = s.get_binding(
        InputDevice.GAMEPAD_PLAYSTATION,
        GameAction.ATTACK_PRIMARY,
    )
    assert b.primary_input == "R1"


def test_get_binding_unknown_device_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.get_binding(
            InputDevice.EYE_TRACKING, GameAction.JUMP,
        )


def test_hold_for_move_forward_qwerty():
    s = _sys()
    b = s.get_binding(
        InputDevice.KEYBOARD_QWERTY,
        GameAction.MOVE_FORWARD,
    )
    assert b.hold_vs_toggle == "hold"


# ---- rebind ----

def test_rebind_creates_custom():
    s = _sys()
    b = s.rebind(
        "char1", InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "X",
    )
    assert b.primary_input == "X"
    fetched = s.get_binding(
        InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "char1",
    )
    assert fetched.primary_input == "X"


def test_rebind_other_chars_unaffected():
    s = _sys()
    s.rebind(
        "char1", InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "X",
    )
    # Different character still sees the default.
    b = s.get_binding(
        InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "char2",
    )
    assert b.primary_input == "SPACE"


def test_rebind_empty_char_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.rebind(
            "", InputDevice.KEYBOARD_QWERTY,
            GameAction.JUMP, "X",
        )


def test_rebind_empty_primary_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.rebind(
            "char1", InputDevice.KEYBOARD_QWERTY,
            GameAction.JUMP, "",
        )


def test_has_custom_bindings_initial_false():
    s = _sys()
    assert not s.has_custom_bindings(
        "char1", InputDevice.KEYBOARD_QWERTY,
    )


def test_has_custom_bindings_after_rebind_true():
    s = _sys()
    s.rebind(
        "char1", InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "X",
    )
    assert s.has_custom_bindings(
        "char1", InputDevice.KEYBOARD_QWERTY,
    )


# ---- reset ----

def test_reset_to_default_restores():
    s = _sys()
    s.rebind(
        "char1", InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "X",
    )
    removed = s.reset_to_default(
        "char1", InputDevice.KEYBOARD_QWERTY,
    )
    assert removed == 1
    # Default is back.
    b = s.get_binding(
        InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "char1",
    )
    assert b.primary_input == "SPACE"


def test_reset_no_custom_returns_zero():
    s = _sys()
    removed = s.reset_to_default(
        "char1", InputDevice.KEYBOARD_QWERTY,
    )
    assert removed == 0


# ---- list ----

def test_list_actions_count():
    s = _sys()
    actions = s.list_actions()
    assert len(actions) >= 40


def test_list_devices_count():
    s = _sys()
    devices = s.list_devices()
    assert len(devices) == 12


# ---- conflicts ----

def test_no_conflicts_in_default_profile():
    s = _sys()
    conflicts = s.conflicts_for(
        "char1", InputDevice.GAMEPAD_XBOX,
    )
    # The Xbox default does have intentional shared chord
    # roots like "DPAD_RIGHT+A" etc. — those are full strings
    # so they don't conflict with "DPAD_UP".
    # MOUNT/DISMOUNT share "DPAD_UP" — that's an intentional
    # contextual conflict we expose to the player.
    cuckoo = [
        (a, b)
        for (a, b, _) in conflicts
        if {a, b} == {GameAction.MOUNT, GameAction.DISMOUNT}
    ]
    assert len(cuckoo) == 1


def test_rebind_creates_conflict():
    s = _sys()
    s.rebind(
        "char1", InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "W",  # W is move_forward by default
    )
    conflicts = s.conflicts_for(
        "char1", InputDevice.KEYBOARD_QWERTY,
    )
    hits = [
        (a, b)
        for (a, b, inp) in conflicts
        if inp == "W"
    ]
    assert len(hits) >= 1


# ---- import / export ----

def test_export_empty_profile():
    s = _sys()
    blob = s.importable_profile_blob("char1")
    assert blob["char_id"] == "char1"
    assert blob["bindings"] == []


def test_export_after_rebind():
    s = _sys()
    s.rebind(
        "char1", InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "X",
    )
    blob = s.importable_profile_blob("char1")
    assert len(blob["bindings"]) == 1
    row = blob["bindings"][0]
    assert row["primary_input"] == "X"


def test_import_profile_round_trip():
    s = _sys()
    s.rebind(
        "char1", InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "X",
    )
    s.rebind(
        "char1", InputDevice.GAMEPAD_XBOX,
        GameAction.ATTACK_PRIMARY, "Y",
    )
    blob = s.importable_profile_blob("char1")
    s2 = _sys()
    n = s2.import_profile_from("char2", blob)
    assert n == 2
    b = s2.get_binding(
        InputDevice.KEYBOARD_QWERTY,
        GameAction.JUMP, "char2",
    )
    assert b.primary_input == "X"


def test_import_empty_char_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.import_profile_from("", {"bindings": []})


def test_import_missing_bindings_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.import_profile_from("char1", {})


# ---- register custom default ----

def test_register_default_profile_overrides():
    s = _sys()
    s.register_default_profile(
        InputDevice.KEYBOARD_AZERTY,
        [
            InputBinding(
                device=InputDevice.KEYBOARD_AZERTY,
                action=GameAction.MOVE_FORWARD,
                primary_input="Z",
                hold_vs_toggle="hold",
            ),
        ],
    )
    b = s.get_binding(
        InputDevice.KEYBOARD_AZERTY,
        GameAction.MOVE_FORWARD,
    )
    assert b.primary_input == "Z"


def test_register_default_profile_device_mismatch_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.register_default_profile(
            InputDevice.KEYBOARD_AZERTY,
            [
                InputBinding(
                    device=InputDevice.KEYBOARD_QWERTY,
                    action=GameAction.MOVE_FORWARD,
                    primary_input="W",
                ),
            ],
        )


# ---- constants ----

def test_default_repeat_delay_constant():
    assert DEFAULT_REPEAT_DELAY_MS > 0


def test_default_double_tap_constant():
    assert DEFAULT_DOUBLE_TAP_MS > 0


def test_binding_default_repeat_delay():
    b = InputBinding(
        device=InputDevice.KEYBOARD_QWERTY,
        action=GameAction.JUMP,
        primary_input="SPACE",
    )
    assert b.repeat_delay_ms == DEFAULT_REPEAT_DELAY_MS
    assert b.double_tap_threshold_ms == DEFAULT_DOUBLE_TAP_MS
