"""Minimap layout — per-player moveable/resizable HUD state.

The Windower minimap plugin gave players movable + resizable
positioning. Demoncore preserves and extends that ergonomics:
each player has their own saved layout — anchor corner, screen
position, size, zoom, opacity, height-pop-strength (3D dot
extrusion), tilt angle, and pin/lock state.

Layouts are persisted across sessions; the renderer reads
state_for() at every frame. Players who prefer top-right tiny
classic minimap can have it; players who want a giant tilted
holo-radar can have that too.

Public surface
--------------
    AnchorCorner enum
    MinimapLayout dataclass
    LayoutUpdateResult
    MinimapLayoutRegistry
        .get_or_default(player_id)
        .move(player_id, screen_x, screen_y)
        .resize(player_id, width, height)
        .set_zoom(player_id, zoom_pct)
        .set_opacity(player_id, opacity_pct)
        .set_height_pop(player_id, pop_strength)
        .set_tilt(player_id, degrees)
        .lock(player_id) / .unlock(player_id)
        .reset(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default layout values, sized for a 1920x1080 reference screen.
DEFAULT_ANCHOR_X = 1620
DEFAULT_ANCHOR_Y = 60
DEFAULT_WIDTH = 280
DEFAULT_HEIGHT = 280
DEFAULT_ZOOM_PCT = 100
DEFAULT_OPACITY_PCT = 85
DEFAULT_HEIGHT_POP_STRENGTH = 50
DEFAULT_TILT_DEGREES = 25       # forward tilt for 3D pop

# Hard bounds.
MIN_WIDTH = 120
MAX_WIDTH = 800
MIN_HEIGHT = 120
MAX_HEIGHT = 800
MIN_ZOOM = 25
MAX_ZOOM = 400
MIN_OPACITY = 10
MAX_OPACITY = 100
MIN_HEIGHT_POP = 0
MAX_HEIGHT_POP = 100
MIN_TILT = 0
MAX_TILT = 60


class AnchorCorner(str, enum.Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    FREE = "free"          # screen_x/screen_y are absolute


@dataclasses.dataclass
class MinimapLayout:
    player_id: str
    anchor: AnchorCorner = AnchorCorner.TOP_RIGHT
    screen_x: int = DEFAULT_ANCHOR_X
    screen_y: int = DEFAULT_ANCHOR_Y
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    zoom_pct: int = DEFAULT_ZOOM_PCT
    opacity_pct: int = DEFAULT_OPACITY_PCT
    height_pop_strength: int = DEFAULT_HEIGHT_POP_STRENGTH
    tilt_degrees: int = DEFAULT_TILT_DEGREES
    locked: bool = False


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


@dataclasses.dataclass
class MinimapLayoutRegistry:
    _layouts: dict[str, MinimapLayout] = dataclasses.field(
        default_factory=dict,
    )

    def get_or_default(
        self, *, player_id: str,
    ) -> MinimapLayout:
        layout = self._layouts.get(player_id)
        if layout is None:
            layout = MinimapLayout(player_id=player_id)
            self._layouts[player_id] = layout
        return layout

    def get(
        self, player_id: str,
    ) -> t.Optional[MinimapLayout]:
        return self._layouts.get(player_id)

    def _layout_for_mutation(
        self, player_id: str,
    ) -> t.Optional[MinimapLayout]:
        layout = self._layouts.get(player_id)
        if layout is None:
            layout = MinimapLayout(player_id=player_id)
            self._layouts[player_id] = layout
        if layout.locked:
            return None
        return layout

    def move(
        self, *, player_id: str,
        screen_x: int, screen_y: int,
        anchor: t.Optional[AnchorCorner] = None,
    ) -> bool:
        layout = self._layout_for_mutation(player_id)
        if layout is None:
            return False
        layout.screen_x = screen_x
        layout.screen_y = screen_y
        if anchor is not None:
            layout.anchor = anchor
        return True

    def resize(
        self, *, player_id: str,
        width: int, height: int,
    ) -> bool:
        layout = self._layout_for_mutation(player_id)
        if layout is None:
            return False
        layout.width = _clamp(width, MIN_WIDTH, MAX_WIDTH)
        layout.height = _clamp(height, MIN_HEIGHT, MAX_HEIGHT)
        return True

    def set_zoom(
        self, *, player_id: str, zoom_pct: int,
    ) -> bool:
        layout = self._layout_for_mutation(player_id)
        if layout is None:
            return False
        layout.zoom_pct = _clamp(zoom_pct, MIN_ZOOM, MAX_ZOOM)
        return True

    def set_opacity(
        self, *, player_id: str, opacity_pct: int,
    ) -> bool:
        layout = self._layout_for_mutation(player_id)
        if layout is None:
            return False
        layout.opacity_pct = _clamp(
            opacity_pct, MIN_OPACITY, MAX_OPACITY,
        )
        return True

    def set_height_pop(
        self, *, player_id: str, pop_strength: int,
    ) -> bool:
        layout = self._layout_for_mutation(player_id)
        if layout is None:
            return False
        layout.height_pop_strength = _clamp(
            pop_strength, MIN_HEIGHT_POP, MAX_HEIGHT_POP,
        )
        return True

    def set_tilt(
        self, *, player_id: str, degrees: int,
    ) -> bool:
        layout = self._layout_for_mutation(player_id)
        if layout is None:
            return False
        layout.tilt_degrees = _clamp(
            degrees, MIN_TILT, MAX_TILT,
        )
        return True

    def lock(self, *, player_id: str) -> bool:
        layout = self._layouts.get(player_id)
        if layout is None:
            layout = MinimapLayout(player_id=player_id)
            self._layouts[player_id] = layout
        if layout.locked:
            return False
        layout.locked = True
        return True

    def unlock(self, *, player_id: str) -> bool:
        layout = self._layouts.get(player_id)
        if layout is None or not layout.locked:
            return False
        layout.locked = False
        return True

    def reset(self, *, player_id: str) -> bool:
        layout = self._layouts.get(player_id)
        if layout is None:
            return False
        if layout.locked:
            return False
        self._layouts[player_id] = MinimapLayout(
            player_id=player_id,
        )
        return True

    def total_layouts(self) -> int:
        return len(self._layouts)


__all__ = [
    "DEFAULT_ANCHOR_X", "DEFAULT_ANCHOR_Y",
    "DEFAULT_WIDTH", "DEFAULT_HEIGHT",
    "DEFAULT_ZOOM_PCT", "DEFAULT_OPACITY_PCT",
    "DEFAULT_HEIGHT_POP_STRENGTH",
    "DEFAULT_TILT_DEGREES",
    "MIN_WIDTH", "MAX_WIDTH", "MIN_HEIGHT", "MAX_HEIGHT",
    "MIN_ZOOM", "MAX_ZOOM",
    "MIN_OPACITY", "MAX_OPACITY",
    "MIN_HEIGHT_POP", "MAX_HEIGHT_POP",
    "MIN_TILT", "MAX_TILT",
    "AnchorCorner", "MinimapLayout",
    "MinimapLayoutRegistry",
]
