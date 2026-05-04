"""Pop-out menu animation — blur-back, scale-in, interactive feel.

Old-school FFXI menus felt instant but flat. Demoncore keeps
the turn-based menu logic but POPS the menu out: a slight back
blur appears, the panel scales in over a few frames, and
hovering / cycling produces a small bump animation. Selecting
a menu item triggers a confirm pulse.

This module is the ANIMATION STATE engine — it tracks each
panel's animation phase and t-value (0..1) so the renderer can
interpolate. It does NOT do the rendering itself.

Public surface
--------------
    AnimPhase enum
    AnimEasing enum
    PopoutAnim dataclass
    PopoutMenuAnimation
        .open(panel_id, easing)
        .close(panel_id)
        .interact(panel_id, kind="hover" | "select")
        .step(elapsed_seconds) — advance all phases
        .state_for(panel_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default phase durations (seconds).
DEFAULT_OPEN_DURATION = 0.18
DEFAULT_CLOSE_DURATION = 0.12
DEFAULT_HOVER_DURATION = 0.08
DEFAULT_SELECT_DURATION = 0.16
DEFAULT_BLUR_BACK_DURATION = 0.10


class AnimPhase(str, enum.Enum):
    HIDDEN = "hidden"
    OPENING = "opening"
    OPEN = "open"
    HOVERING = "hovering"
    SELECTING = "selecting"
    CLOSING = "closing"


class AnimEasing(str, enum.Enum):
    LINEAR = "linear"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE_OUT = "bounce_out"


@dataclasses.dataclass
class PopoutAnim:
    panel_id: str
    phase: AnimPhase = AnimPhase.HIDDEN
    t_value: float = 0.0           # 0.0..1.0 within phase
    easing: AnimEasing = AnimEasing.EASE_OUT
    blur_back_strength: float = 0.0   # 0..1
    elapsed_in_phase: float = 0.0
    duration: float = DEFAULT_OPEN_DURATION


@dataclasses.dataclass
class PopoutMenuAnimation:
    open_duration: float = DEFAULT_OPEN_DURATION
    close_duration: float = DEFAULT_CLOSE_DURATION
    hover_duration: float = DEFAULT_HOVER_DURATION
    select_duration: float = DEFAULT_SELECT_DURATION
    blur_back_duration: float = DEFAULT_BLUR_BACK_DURATION
    _panels: dict[str, PopoutAnim] = dataclasses.field(
        default_factory=dict,
    )

    def _panel(self, panel_id: str) -> PopoutAnim:
        a = self._panels.get(panel_id)
        if a is None:
            a = PopoutAnim(panel_id=panel_id)
            self._panels[panel_id] = a
        return a

    def open(
        self, *, panel_id: str,
        easing: AnimEasing = AnimEasing.EASE_OUT,
    ) -> bool:
        a = self._panel(panel_id)
        if a.phase in (AnimPhase.OPENING, AnimPhase.OPEN):
            return False
        a.phase = AnimPhase.OPENING
        a.t_value = 0.0
        a.elapsed_in_phase = 0.0
        a.duration = self.open_duration
        a.easing = easing
        return True

    def close(self, *, panel_id: str) -> bool:
        a = self._panel(panel_id)
        if a.phase == AnimPhase.HIDDEN:
            return False
        a.phase = AnimPhase.CLOSING
        a.t_value = 0.0
        a.elapsed_in_phase = 0.0
        a.duration = self.close_duration
        return True

    def interact(
        self, *, panel_id: str,
        kind: str = "hover",
    ) -> bool:
        """Trigger a brief HOVERING or SELECTING burst on top
        of an OPEN panel."""
        a = self._panel(panel_id)
        if a.phase not in (
            AnimPhase.OPEN,
            AnimPhase.HOVERING,
            AnimPhase.SELECTING,
        ):
            return False
        if kind == "hover":
            a.phase = AnimPhase.HOVERING
            a.duration = self.hover_duration
        elif kind == "select":
            a.phase = AnimPhase.SELECTING
            a.duration = self.select_duration
        else:
            return False
        a.t_value = 0.0
        a.elapsed_in_phase = 0.0
        return True

    def step(
        self, *, elapsed_seconds: float,
    ) -> int:
        if elapsed_seconds <= 0:
            return 0
        moved = 0
        for a in self._panels.values():
            if a.phase == AnimPhase.HIDDEN:
                continue
            if a.phase == AnimPhase.OPEN:
                # Settled — blur converges to 1.0
                a.blur_back_strength = min(
                    1.0,
                    a.blur_back_strength
                    + elapsed_seconds / self.blur_back_duration,
                )
                continue
            a.elapsed_in_phase += elapsed_seconds
            if a.duration <= 0:
                a.t_value = 1.0
            else:
                a.t_value = min(
                    1.0,
                    a.elapsed_in_phase / a.duration,
                )
            moved += 1
            if a.t_value >= 1.0:
                # Phase complete — transition
                if a.phase == AnimPhase.OPENING:
                    a.phase = AnimPhase.OPEN
                    a.t_value = 1.0
                    a.elapsed_in_phase = 0.0
                elif a.phase == AnimPhase.CLOSING:
                    a.phase = AnimPhase.HIDDEN
                    a.t_value = 0.0
                    a.elapsed_in_phase = 0.0
                    a.blur_back_strength = 0.0
                elif a.phase in (
                    AnimPhase.HOVERING,
                    AnimPhase.SELECTING,
                ):
                    # Decay back to OPEN after the burst
                    a.phase = AnimPhase.OPEN
                    a.t_value = 1.0
                    a.elapsed_in_phase = 0.0
        return moved

    def state_for(
        self, panel_id: str,
    ) -> t.Optional[PopoutAnim]:
        return self._panels.get(panel_id)

    def total_active_panels(self) -> int:
        return sum(
            1 for a in self._panels.values()
            if a.phase != AnimPhase.HIDDEN
        )


__all__ = [
    "DEFAULT_OPEN_DURATION", "DEFAULT_CLOSE_DURATION",
    "DEFAULT_HOVER_DURATION", "DEFAULT_SELECT_DURATION",
    "DEFAULT_BLUR_BACK_DURATION",
    "AnimPhase", "AnimEasing",
    "PopoutAnim", "PopoutMenuAnimation",
]
