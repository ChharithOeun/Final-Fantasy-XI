"""VR controller bindings — map physical inputs to actions.

VR mode without working input is just a 3D screensaver.
This module owns the per-player mapping from
ControllerInput (a button/trigger/joystick on the HMD's
hand controllers) to GameAction (attack/cast/target etc).

Inputs we track:
    LEFT_TRIGGER         primary left-hand trigger
    RIGHT_TRIGGER        primary right-hand trigger
    LEFT_GRIP            squeeze grip on left
    RIGHT_GRIP           squeeze grip on right
    LEFT_STICK_CLICK     joystick press, left
    RIGHT_STICK_CLICK    joystick press, right
    LEFT_A               face button A, left
    LEFT_B               face button B, left
    RIGHT_A              face button A, right
    RIGHT_B              face button B, right
    LEFT_MENU            menu button, left
    RIGHT_MENU           menu button, right

Actions:
    ATTACK / TARGET_NEAREST / TARGET_NEXT / DISENGAGE
    CAST_HOTBAR_1..6
    OPEN_MENU / CLOSE_MENU
    DODGE_BACKSTEP
    INTERACT (pickup, talk to NPC)
    SUMMON_TRUST
    EMOTE_RING (open emote wheel)

Defaults are sane — a player with no custom binding gets
the canonical layout. Once a player customizes ANYTHING,
their snapshot of the binding map becomes a personal
copy (a profile fork). reset_all() returns them to the
shared defaults.

Two physical inputs cannot map to the same action; one
input cannot map to two actions. The validator enforces
both: set_binding refuses if the action is already on
another input.

Public surface
--------------
    ControllerInput enum
    GameAction enum
    Binding dataclass (frozen)
    VrControllerBindings
        .set_binding(player_id, controller_input,
                     game_action) -> bool
        .clear_binding(player_id, controller_input) -> bool
        .reset_all(player_id) -> bool
        .resolve(player_id, controller_input)
            -> Optional[GameAction]
        .all_bindings(player_id) -> dict[ControllerInput, GameAction]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ControllerInput(str, enum.Enum):
    LEFT_TRIGGER = "left_trigger"
    RIGHT_TRIGGER = "right_trigger"
    LEFT_GRIP = "left_grip"
    RIGHT_GRIP = "right_grip"
    LEFT_STICK_CLICK = "left_stick_click"
    RIGHT_STICK_CLICK = "right_stick_click"
    LEFT_A = "left_a"
    LEFT_B = "left_b"
    RIGHT_A = "right_a"
    RIGHT_B = "right_b"
    LEFT_MENU = "left_menu"
    RIGHT_MENU = "right_menu"


class GameAction(str, enum.Enum):
    ATTACK = "attack"
    TARGET_NEAREST = "target_nearest"
    TARGET_NEXT = "target_next"
    DISENGAGE = "disengage"
    CAST_HOTBAR_1 = "cast_hotbar_1"
    CAST_HOTBAR_2 = "cast_hotbar_2"
    CAST_HOTBAR_3 = "cast_hotbar_3"
    CAST_HOTBAR_4 = "cast_hotbar_4"
    CAST_HOTBAR_5 = "cast_hotbar_5"
    CAST_HOTBAR_6 = "cast_hotbar_6"
    OPEN_MENU = "open_menu"
    CLOSE_MENU = "close_menu"
    DODGE_BACKSTEP = "dodge_backstep"
    INTERACT = "interact"
    SUMMON_TRUST = "summon_trust"
    EMOTE_RING = "emote_ring"


_DEFAULT: dict[ControllerInput, GameAction] = {
    ControllerInput.RIGHT_TRIGGER: GameAction.ATTACK,
    ControllerInput.LEFT_TRIGGER: GameAction.TARGET_NEAREST,
    ControllerInput.LEFT_GRIP: GameAction.DISENGAGE,
    ControllerInput.RIGHT_GRIP: GameAction.INTERACT,
    ControllerInput.LEFT_STICK_CLICK: GameAction.DODGE_BACKSTEP,
    ControllerInput.RIGHT_STICK_CLICK: GameAction.TARGET_NEXT,
    ControllerInput.RIGHT_A: GameAction.CAST_HOTBAR_1,
    ControllerInput.RIGHT_B: GameAction.CAST_HOTBAR_2,
    ControllerInput.LEFT_A: GameAction.CAST_HOTBAR_3,
    ControllerInput.LEFT_B: GameAction.CAST_HOTBAR_4,
    ControllerInput.LEFT_MENU: GameAction.OPEN_MENU,
    ControllerInput.RIGHT_MENU: GameAction.EMOTE_RING,
}


@dataclasses.dataclass(frozen=True)
class Binding:
    controller_input: ControllerInput
    game_action: GameAction


@dataclasses.dataclass
class VrControllerBindings:
    # player_id -> {input -> GameAction | None}
    # None = explicitly cleared (no action bound)
    # Missing player_id = use defaults entirely
    _profile: dict[
        str, dict[
            ControllerInput, t.Optional[GameAction],
        ],
    ] = dataclasses.field(default_factory=dict)

    def _ensure_profile(
        self, player_id: str,
    ) -> dict[ControllerInput, t.Optional[GameAction]]:
        if player_id not in self._profile:
            # Fork the defaults into a personal profile
            self._profile[player_id] = dict(_DEFAULT)
        return self._profile[player_id]

    def set_binding(
        self, *, player_id: str,
        controller_input: ControllerInput,
        game_action: GameAction,
    ) -> bool:
        if not player_id:
            return False
        prof = self._ensure_profile(player_id)
        # Reject if action is already mapped elsewhere
        for inp, act in prof.items():
            if (act == game_action
                    and inp != controller_input):
                return False
        prof[controller_input] = game_action
        return True

    def clear_binding(
        self, *, player_id: str,
        controller_input: ControllerInput,
    ) -> bool:
        prof = self._ensure_profile(player_id)
        if prof.get(controller_input) is None:
            return False  # already unbound
        prof[controller_input] = None
        return True

    def reset_all(self, *, player_id: str) -> bool:
        if player_id not in self._profile:
            return False
        del self._profile[player_id]
        return True

    def resolve(
        self, *, player_id: str,
        controller_input: ControllerInput,
    ) -> t.Optional[GameAction]:
        if player_id in self._profile:
            return self._profile[player_id].get(
                controller_input,
            )
        return _DEFAULT.get(controller_input)

    def all_bindings(
        self, *, player_id: str,
    ) -> dict[ControllerInput, GameAction]:
        """Return only the LIVE bindings (None entries
        omitted)."""
        src = (
            self._profile[player_id]
            if player_id in self._profile
            else _DEFAULT
        )
        return {
            inp: act
            for inp, act in src.items()
            if act is not None
        }


__all__ = [
    "ControllerInput", "GameAction", "Binding",
    "VrControllerBindings",
]
