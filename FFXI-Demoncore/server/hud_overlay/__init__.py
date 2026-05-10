"""HUD overlay — live-action heads-up display.

The visible_health philosophy says "read the world
physically; the HUD is backup". So the HUD is here, but it
is subtle, transparent, and contextual. In COMBAT it lights
up to full opacity because the player needs the numbers.
In EXPLORATION it ghosts down to 0.4 because the player is
supposed to be reading posture and breath, not a bar. In
DIALOGUE it disappears entirely except for the casting bar
(if you're casting through a conversation, you still need
to see the cast). In CINEMATIC it disappears completely —
the camera director owns the frame.

HudElement enumerates every UI thing that paints over the
3D view: health/MP/TP gauges, target frames, party frame,
casting bar, recast timers, status icons, action bar,
chat, minimap, compass, conquest tally, region banner,
plus three delegating elements (DAMAGE_NUMBERS_FLOATING,
SKILLCHAIN_SUGGEST_OVERLAY, DPS_METER_OVERLAY) that defer
to their dedicated modules.

Each element has an opacity_target (where it wants to be)
and an opacity_current (where it is now). tick(dt) eases
current toward target at fade_speed_s. set_mode flips
opacity_targets per the mode rules; tick smooths the
transition.

User preference hud_density is a multiplier on top of the
mode rules — MINIMAL = 0.4 of nominal, STANDARD = 0.7,
DENSE = 1.0 (full).

Public surface
--------------
    HudElement enum
    HudMode enum
    HudDensity enum
    HudElementSpec dataclass (frozen)
    HudOverlaySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class HudElement(enum.Enum):
    HEALTH_GAUGE = "health_gauge"
    MP_GAUGE = "mp_gauge"
    TP_GAUGE = "tp_gauge"
    TARGET_FRAME = "target_frame"
    SUB_TARGET_FRAME = "sub_target_frame"
    PARTY_FRAME = "party_frame"
    CASTING_BAR = "casting_bar"
    RECAST_TIMERS_GRID = "recast_timers_grid"
    STATUS_ICONS_ROW = "status_icons_row"
    ACTION_BAR = "action_bar"
    CHAT_WINDOW = "chat_window"
    MINIMAP = "minimap"
    WAYFINDER_COMPASS = "wayfinder_compass"
    CONQUEST_TALLY_TICKER = "conquest_tally_ticker"
    REGION_NAME_BANNER = "region_name_banner"
    DAMAGE_NUMBERS_FLOATING = "damage_numbers_floating"
    SKILLCHAIN_SUGGEST_OVERLAY = "skillchain_suggest_overlay"
    DPS_METER_OVERLAY = "dps_meter_overlay"
    MENTOR_TAG = "mentor_tag"
    NEW_PLAYER_HELPER = "new_player_helper"


class HudMode(enum.Enum):
    COMBAT = "combat"
    EXPLORATION = "exploration"
    DIALOGUE = "dialogue"
    CINEMATIC = "cinematic"
    MAP_OPEN = "map_open"
    MENU_OPEN = "menu_open"


class HudDensity(enum.Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    DENSE = "dense"


_DENSITY_MULT: dict[HudDensity, float] = {
    HudDensity.MINIMAL: 0.4,
    HudDensity.STANDARD: 0.7,
    HudDensity.DENSE: 1.0,
}


# Default visibility map: element -> (visible-in-modes set,
# nominal opacity in those modes, opacity_when_not_visible).
# In EXPLORATION the gauges ghost down to 0.4 baseline; in
# COMBAT they go full; in DIALOGUE/CINEMATIC most hide
# entirely. CASTING_BAR is the exception that survives
# DIALOGUE.
_DEFAULT_RULES: dict[
    HudElement, tuple[set[HudMode], float, float],
] = {
    HudElement.HEALTH_GAUGE: (
        {HudMode.COMBAT, HudMode.EXPLORATION,
         HudMode.MAP_OPEN, HudMode.MENU_OPEN},
        1.0, 0.0,
    ),
    HudElement.MP_GAUGE: (
        {HudMode.COMBAT, HudMode.EXPLORATION,
         HudMode.MAP_OPEN, HudMode.MENU_OPEN},
        1.0, 0.0,
    ),
    HudElement.TP_GAUGE: (
        {HudMode.COMBAT, HudMode.EXPLORATION,
         HudMode.MAP_OPEN, HudMode.MENU_OPEN},
        1.0, 0.0,
    ),
    HudElement.TARGET_FRAME: (
        {HudMode.COMBAT}, 1.0, 0.0,
    ),
    HudElement.SUB_TARGET_FRAME: (
        {HudMode.COMBAT}, 1.0, 0.0,
    ),
    HudElement.PARTY_FRAME: (
        {HudMode.COMBAT, HudMode.EXPLORATION,
         HudMode.MAP_OPEN}, 1.0, 0.0,
    ),
    HudElement.CASTING_BAR: (
        {HudMode.COMBAT, HudMode.EXPLORATION,
         HudMode.DIALOGUE, HudMode.MAP_OPEN,
         HudMode.MENU_OPEN}, 1.0, 0.0,
    ),
    HudElement.RECAST_TIMERS_GRID: (
        {HudMode.COMBAT, HudMode.EXPLORATION}, 1.0, 0.0,
    ),
    HudElement.STATUS_ICONS_ROW: (
        {HudMode.COMBAT, HudMode.EXPLORATION,
         HudMode.MENU_OPEN}, 1.0, 0.0,
    ),
    HudElement.ACTION_BAR: (
        {HudMode.COMBAT, HudMode.EXPLORATION,
         HudMode.MENU_OPEN}, 1.0, 0.0,
    ),
    HudElement.CHAT_WINDOW: (
        {HudMode.COMBAT, HudMode.EXPLORATION,
         HudMode.DIALOGUE, HudMode.MAP_OPEN,
         HudMode.MENU_OPEN}, 1.0, 0.0,
    ),
    HudElement.MINIMAP: (
        {HudMode.COMBAT, HudMode.EXPLORATION}, 1.0, 0.0,
    ),
    HudElement.WAYFINDER_COMPASS: (
        {HudMode.EXPLORATION}, 1.0, 0.0,
    ),
    HudElement.CONQUEST_TALLY_TICKER: (
        {HudMode.EXPLORATION, HudMode.MAP_OPEN}, 1.0, 0.0,
    ),
    HudElement.REGION_NAME_BANNER: (
        {HudMode.EXPLORATION}, 1.0, 0.0,
    ),
    HudElement.DAMAGE_NUMBERS_FLOATING: (
        {HudMode.COMBAT, HudMode.EXPLORATION}, 1.0, 0.0,
    ),
    HudElement.SKILLCHAIN_SUGGEST_OVERLAY: (
        {HudMode.COMBAT}, 1.0, 0.0,
    ),
    HudElement.DPS_METER_OVERLAY: (
        {HudMode.COMBAT}, 1.0, 0.0,
    ),
    HudElement.MENTOR_TAG: (
        {HudMode.COMBAT, HudMode.EXPLORATION}, 1.0, 0.0,
    ),
    HudElement.NEW_PLAYER_HELPER: (
        {HudMode.EXPLORATION, HudMode.MAP_OPEN}, 1.0, 0.0,
    ),
}


# Elements that ghost down (instead of full) in EXPLORATION
# — matches the visible_health philosophy of "read posture
# if calm".
_GHOST_IN_EXPLORATION: frozenset[HudElement] = frozenset({
    HudElement.HEALTH_GAUGE,
    HudElement.MP_GAUGE,
    HudElement.TP_GAUGE,
})
_EXPLORATION_GHOST_OPACITY = 0.4


@dataclasses.dataclass(frozen=True)
class HudElementSpec:
    element: HudElement
    opacity_target: float
    opacity_current: float
    fade_speed_s: float
    visible_in_modes: tuple[HudMode, ...]
    opacity_when_not_visible: float


@dataclasses.dataclass
class _ElementInternal:
    element: HudElement
    opacity_target: float
    opacity_current: float
    fade_speed_s: float
    visible_in_modes: set[HudMode]
    opacity_when_not_visible: float
    nominal_opacity: float


@dataclasses.dataclass
class HudOverlaySystem:
    _elements: dict[
        HudElement, _ElementInternal,
    ] = dataclasses.field(default_factory=dict)
    _current_mode: HudMode = HudMode.EXPLORATION
    _density: HudDensity = HudDensity.STANDARD

    # ---------------------------------------------- register
    def register_element(self, spec: HudElementSpec) -> None:
        if spec.element in self._elements:
            raise ValueError(
                f"duplicate element: {spec.element.value}",
            )
        if not (0.0 <= spec.opacity_target <= 1.0):
            raise ValueError(
                "opacity_target must be in [0, 1]",
            )
        if not (0.0 <= spec.opacity_current <= 1.0):
            raise ValueError(
                "opacity_current must be in [0, 1]",
            )
        if spec.fade_speed_s < 0:
            raise ValueError("fade_speed_s must be >= 0")
        if not (
            0.0 <= spec.opacity_when_not_visible <= 1.0
        ):
            raise ValueError(
                "opacity_when_not_visible must be in [0, 1]",
            )
        internal = _ElementInternal(
            element=spec.element,
            opacity_target=spec.opacity_target,
            opacity_current=spec.opacity_current,
            fade_speed_s=spec.fade_speed_s,
            visible_in_modes=set(spec.visible_in_modes),
            opacity_when_not_visible=(
                spec.opacity_when_not_visible
            ),
            nominal_opacity=spec.opacity_target,
        )
        self._elements[spec.element] = internal

    def populate_defaults(self) -> int:
        n = 0
        for elem, (modes, nominal, hidden) in (
            _DEFAULT_RULES.items()
        ):
            self.register_element(HudElementSpec(
                element=elem,
                opacity_target=nominal,
                opacity_current=nominal,
                fade_speed_s=0.25,
                visible_in_modes=tuple(modes),
                opacity_when_not_visible=hidden,
            ))
            n += 1
        return n

    def element_count(self) -> int:
        return len(self._elements)

    # ---------------------------------------------- modes
    def set_mode(self, mode: HudMode) -> HudMode:
        prev = self._current_mode
        self._current_mode = mode
        # Update every element's opacity_target.
        for internal in self._elements.values():
            target = self._compute_target(internal, mode)
            internal.opacity_target = target
        return prev

    def current_mode(self) -> HudMode:
        return self._current_mode

    def _compute_target(
        self,
        internal: _ElementInternal,
        mode: HudMode,
    ) -> float:
        # CINEMATIC hides everything.
        if mode == HudMode.CINEMATIC:
            return 0.0
        if mode in internal.visible_in_modes:
            base = internal.nominal_opacity
            # Ghost gauges in EXPLORATION
            if (
                mode == HudMode.EXPLORATION
                and internal.element in _GHOST_IN_EXPLORATION
            ):
                base = _EXPLORATION_GHOST_OPACITY
            return base * _DENSITY_MULT[self._density]
        return internal.opacity_when_not_visible

    # ---------------------------------------------- density
    def set_density(self, density: HudDensity) -> None:
        self._density = density
        # Re-target everyone using the new density.
        for internal in self._elements.values():
            internal.opacity_target = self._compute_target(
                internal, self._current_mode,
            )

    def density(self) -> HudDensity:
        return self._density

    def density_multiplier(self, density: HudDensity) -> float:
        return _DENSITY_MULT[density]

    # ---------------------------------------------- opacity
    def opacity_for(
        self,
        element: HudElement,
        current_mode: HudMode | None = None,
    ) -> float:
        if element not in self._elements:
            raise KeyError(f"unknown element: {element.value}")
        internal = self._elements[element]
        if current_mode is None:
            return internal.opacity_current
        return self._compute_target(internal, current_mode)

    def current_opacity(self, element: HudElement) -> float:
        return self._elements[element].opacity_current

    def target_opacity(self, element: HudElement) -> float:
        return self._elements[element].opacity_target

    def should_render(
        self, element: HudElement, mode: HudMode,
    ) -> bool:
        target = self._compute_target(
            self._elements[element], mode,
        )
        return target > 0.0

    # ---------------------------------------------- tick
    def tick(self, dt: float) -> None:
        if dt < 0:
            raise ValueError("dt must be >= 0")
        for internal in self._elements.values():
            if internal.fade_speed_s <= 0:
                internal.opacity_current = (
                    internal.opacity_target
                )
                continue
            cur = internal.opacity_current
            tgt = internal.opacity_target
            if cur == tgt:
                continue
            step = dt / internal.fade_speed_s
            if step >= 1.0:
                internal.opacity_current = tgt
                continue
            delta = tgt - cur
            internal.opacity_current = cur + delta * step

    # ---------------------------------------------- helpers
    def hide_all_for_cinematic(self) -> None:
        for internal in self._elements.values():
            internal.opacity_target = 0.0

    def restore_from_cinematic(self) -> None:
        # Restore using current mode
        for internal in self._elements.values():
            internal.opacity_target = self._compute_target(
                internal, self._current_mode,
            )

    def is_visible_in(
        self,
        element: HudElement,
        mode: HudMode,
    ) -> bool:
        return mode in self._elements[element].visible_in_modes


__all__ = [
    "HudElement",
    "HudMode",
    "HudDensity",
    "HudElementSpec",
    "HudOverlaySystem",
]
