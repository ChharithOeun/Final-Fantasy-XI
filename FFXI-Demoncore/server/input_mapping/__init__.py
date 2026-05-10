"""Input mapping — keyboard / mouse / gamepad / touch with
accessibility-aware binding.

FFXI shipped with a hard-coded Japanese keyboard + numpad-
driven menu and a PS2 gamepad. That was 2002. Today the
demo has to support every layout a player might bring:
QWERTY, AZERTY, QWERTZ, JIS Japanese, Xbox / PlayStation /
Switch Pro / Steam Deck gamepads, tablets, eye-tracking
for accessibility, and motion controls for the cinematic
kit. This module is the layer that says "the action
ATTACK_PRIMARY is bound to W on QWERTY, Z on AZERTY,
GAMEPAD_RB on Xbox, R1 on PlayStation."

Forty-eight GameAction values cover every demo verb —
locomotion (MOVE_FORWARD/BACK/STRAFE/JUMP/CROUCH/MOUNT/
DISMOUNT/RUN_TOGGLE/WALK_TOGGLE), combat (INTERACT/ATTACK_
PRIMARY/ATTACK_SECONDARY/BLOCK/DODGE/TARGET_NEXT/TARGET_
PREV/TARGET_LOCK), camera (CAMERA_ROTATE_LEFT/RIGHT/ZOOM_
IN/OUT), menus (OPEN_INVENTORY/QUEST_LOG/MAP/MENU_OPEN/
CHAT_OPEN/EMOTE_WHEEL), and the binding hot-row of
MACRO_1..10 + ACTION_BAR_1..10.

Per-device default profiles ship for KEYBOARD_QWERTY,
GAMEPAD_XBOX, GAMEPAD_PLAYSTATION, GAMEPAD_STEAM_DECK.
That's 4 devices x 48 actions = 192 default bindings the
moment the system boots. Players can rebind per-character
(or per-account); reset_to_default puts them back.

Binding metadata captures hold-vs-toggle, repeat delay,
and double-tap threshold — important for accessibility
(STICKY_KEYS replaces holds with toggles), and for
combat (DODGE on double-tap forward).

Profile import/export is a single blob so players can
share configs between machines.

Public surface
--------------
    InputDevice enum
    GameAction enum
    InputBinding dataclass (frozen)
    InputMappingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default repeat delay (ms) for held actions.
DEFAULT_REPEAT_DELAY_MS = 250

# Default double-tap window (ms).
DEFAULT_DOUBLE_TAP_MS = 280


class InputDevice(enum.Enum):
    KEYBOARD_QWERTY = "keyboard_qwerty"
    KEYBOARD_AZERTY = "keyboard_azerty"
    KEYBOARD_QWERTZ = "keyboard_qwertz"
    KEYBOARD_JIS = "keyboard_jis"
    MOUSE = "mouse"
    GAMEPAD_XBOX = "gamepad_xbox"
    GAMEPAD_PLAYSTATION = "gamepad_playstation"
    GAMEPAD_SWITCH_PRO = "gamepad_switch_pro"
    GAMEPAD_STEAM_DECK = "gamepad_steam_deck"
    TOUCH_TABLET = "touch_tablet"
    EYE_TRACKING = "eye_tracking"
    MOTION_CONTROL = "motion_control"


class GameAction(enum.Enum):
    # locomotion
    MOVE_FORWARD = "move_forward"
    MOVE_BACK = "move_back"
    STRAFE_LEFT = "strafe_left"
    STRAFE_RIGHT = "strafe_right"
    JUMP = "jump"
    CROUCH = "crouch"
    MOUNT = "mount"
    DISMOUNT = "dismount"
    RUN_TOGGLE = "run_toggle"
    WALK_TOGGLE = "walk_toggle"
    # combat
    INTERACT = "interact"
    ATTACK_PRIMARY = "attack_primary"
    ATTACK_SECONDARY = "attack_secondary"
    BLOCK = "block"
    DODGE = "dodge"
    TARGET_NEXT = "target_next"
    TARGET_PREV = "target_prev"
    TARGET_LOCK = "target_lock"
    # camera
    CAMERA_ROTATE_LEFT = "camera_rotate_left"
    CAMERA_ROTATE_RIGHT = "camera_rotate_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    # ui / menus
    OPEN_INVENTORY = "open_inventory"
    OPEN_QUEST_LOG = "open_quest_log"
    OPEN_MAP = "open_map"
    MENU_OPEN = "menu_open"
    CHAT_OPEN = "chat_open"
    EMOTE_WHEEL = "emote_wheel"
    # macros
    MACRO_1 = "macro_1"
    MACRO_2 = "macro_2"
    MACRO_3 = "macro_3"
    MACRO_4 = "macro_4"
    MACRO_5 = "macro_5"
    MACRO_6 = "macro_6"
    MACRO_7 = "macro_7"
    MACRO_8 = "macro_8"
    MACRO_9 = "macro_9"
    MACRO_10 = "macro_10"
    # action bar
    ACTION_BAR_1 = "action_bar_1"
    ACTION_BAR_2 = "action_bar_2"
    ACTION_BAR_3 = "action_bar_3"
    ACTION_BAR_4 = "action_bar_4"
    ACTION_BAR_5 = "action_bar_5"
    ACTION_BAR_6 = "action_bar_6"
    ACTION_BAR_7 = "action_bar_7"
    ACTION_BAR_8 = "action_bar_8"
    ACTION_BAR_9 = "action_bar_9"
    ACTION_BAR_10 = "action_bar_10"


@dataclasses.dataclass(frozen=True)
class InputBinding:
    device: InputDevice
    action: GameAction
    primary_input: str
    secondary_input: str = ""
    hold_vs_toggle: str = "press"  # "press" | "hold" | "toggle"
    repeat_delay_ms: int = DEFAULT_REPEAT_DELAY_MS
    double_tap_threshold_ms: int = DEFAULT_DOUBLE_TAP_MS


def _b(
    device: InputDevice,
    action: GameAction,
    primary: str,
    secondary: str = "",
    *,
    hold: str = "press",
) -> InputBinding:
    return InputBinding(
        device=device,
        action=action,
        primary_input=primary,
        secondary_input=secondary,
        hold_vs_toggle=hold,
    )


def _build_keyboard_qwerty() -> tuple[InputBinding, ...]:
    d = InputDevice.KEYBOARD_QWERTY
    return (
        _b(d, GameAction.MOVE_FORWARD, "W", hold="hold"),
        _b(d, GameAction.MOVE_BACK, "S", hold="hold"),
        _b(d, GameAction.STRAFE_LEFT, "A", hold="hold"),
        _b(d, GameAction.STRAFE_RIGHT, "D", hold="hold"),
        _b(d, GameAction.JUMP, "SPACE"),
        _b(d, GameAction.CROUCH, "C", hold="hold"),
        _b(d, GameAction.MOUNT, "Y"),
        _b(d, GameAction.DISMOUNT, "Y"),
        _b(d, GameAction.RUN_TOGGLE, "LSHIFT", hold="toggle"),
        _b(d, GameAction.WALK_TOGGLE, "LCTRL", hold="toggle"),
        _b(d, GameAction.INTERACT, "E"),
        _b(d, GameAction.ATTACK_PRIMARY, "MOUSE_LEFT"),
        _b(d, GameAction.ATTACK_SECONDARY, "MOUSE_RIGHT"),
        _b(d, GameAction.BLOCK, "Q", hold="hold"),
        _b(d, GameAction.DODGE, "SPACE", hold="press"),
        _b(d, GameAction.TARGET_NEXT, "TAB"),
        _b(d, GameAction.TARGET_PREV, "LSHIFT+TAB"),
        _b(d, GameAction.TARGET_LOCK, "MOUSE_MIDDLE"),
        _b(d, GameAction.CAMERA_ROTATE_LEFT, "ARROW_LEFT"),
        _b(d, GameAction.CAMERA_ROTATE_RIGHT, "ARROW_RIGHT"),
        _b(d, GameAction.ZOOM_IN, "MOUSE_WHEEL_UP"),
        _b(d, GameAction.ZOOM_OUT, "MOUSE_WHEEL_DOWN"),
        _b(d, GameAction.OPEN_INVENTORY, "I"),
        _b(d, GameAction.OPEN_QUEST_LOG, "J"),
        _b(d, GameAction.OPEN_MAP, "M"),
        _b(d, GameAction.MENU_OPEN, "ESC"),
        _b(d, GameAction.CHAT_OPEN, "ENTER"),
        _b(d, GameAction.EMOTE_WHEEL, "B"),
        _b(d, GameAction.MACRO_1, "F1"),
        _b(d, GameAction.MACRO_2, "F2"),
        _b(d, GameAction.MACRO_3, "F3"),
        _b(d, GameAction.MACRO_4, "F4"),
        _b(d, GameAction.MACRO_5, "F5"),
        _b(d, GameAction.MACRO_6, "F6"),
        _b(d, GameAction.MACRO_7, "F7"),
        _b(d, GameAction.MACRO_8, "F8"),
        _b(d, GameAction.MACRO_9, "F9"),
        _b(d, GameAction.MACRO_10, "F10"),
        _b(d, GameAction.ACTION_BAR_1, "1"),
        _b(d, GameAction.ACTION_BAR_2, "2"),
        _b(d, GameAction.ACTION_BAR_3, "3"),
        _b(d, GameAction.ACTION_BAR_4, "4"),
        _b(d, GameAction.ACTION_BAR_5, "5"),
        _b(d, GameAction.ACTION_BAR_6, "6"),
        _b(d, GameAction.ACTION_BAR_7, "7"),
        _b(d, GameAction.ACTION_BAR_8, "8"),
        _b(d, GameAction.ACTION_BAR_9, "9"),
        _b(d, GameAction.ACTION_BAR_10, "0"),
    )


def _build_gamepad_xbox() -> tuple[InputBinding, ...]:
    d = InputDevice.GAMEPAD_XBOX
    return (
        _b(d, GameAction.MOVE_FORWARD, "LSTICK_UP", hold="hold"),
        _b(d, GameAction.MOVE_BACK, "LSTICK_DOWN", hold="hold"),
        _b(d, GameAction.STRAFE_LEFT, "LSTICK_LEFT", hold="hold"),
        _b(d, GameAction.STRAFE_RIGHT, "LSTICK_RIGHT", hold="hold"),
        _b(d, GameAction.JUMP, "A"),
        _b(d, GameAction.CROUCH, "B", hold="hold"),
        _b(d, GameAction.MOUNT, "DPAD_UP"),
        _b(d, GameAction.DISMOUNT, "DPAD_UP"),
        _b(d, GameAction.RUN_TOGGLE, "LSTICK_CLICK", hold="toggle"),
        _b(d, GameAction.WALK_TOGGLE, "RSTICK_CLICK", hold="toggle"),
        _b(d, GameAction.INTERACT, "X"),
        _b(d, GameAction.ATTACK_PRIMARY, "RB"),
        _b(d, GameAction.ATTACK_SECONDARY, "RT"),
        _b(d, GameAction.BLOCK, "LB", hold="hold"),
        _b(d, GameAction.DODGE, "B"),
        _b(d, GameAction.TARGET_NEXT, "RB+DPAD_RIGHT"),
        _b(d, GameAction.TARGET_PREV, "RB+DPAD_LEFT"),
        _b(d, GameAction.TARGET_LOCK, "LT"),
        _b(d, GameAction.CAMERA_ROTATE_LEFT, "RSTICK_LEFT"),
        _b(d, GameAction.CAMERA_ROTATE_RIGHT, "RSTICK_RIGHT"),
        _b(d, GameAction.ZOOM_IN, "DPAD_UP"),
        _b(d, GameAction.ZOOM_OUT, "DPAD_DOWN"),
        _b(d, GameAction.OPEN_INVENTORY, "SELECT"),
        _b(d, GameAction.OPEN_QUEST_LOG, "Y"),
        _b(d, GameAction.OPEN_MAP, "START"),
        _b(d, GameAction.MENU_OPEN, "START"),
        _b(d, GameAction.CHAT_OPEN, "SELECT+RB"),
        _b(d, GameAction.EMOTE_WHEEL, "DPAD_LEFT"),
        _b(d, GameAction.MACRO_1, "DPAD_RIGHT+A"),
        _b(d, GameAction.MACRO_2, "DPAD_RIGHT+B"),
        _b(d, GameAction.MACRO_3, "DPAD_RIGHT+X"),
        _b(d, GameAction.MACRO_4, "DPAD_RIGHT+Y"),
        _b(d, GameAction.MACRO_5, "DPAD_LEFT+A"),
        _b(d, GameAction.MACRO_6, "DPAD_LEFT+B"),
        _b(d, GameAction.MACRO_7, "DPAD_LEFT+X"),
        _b(d, GameAction.MACRO_8, "DPAD_LEFT+Y"),
        _b(d, GameAction.MACRO_9, "DPAD_UP+A"),
        _b(d, GameAction.MACRO_10, "DPAD_UP+B"),
        _b(d, GameAction.ACTION_BAR_1, "RB+A"),
        _b(d, GameAction.ACTION_BAR_2, "RB+B"),
        _b(d, GameAction.ACTION_BAR_3, "RB+X"),
        _b(d, GameAction.ACTION_BAR_4, "RB+Y"),
        _b(d, GameAction.ACTION_BAR_5, "LB+A"),
        _b(d, GameAction.ACTION_BAR_6, "LB+B"),
        _b(d, GameAction.ACTION_BAR_7, "LB+X"),
        _b(d, GameAction.ACTION_BAR_8, "LB+Y"),
        _b(d, GameAction.ACTION_BAR_9, "LT+A"),
        _b(d, GameAction.ACTION_BAR_10, "LT+B"),
    )


def _build_gamepad_playstation() -> tuple[InputBinding, ...]:
    d = InputDevice.GAMEPAD_PLAYSTATION
    return (
        _b(d, GameAction.MOVE_FORWARD, "LSTICK_UP", hold="hold"),
        _b(d, GameAction.MOVE_BACK, "LSTICK_DOWN", hold="hold"),
        _b(d, GameAction.STRAFE_LEFT, "LSTICK_LEFT", hold="hold"),
        _b(d, GameAction.STRAFE_RIGHT, "LSTICK_RIGHT", hold="hold"),
        _b(d, GameAction.JUMP, "CROSS"),
        _b(d, GameAction.CROUCH, "CIRCLE", hold="hold"),
        _b(d, GameAction.MOUNT, "DPAD_UP"),
        _b(d, GameAction.DISMOUNT, "DPAD_UP"),
        _b(d, GameAction.RUN_TOGGLE, "L3", hold="toggle"),
        _b(d, GameAction.WALK_TOGGLE, "R3", hold="toggle"),
        _b(d, GameAction.INTERACT, "SQUARE"),
        _b(d, GameAction.ATTACK_PRIMARY, "R1"),
        _b(d, GameAction.ATTACK_SECONDARY, "R2"),
        _b(d, GameAction.BLOCK, "L1", hold="hold"),
        _b(d, GameAction.DODGE, "CIRCLE"),
        _b(d, GameAction.TARGET_NEXT, "R1+DPAD_RIGHT"),
        _b(d, GameAction.TARGET_PREV, "R1+DPAD_LEFT"),
        _b(d, GameAction.TARGET_LOCK, "L2"),
        _b(d, GameAction.CAMERA_ROTATE_LEFT, "RSTICK_LEFT"),
        _b(d, GameAction.CAMERA_ROTATE_RIGHT, "RSTICK_RIGHT"),
        _b(d, GameAction.ZOOM_IN, "DPAD_UP"),
        _b(d, GameAction.ZOOM_OUT, "DPAD_DOWN"),
        _b(d, GameAction.OPEN_INVENTORY, "TOUCHPAD"),
        _b(d, GameAction.OPEN_QUEST_LOG, "TRIANGLE"),
        _b(d, GameAction.OPEN_MAP, "OPTIONS"),
        _b(d, GameAction.MENU_OPEN, "OPTIONS"),
        _b(d, GameAction.CHAT_OPEN, "TOUCHPAD+R1"),
        _b(d, GameAction.EMOTE_WHEEL, "DPAD_LEFT"),
        _b(d, GameAction.MACRO_1, "DPAD_RIGHT+CROSS"),
        _b(d, GameAction.MACRO_2, "DPAD_RIGHT+CIRCLE"),
        _b(d, GameAction.MACRO_3, "DPAD_RIGHT+SQUARE"),
        _b(d, GameAction.MACRO_4, "DPAD_RIGHT+TRIANGLE"),
        _b(d, GameAction.MACRO_5, "DPAD_LEFT+CROSS"),
        _b(d, GameAction.MACRO_6, "DPAD_LEFT+CIRCLE"),
        _b(d, GameAction.MACRO_7, "DPAD_LEFT+SQUARE"),
        _b(d, GameAction.MACRO_8, "DPAD_LEFT+TRIANGLE"),
        _b(d, GameAction.MACRO_9, "DPAD_UP+CROSS"),
        _b(d, GameAction.MACRO_10, "DPAD_UP+CIRCLE"),
        _b(d, GameAction.ACTION_BAR_1, "R1+CROSS"),
        _b(d, GameAction.ACTION_BAR_2, "R1+CIRCLE"),
        _b(d, GameAction.ACTION_BAR_3, "R1+SQUARE"),
        _b(d, GameAction.ACTION_BAR_4, "R1+TRIANGLE"),
        _b(d, GameAction.ACTION_BAR_5, "L1+CROSS"),
        _b(d, GameAction.ACTION_BAR_6, "L1+CIRCLE"),
        _b(d, GameAction.ACTION_BAR_7, "L1+SQUARE"),
        _b(d, GameAction.ACTION_BAR_8, "L1+TRIANGLE"),
        _b(d, GameAction.ACTION_BAR_9, "L2+CROSS"),
        _b(d, GameAction.ACTION_BAR_10, "L2+CIRCLE"),
    )


def _build_gamepad_steam_deck() -> tuple[InputBinding, ...]:
    d = InputDevice.GAMEPAD_STEAM_DECK
    return (
        _b(d, GameAction.MOVE_FORWARD, "LSTICK_UP", hold="hold"),
        _b(d, GameAction.MOVE_BACK, "LSTICK_DOWN", hold="hold"),
        _b(d, GameAction.STRAFE_LEFT, "LSTICK_LEFT", hold="hold"),
        _b(d, GameAction.STRAFE_RIGHT, "LSTICK_RIGHT", hold="hold"),
        _b(d, GameAction.JUMP, "A"),
        _b(d, GameAction.CROUCH, "B", hold="hold"),
        _b(d, GameAction.MOUNT, "DPAD_UP"),
        _b(d, GameAction.DISMOUNT, "DPAD_UP"),
        _b(d, GameAction.RUN_TOGGLE, "L4", hold="toggle"),
        _b(d, GameAction.WALK_TOGGLE, "R4", hold="toggle"),
        _b(d, GameAction.INTERACT, "X"),
        _b(d, GameAction.ATTACK_PRIMARY, "R1"),
        _b(d, GameAction.ATTACK_SECONDARY, "R2"),
        _b(d, GameAction.BLOCK, "L1", hold="hold"),
        _b(d, GameAction.DODGE, "B"),
        _b(d, GameAction.TARGET_NEXT, "RIGHT_TRACKPAD_SWIPE_RIGHT"),
        _b(d, GameAction.TARGET_PREV, "RIGHT_TRACKPAD_SWIPE_LEFT"),
        _b(d, GameAction.TARGET_LOCK, "L2"),
        _b(d, GameAction.CAMERA_ROTATE_LEFT, "RIGHT_TRACKPAD_LEFT"),
        _b(d, GameAction.CAMERA_ROTATE_RIGHT, "RIGHT_TRACKPAD_RIGHT"),
        _b(d, GameAction.ZOOM_IN, "RIGHT_TRACKPAD_UP"),
        _b(d, GameAction.ZOOM_OUT, "RIGHT_TRACKPAD_DOWN"),
        _b(d, GameAction.OPEN_INVENTORY, "L5"),
        _b(d, GameAction.OPEN_QUEST_LOG, "Y"),
        _b(d, GameAction.OPEN_MAP, "START"),
        _b(d, GameAction.MENU_OPEN, "START"),
        _b(d, GameAction.CHAT_OPEN, "SELECT"),
        _b(d, GameAction.EMOTE_WHEEL, "DPAD_LEFT"),
        _b(d, GameAction.MACRO_1, "DPAD_RIGHT+A"),
        _b(d, GameAction.MACRO_2, "DPAD_RIGHT+B"),
        _b(d, GameAction.MACRO_3, "DPAD_RIGHT+X"),
        _b(d, GameAction.MACRO_4, "DPAD_RIGHT+Y"),
        _b(d, GameAction.MACRO_5, "DPAD_LEFT+A"),
        _b(d, GameAction.MACRO_6, "DPAD_LEFT+B"),
        _b(d, GameAction.MACRO_7, "DPAD_LEFT+X"),
        _b(d, GameAction.MACRO_8, "DPAD_LEFT+Y"),
        _b(d, GameAction.MACRO_9, "DPAD_UP+A"),
        _b(d, GameAction.MACRO_10, "DPAD_UP+B"),
        _b(d, GameAction.ACTION_BAR_1, "R1+A"),
        _b(d, GameAction.ACTION_BAR_2, "R1+B"),
        _b(d, GameAction.ACTION_BAR_3, "R1+X"),
        _b(d, GameAction.ACTION_BAR_4, "R1+Y"),
        _b(d, GameAction.ACTION_BAR_5, "L1+A"),
        _b(d, GameAction.ACTION_BAR_6, "L1+B"),
        _b(d, GameAction.ACTION_BAR_7, "L1+X"),
        _b(d, GameAction.ACTION_BAR_8, "L1+Y"),
        _b(d, GameAction.ACTION_BAR_9, "L2+A"),
        _b(d, GameAction.ACTION_BAR_10, "L2+B"),
    )


# Built-in default profiles, registered at construction.
_BUILTIN_PROFILES: dict[
    InputDevice, tuple[InputBinding, ...],
] = {
    InputDevice.KEYBOARD_QWERTY: _build_keyboard_qwerty(),
    InputDevice.GAMEPAD_XBOX: _build_gamepad_xbox(),
    InputDevice.GAMEPAD_PLAYSTATION: _build_gamepad_playstation(),
    InputDevice.GAMEPAD_STEAM_DECK: _build_gamepad_steam_deck(),
}


@dataclasses.dataclass
class InputMappingSystem:
    _defaults: dict[
        InputDevice, dict[GameAction, InputBinding],
    ] = dataclasses.field(default_factory=dict)
    # (char_id, device) -> {action -> binding}
    _custom: dict[
        tuple[str, InputDevice], dict[GameAction, InputBinding],
    ] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        for device, bindings in _BUILTIN_PROFILES.items():
            self._defaults[device] = {
                b.action: b for b in bindings
            }

    # ---------------------------------------------- profiles
    def register_default_profile(
        self,
        device: InputDevice,
        bindings: t.Iterable[InputBinding],
    ) -> None:
        mapping: dict[GameAction, InputBinding] = {}
        for b in bindings:
            if b.device != device:
                raise ValueError(
                    "binding.device must match arg device",
                )
            mapping[b.action] = b
        self._defaults[device] = mapping

    def has_default_for(self, device: InputDevice) -> bool:
        return device in self._defaults

    def defaults_for(
        self,
        device: InputDevice,
    ) -> tuple[InputBinding, ...]:
        if device not in self._defaults:
            return ()
        return tuple(self._defaults[device].values())

    def default_binding_count(self) -> int:
        return sum(len(m) for m in self._defaults.values())

    # ---------------------------------------------- list
    def list_actions(self) -> tuple[GameAction, ...]:
        return tuple(GameAction)

    def list_devices(self) -> tuple[InputDevice, ...]:
        return tuple(InputDevice)

    # ---------------------------------------------- get
    def get_binding(
        self,
        device: InputDevice,
        action: GameAction,
        char_id: str = "",
    ) -> InputBinding:
        # Per-char override wins.
        key = (char_id, device)
        if char_id and key in self._custom:
            if action in self._custom[key]:
                return self._custom[key][action]
        # Fall back to default.
        if device not in self._defaults:
            raise KeyError(
                f"no default profile for {device.value}",
            )
        if action not in self._defaults[device]:
            raise KeyError(
                f"no default binding for "
                f"{device.value}/{action.value}",
            )
        return self._defaults[device][action]

    # ---------------------------------------------- rebind
    def rebind(
        self,
        char_id: str,
        device: InputDevice,
        action: GameAction,
        new_primary: str,
        new_secondary: str = "",
        *,
        hold: str = "press",
    ) -> InputBinding:
        if not char_id:
            raise ValueError("char_id required")
        if not new_primary:
            raise ValueError("new_primary required")
        key = (char_id, device)
        if key not in self._custom:
            self._custom[key] = {}
        binding = InputBinding(
            device=device,
            action=action,
            primary_input=new_primary,
            secondary_input=new_secondary,
            hold_vs_toggle=hold,
        )
        self._custom[key][action] = binding
        return binding

    def reset_to_default(
        self,
        char_id: str,
        device: InputDevice,
    ) -> int:
        key = (char_id, device)
        removed = len(self._custom.get(key, {}))
        self._custom.pop(key, None)
        return removed

    def has_custom_bindings(
        self,
        char_id: str,
        device: InputDevice,
    ) -> bool:
        return (char_id, device) in self._custom

    # ---------------------------------------------- conflicts
    def conflicts_for(
        self,
        char_id: str,
        device: InputDevice,
    ) -> tuple[tuple[GameAction, GameAction, str], ...]:
        """Returns (action_a, action_b, shared_input)."""
        bindings: dict[GameAction, InputBinding] = {}
        if device in self._defaults:
            for action, b in self._defaults[device].items():
                bindings[action] = b
        key = (char_id, device)
        if char_id and key in self._custom:
            for action, b in self._custom[key].items():
                bindings[action] = b
        # Build reverse index of input -> [actions].
        rev: dict[str, list[GameAction]] = {}
        for action, b in bindings.items():
            rev.setdefault(b.primary_input, []).append(action)
        out: list[tuple[GameAction, GameAction, str]] = []
        for inp, actions in rev.items():
            if len(actions) > 1:
                # Sort by enum value for determinism.
                sorted_actions = sorted(
                    actions, key=lambda a: a.value,
                )
                for i in range(len(sorted_actions)):
                    for j in range(i + 1, len(sorted_actions)):
                        out.append((
                            sorted_actions[i],
                            sorted_actions[j],
                            inp,
                        ))
        return tuple(out)

    # ---------------------------------------------- import/export
    def importable_profile_blob(
        self,
        char_id: str,
    ) -> dict:
        out: dict = {"char_id": char_id, "bindings": []}
        for (cid, device), mapping in self._custom.items():
            if cid != char_id:
                continue
            for action, b in mapping.items():
                out["bindings"].append({
                    "device": device.value,
                    "action": action.value,
                    "primary_input": b.primary_input,
                    "secondary_input": b.secondary_input,
                    "hold_vs_toggle": b.hold_vs_toggle,
                })
        return out

    def import_profile_from(
        self,
        char_id: str,
        blob: dict,
    ) -> int:
        if not char_id:
            raise ValueError("char_id required")
        if "bindings" not in blob:
            raise ValueError("missing 'bindings'")
        imported = 0
        for row in blob["bindings"]:
            device = InputDevice(row["device"])
            action = GameAction(row["action"])
            self.rebind(
                char_id, device, action,
                row["primary_input"],
                row.get("secondary_input", ""),
                hold=row.get("hold_vs_toggle", "press"),
            )
            imported += 1
        return imported


__all__ = [
    "InputDevice",
    "GameAction",
    "InputBinding",
    "InputMappingSystem",
    "DEFAULT_REPEAT_DELAY_MS",
    "DEFAULT_DOUBLE_TAP_MS",
]
