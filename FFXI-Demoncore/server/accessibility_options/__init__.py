"""Accessibility options — colorblind, motion, subtitles,
screen reader, contrast, tutorial pacing.

Every player can play. That's the philosophy of this
module. Twenty-two AccessibilityFlag values cover the
common needs — colorblind filters (protanopia /
deuteranopia / tritanopia / monochromat), motor (sticky
keys, one-hand mode, hold→toggle), cognitive (tutorial
pace, subtitles, screen reader hooks), audio (TTS
dialogue), photosensitivity (reduced flash, reduced
motion), and content sensitivity (arachnophobia mode
replaces spider geometry with cubes).

Each flag has a settings panel category (VISUAL / MOTOR /
COGNITIVE / AUDIO / CONTROL), a list of other flags it
interferes with (you can't have HIGH_CONTRAST and
COLORBLIND_MONOCHROMAT both on), a list it's recommended
with (REDUCED_FLASH pairs with REDUCED_MOTION), and a
human-readable description.

Three integration surfaces:
- ``apply_color_filter(rgb, player_id)`` — runs the rgb
  through the player's colorblind LUT and returns
  filtered rgb. screen_effects / hud_overlay call this
  on every pixel before display.
- ``should_show_screen_effect(player_id, effect_kind)``
  — REDUCED_MOTION suppresses HIT_SHAKE_HEAVY and
  similar; REDUCED_FLASH suppresses MB_FLASH and
  PARALYZE_STATIC_CRACKLE. screen_effects asks before
  spawning.
- ``subtitle_renderable(player_id, dialogue_line)`` —
  returns the dialogue text formatted with the player's
  preferred size + contrast.

Flag suggestion: ``suggest_flags_for(complaints)`` reads
a set of complaint tokens ("camera_shake_complaint",
"text_too_small", "flashing_lights") and returns a list
of flag recommendations. The flag picker UI uses this to
show "you might also want…".

Public surface
--------------
    AccessibilityFlag enum
    SettingsCategory enum
    FlagMetadata dataclass (frozen)
    AccessibilityOptionsSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AccessibilityFlag(enum.Enum):
    # Visual / colorblindness
    COLORBLIND_PROTANOPIA = "colorblind_protanopia"
    COLORBLIND_DEUTERANOPIA = "colorblind_deuteranopia"
    COLORBLIND_TRITANOPIA = "colorblind_tritanopia"
    COLORBLIND_MONOCHROMAT = "colorblind_monochromat"
    HIGH_CONTRAST = "high_contrast"
    # Motion / photosensitivity
    REDUCED_MOTION = "reduced_motion"
    REDUCED_FLASH = "reduced_flash"
    # Subtitle / text
    SUBTITLES_ALWAYS_ON = "subtitles_always_on"
    SUBTITLES_HIGH_CONTRAST = "subtitles_high_contrast"
    SUBTITLES_LARGE = "subtitles_large"
    # Audio / cognition
    TTS_DIALOGUE = "tts_dialogue"
    SCREEN_READER_HOOKS = "screen_reader_hooks"
    # Motor
    STICKY_KEYS = "sticky_keys"
    HOLD_TO_TOGGLE = "hold_to_toggle"
    ONE_HAND_MODE = "one_hand_mode"
    # Assist
    ASSIST_AIM = "assist_aim"
    ASSIST_TARGETING = "assist_targeting"
    # Pacing
    TUTORIAL_SLOW_PACE = "tutorial_slow_pace"
    TUTORIAL_FAST_PACE = "tutorial_fast_pace"
    # Content sensitivity
    ARACHNOPHOBIA_MODE = "arachnophobia_mode"
    # Convenience
    AUTO_LOOT = "auto_loot"
    AUTO_FOLLOW_LEADER = "auto_follow_leader"


class SettingsCategory(enum.Enum):
    VISUAL = "visual"
    MOTOR = "motor"
    COGNITIVE = "cognitive"
    AUDIO = "audio"
    CONTROL = "control"


@dataclasses.dataclass(frozen=True)
class FlagMetadata:
    flag: AccessibilityFlag
    default_off: bool
    settings_panel_category: SettingsCategory
    interferes_with: frozenset[AccessibilityFlag]
    recommended_with: frozenset[AccessibilityFlag]
    description: str
    suggested_by: frozenset[str]


def _meta(
    flag: AccessibilityFlag,
    category: SettingsCategory,
    description: str,
    *,
    default_off: bool = True,
    interferes: t.Iterable[AccessibilityFlag] = (),
    recommended: t.Iterable[AccessibilityFlag] = (),
    suggested_by: t.Iterable[str] = (),
) -> FlagMetadata:
    return FlagMetadata(
        flag=flag,
        default_off=default_off,
        settings_panel_category=category,
        interferes_with=frozenset(interferes),
        recommended_with=frozenset(recommended),
        description=description,
        suggested_by=frozenset(suggested_by),
    )


# Built-in metadata for every flag. Default-off for all —
# accessibility is opt-in, but every flag is one click away.
_DEFAULT_METADATA: dict[AccessibilityFlag, FlagMetadata] = {
    m.flag: m for m in (
        _meta(
            AccessibilityFlag.COLORBLIND_PROTANOPIA,
            SettingsCategory.VISUAL,
            "Red-cone deficiency: shift reds toward yellow.",
            interferes=(
                AccessibilityFlag.COLORBLIND_DEUTERANOPIA,
                AccessibilityFlag.COLORBLIND_TRITANOPIA,
                AccessibilityFlag.COLORBLIND_MONOCHROMAT,
            ),
            suggested_by=("reds_look_like_browns",),
        ),
        _meta(
            AccessibilityFlag.COLORBLIND_DEUTERANOPIA,
            SettingsCategory.VISUAL,
            "Green-cone deficiency: shift greens toward yellow.",
            interferes=(
                AccessibilityFlag.COLORBLIND_PROTANOPIA,
                AccessibilityFlag.COLORBLIND_TRITANOPIA,
                AccessibilityFlag.COLORBLIND_MONOCHROMAT,
            ),
            suggested_by=("greens_look_like_browns",),
        ),
        _meta(
            AccessibilityFlag.COLORBLIND_TRITANOPIA,
            SettingsCategory.VISUAL,
            "Blue-cone deficiency: shift blues toward cyan.",
            interferes=(
                AccessibilityFlag.COLORBLIND_PROTANOPIA,
                AccessibilityFlag.COLORBLIND_DEUTERANOPIA,
                AccessibilityFlag.COLORBLIND_MONOCHROMAT,
            ),
            suggested_by=("blues_look_like_greens",),
        ),
        _meta(
            AccessibilityFlag.COLORBLIND_MONOCHROMAT,
            SettingsCategory.VISUAL,
            "Full color blindness: render in luminance only.",
            interferes=(
                AccessibilityFlag.COLORBLIND_PROTANOPIA,
                AccessibilityFlag.COLORBLIND_DEUTERANOPIA,
                AccessibilityFlag.COLORBLIND_TRITANOPIA,
                AccessibilityFlag.HIGH_CONTRAST,
            ),
            suggested_by=("colors_indistinguishable",),
        ),
        _meta(
            AccessibilityFlag.HIGH_CONTRAST,
            SettingsCategory.VISUAL,
            "Boost contrast for low-vision users.",
            interferes=(
                AccessibilityFlag.COLORBLIND_MONOCHROMAT,
            ),
            recommended=(
                AccessibilityFlag.SUBTITLES_HIGH_CONTRAST,
            ),
            suggested_by=("text_hard_to_read",),
        ),
        _meta(
            AccessibilityFlag.REDUCED_MOTION,
            SettingsCategory.VISUAL,
            "Suppress camera shake and screen flashes.",
            recommended=(AccessibilityFlag.REDUCED_FLASH,),
            suggested_by=(
                "camera_shake_complaint",
                "motion_sickness",
            ),
        ),
        _meta(
            AccessibilityFlag.REDUCED_FLASH,
            SettingsCategory.VISUAL,
            "Eliminate strobes — photosensitive-safe.",
            recommended=(AccessibilityFlag.REDUCED_MOTION,),
            suggested_by=("flashing_lights", "epilepsy_risk"),
        ),
        _meta(
            AccessibilityFlag.SUBTITLES_ALWAYS_ON,
            SettingsCategory.COGNITIVE,
            "Show subtitles for all spoken dialogue.",
            suggested_by=("audio_hard_to_hear",),
        ),
        _meta(
            AccessibilityFlag.SUBTITLES_HIGH_CONTRAST,
            SettingsCategory.VISUAL,
            "Subtitles render on a solid backplate.",
            recommended=(
                AccessibilityFlag.SUBTITLES_ALWAYS_ON,
            ),
            suggested_by=("subtitles_unreadable",),
        ),
        _meta(
            AccessibilityFlag.SUBTITLES_LARGE,
            SettingsCategory.VISUAL,
            "Increase subtitle font size 1.5x.",
            recommended=(
                AccessibilityFlag.SUBTITLES_ALWAYS_ON,
            ),
            suggested_by=("text_too_small",),
        ),
        _meta(
            AccessibilityFlag.TTS_DIALOGUE,
            SettingsCategory.AUDIO,
            "Synthesize dialogue text to speech.",
            suggested_by=("cannot_read_text",),
        ),
        _meta(
            AccessibilityFlag.SCREEN_READER_HOOKS,
            SettingsCategory.AUDIO,
            "Expose menus to OS screen readers.",
            recommended=(AccessibilityFlag.TTS_DIALOGUE,),
            suggested_by=("blind_player",),
        ),
        _meta(
            AccessibilityFlag.STICKY_KEYS,
            SettingsCategory.MOTOR,
            "Modifier keys latch on first press.",
            suggested_by=("can_only_press_one_key",),
        ),
        _meta(
            AccessibilityFlag.HOLD_TO_TOGGLE,
            SettingsCategory.MOTOR,
            "Held inputs become toggle on/off.",
            suggested_by=("cannot_hold_button",),
        ),
        _meta(
            AccessibilityFlag.ONE_HAND_MODE,
            SettingsCategory.CONTROL,
            "Remap controls so all actions reach one hand.",
            recommended=(
                AccessibilityFlag.STICKY_KEYS,
                AccessibilityFlag.HOLD_TO_TOGGLE,
            ),
            suggested_by=("one_hand_player",),
        ),
        _meta(
            AccessibilityFlag.ASSIST_AIM,
            SettingsCategory.CONTROL,
            "Soft-snap aim toward valid targets.",
            suggested_by=(
                "missing_targets",
                "trouble_aiming",
            ),
        ),
        _meta(
            AccessibilityFlag.ASSIST_TARGETING,
            SettingsCategory.CONTROL,
            "Auto-cycle to the most relevant target.",
            recommended=(AccessibilityFlag.ASSIST_AIM,),
            suggested_by=("trouble_targeting",),
        ),
        _meta(
            AccessibilityFlag.TUTORIAL_SLOW_PACE,
            SettingsCategory.COGNITIVE,
            "Tutorial waits longer between prompts.",
            interferes=(
                AccessibilityFlag.TUTORIAL_FAST_PACE,
            ),
            suggested_by=("tutorial_too_fast",),
        ),
        _meta(
            AccessibilityFlag.TUTORIAL_FAST_PACE,
            SettingsCategory.COGNITIVE,
            "Tutorial skips dwell time.",
            interferes=(
                AccessibilityFlag.TUTORIAL_SLOW_PACE,
            ),
            suggested_by=("tutorial_too_slow",),
        ),
        _meta(
            AccessibilityFlag.ARACHNOPHOBIA_MODE,
            SettingsCategory.COGNITIVE,
            "Replace spider geometry with cubes.",
            suggested_by=("arachnophobia",),
        ),
        _meta(
            AccessibilityFlag.AUTO_LOOT,
            SettingsCategory.CONTROL,
            "Auto-pick-up dropped items in reach.",
            suggested_by=("inventory_friction",),
        ),
        _meta(
            AccessibilityFlag.AUTO_FOLLOW_LEADER,
            SettingsCategory.CONTROL,
            "Auto-pathfind to the party leader.",
            recommended=(
                AccessibilityFlag.ASSIST_TARGETING,
            ),
            suggested_by=("trouble_keeping_up",),
        ),
    )
}


# screen-effect kinds that REDUCED_MOTION suppresses.
_MOTION_SUPPRESS: frozenset[str] = frozenset({
    "hit_shake_light",
    "hit_shake_medium",
    "hit_shake_heavy",
    "hit_shake_ultra",
    "levitate_bob",
    "intoxication_blur",
    "dragon_breath_heat_haze",
})


# screen-effect kinds that REDUCED_FLASH suppresses.
_FLASH_SUPPRESS: frozenset[str] = frozenset({
    "mb_flash",
    "paralyze_static_crackle",
    "charm_pink_haze",
    "petrification_grey_freeze",
})


# Colorblind LUT — a coarse but useful linear mix.
# (For shipping, the engine swaps in the canonical Brettel-
# Vienot-Mollon transform via Open Color Filter — but the
# server layer just labels intent and supplies the mix.)
_COLOR_MIX: dict[
    AccessibilityFlag,
    tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ],
] = {
    AccessibilityFlag.COLORBLIND_PROTANOPIA: (
        (0.56, 0.44, 0.0),
        (0.56, 0.44, 0.0),
        (0.0, 0.24, 0.76),
    ),
    AccessibilityFlag.COLORBLIND_DEUTERANOPIA: (
        (0.62, 0.38, 0.0),
        (0.70, 0.30, 0.0),
        (0.0, 0.30, 0.70),
    ),
    AccessibilityFlag.COLORBLIND_TRITANOPIA: (
        (0.95, 0.05, 0.0),
        (0.0, 0.43, 0.57),
        (0.0, 0.48, 0.52),
    ),
    AccessibilityFlag.COLORBLIND_MONOCHROMAT: (
        (0.299, 0.587, 0.114),
        (0.299, 0.587, 0.114),
        (0.299, 0.587, 0.114),
    ),
}


@dataclasses.dataclass
class AccessibilityOptionsSystem:
    _metadata: dict[AccessibilityFlag, FlagMetadata] = (
        dataclasses.field(default_factory=dict)
    )
    _player_flags: dict[str, set[AccessibilityFlag]] = (
        dataclasses.field(default_factory=dict)
    )

    def __post_init__(self) -> None:
        for flag, md in _DEFAULT_METADATA.items():
            self._metadata[flag] = md

    # ---------------------------------------------- metadata
    def register_flag(self, md: FlagMetadata) -> None:
        self._metadata[md.flag] = md

    def metadata_for(
        self,
        flag: AccessibilityFlag,
    ) -> FlagMetadata:
        if flag not in self._metadata:
            raise KeyError(f"unknown flag: {flag.value}")
        return self._metadata[flag]

    def all_flags(self) -> tuple[AccessibilityFlag, ...]:
        return tuple(AccessibilityFlag)

    def flags_in_category(
        self,
        category: SettingsCategory,
    ) -> tuple[AccessibilityFlag, ...]:
        return tuple(
            md.flag for md in self._metadata.values()
            if md.settings_panel_category == category
        )

    # ---------------------------------------------- per-player
    def set_flag(
        self,
        player_id: str,
        flag: AccessibilityFlag,
        enabled: bool,
    ) -> None:
        if not player_id:
            raise ValueError("player_id required")
        st = self._player_flags.setdefault(player_id, set())
        if enabled:
            # Disable any flags this one interferes with.
            md = self._metadata.get(flag)
            if md:
                for other in md.interferes_with:
                    st.discard(other)
            st.add(flag)
        else:
            st.discard(flag)

    def is_active(
        self,
        player_id: str,
        flag: AccessibilityFlag,
    ) -> bool:
        return flag in self._player_flags.get(player_id, set())

    def active_flags_for(
        self,
        player_id: str,
    ) -> frozenset[AccessibilityFlag]:
        return frozenset(
            self._player_flags.get(player_id, set()),
        )

    # ---------------------------------------------- color
    def apply_color_filter(
        self,
        rgb: tuple[float, float, float],
        player_id: str,
    ) -> tuple[float, float, float]:
        # Pick the first active colorblind flag.
        active = self._player_flags.get(player_id, set())
        for flag in (
            AccessibilityFlag.COLORBLIND_PROTANOPIA,
            AccessibilityFlag.COLORBLIND_DEUTERANOPIA,
            AccessibilityFlag.COLORBLIND_TRITANOPIA,
            AccessibilityFlag.COLORBLIND_MONOCHROMAT,
        ):
            if flag in active:
                row_r, row_g, row_b = _COLOR_MIX[flag]
                r, g, b = rgb
                nr = row_r[0] * r + row_r[1] * g + row_r[2] * b
                ng = row_g[0] * r + row_g[1] * g + row_g[2] * b
                nb = row_b[0] * r + row_b[1] * g + row_b[2] * b
                return (nr, ng, nb)
        return rgb

    # ---------------------------------------------- effects
    def should_show_screen_effect(
        self,
        player_id: str,
        effect_kind: str,
    ) -> bool:
        active = self._player_flags.get(player_id, set())
        if (
            AccessibilityFlag.REDUCED_MOTION in active
            and effect_kind in _MOTION_SUPPRESS
        ):
            return False
        if (
            AccessibilityFlag.REDUCED_FLASH in active
            and effect_kind in _FLASH_SUPPRESS
        ):
            return False
        return True

    # ---------------------------------------------- subtitles
    def subtitle_renderable(
        self,
        player_id: str,
        dialogue_line: str,
    ) -> dict:
        active = self._player_flags.get(player_id, set())
        size = "large" if (
            AccessibilityFlag.SUBTITLES_LARGE in active
        ) else "normal"
        backplate = (
            AccessibilityFlag.SUBTITLES_HIGH_CONTRAST in active
        )
        always_on = (
            AccessibilityFlag.SUBTITLES_ALWAYS_ON in active
        )
        return {
            "text": dialogue_line,
            "size": size,
            "backplate": backplate,
            "always_on": always_on,
        }

    # ---------------------------------------------- TTS
    def narrate_to_player(
        self,
        player_id: str,
        text: str,
    ) -> bool:
        active = self._player_flags.get(player_id, set())
        return AccessibilityFlag.TTS_DIALOGUE in active or (
            AccessibilityFlag.SCREEN_READER_HOOKS in active
        )

    # ---------------------------------------------- suggest
    def suggest_flags_for(
        self,
        complaints: t.Iterable[str],
    ) -> tuple[AccessibilityFlag, ...]:
        complaint_set = set(complaints)
        out: list[AccessibilityFlag] = []
        # Walk in declared enum order for determinism.
        for flag in AccessibilityFlag:
            md = self._metadata.get(flag)
            if md is None:
                continue
            if md.suggested_by & complaint_set:
                out.append(flag)
        return tuple(out)


__all__ = [
    "AccessibilityFlag",
    "SettingsCategory",
    "FlagMetadata",
    "AccessibilityOptionsSystem",
]
