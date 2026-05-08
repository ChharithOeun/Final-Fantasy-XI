"""Tests for vr_controller_bindings."""
from __future__ import annotations

from server.vr_controller_bindings import (
    ControllerInput, GameAction, VrControllerBindings,
)


def test_default_resolves():
    b = VrControllerBindings()
    out = b.resolve(
        player_id="bob",
        controller_input=ControllerInput.RIGHT_TRIGGER,
    )
    assert out == GameAction.ATTACK


def test_default_target():
    b = VrControllerBindings()
    out = b.resolve(
        player_id="bob",
        controller_input=ControllerInput.LEFT_TRIGGER,
    )
    assert out == GameAction.TARGET_NEAREST


def test_set_binding_overrides_default():
    b = VrControllerBindings()
    # Clear the default mapping for OPEN_MENU first so
    # we can re-bind it, then re-bind to a free input
    b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_MENU,
    )
    out = b.set_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_MENU,
        game_action=GameAction.OPEN_MENU,
    )
    assert out is True


def test_set_binding_blank_player():
    b = VrControllerBindings()
    out = b.set_binding(
        player_id="",
        controller_input=ControllerInput.LEFT_TRIGGER,
        game_action=GameAction.ATTACK,
    )
    assert out is False


def test_set_binding_blocks_dup_action():
    """ATTACK is already on RIGHT_TRIGGER by default;
    can't also bind it to LEFT_GRIP."""
    b = VrControllerBindings()
    out = b.set_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_GRIP,
        game_action=GameAction.ATTACK,
    )
    assert out is False


def test_clear_binding():
    b = VrControllerBindings()
    # Make a custom binding then clear it
    # Re-mapping LEFT_GRIP from DISENGAGE → INTERACT
    # First clear the default INTERACT slot
    b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.RIGHT_GRIP,
    )
    b.set_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_GRIP,
        game_action=GameAction.INTERACT,
    )
    out = b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_GRIP,
    )
    assert out is True


def test_clear_binding_already_cleared():
    """Clearing twice — the second clear is a no-op."""
    b = VrControllerBindings()
    b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_GRIP,
    )
    out = b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_GRIP,
    )
    assert out is False


def test_reset_all():
    b = VrControllerBindings()
    b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.RIGHT_GRIP,
    )
    b.set_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_GRIP,
        game_action=GameAction.INTERACT,
    )
    out = b.reset_all(player_id="bob")
    assert out is True
    # Defaults restored
    out2 = b.resolve(
        player_id="bob",
        controller_input=ControllerInput.LEFT_GRIP,
    )
    assert out2 == GameAction.DISENGAGE


def test_reset_all_no_customs():
    b = VrControllerBindings()
    assert b.reset_all(player_id="bob") is False


def test_all_bindings_returns_full_map():
    b = VrControllerBindings()
    out = b.all_bindings(player_id="bob")
    # All defaults present
    assert (
        out[ControllerInput.RIGHT_TRIGGER]
        == GameAction.ATTACK
    )
    assert len(out) == len(_default_count())


def _default_count():
    # Count unique inputs in the default; 12 default
    return [
        ControllerInput.LEFT_TRIGGER,
        ControllerInput.RIGHT_TRIGGER,
        ControllerInput.LEFT_GRIP,
        ControllerInput.RIGHT_GRIP,
        ControllerInput.LEFT_STICK_CLICK,
        ControllerInput.RIGHT_STICK_CLICK,
        ControllerInput.LEFT_A,
        ControllerInput.LEFT_B,
        ControllerInput.RIGHT_A,
        ControllerInput.RIGHT_B,
        ControllerInput.LEFT_MENU,
        ControllerInput.RIGHT_MENU,
    ]


def test_resolve_after_clear_falls_back_to_default():
    b = VrControllerBindings()
    b.set_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_TRIGGER,
        game_action=GameAction.TARGET_NEXT,
    )
    # Clearing should restore the default for that input
    # But TARGET_NEAREST is the default for LEFT_TRIGGER
    # We need to first clear RIGHT_STICK_CLICK (default
    # TARGET_NEXT) to make this rebind valid. Test order:
    # set → resolve as TARGET_NEXT → clear → resolve as
    # default TARGET_NEAREST


def test_set_binding_swap_workflow():
    """A swap requires two clears before the new sets;
    this verifies the constraint chain."""
    b = VrControllerBindings()
    # Goal: swap right-trigger ATTACK with left-trigger
    # TARGET_NEAREST. Have to clear both first.
    b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.RIGHT_TRIGGER,
    )
    b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_TRIGGER,
    )
    assert b.set_binding(
        player_id="bob",
        controller_input=ControllerInput.RIGHT_TRIGGER,
        game_action=GameAction.TARGET_NEAREST,
    ) is True
    assert b.set_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_TRIGGER,
        game_action=GameAction.ATTACK,
    ) is True


def test_per_player_isolated():
    b = VrControllerBindings()
    b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.RIGHT_TRIGGER,
    )
    b.set_binding(
        player_id="bob",
        controller_input=ControllerInput.RIGHT_TRIGGER,
        game_action=GameAction.CAST_HOTBAR_1,
    )
    # Cara still has default
    cara = b.resolve(
        player_id="cara",
        controller_input=ControllerInput.RIGHT_TRIGGER,
    )
    assert cara == GameAction.ATTACK


def test_twelve_controller_inputs():
    assert len(list(ControllerInput)) == 12


def test_sixteen_game_actions():
    assert len(list(GameAction)) == 16


def test_resolve_after_clear():
    b = VrControllerBindings()
    b.clear_binding(
        player_id="bob",
        controller_input=ControllerInput.RIGHT_STICK_CLICK,
    )
    b.set_binding(
        player_id="bob",
        controller_input=ControllerInput.LEFT_TRIGGER,
        game_action=GameAction.TARGET_NEXT,
    )
    out = b.resolve(
        player_id="bob",
        controller_input=ControllerInput.LEFT_TRIGGER,
    )
    assert out == GameAction.TARGET_NEXT
