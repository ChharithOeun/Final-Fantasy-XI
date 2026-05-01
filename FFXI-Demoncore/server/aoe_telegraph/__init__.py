"""AOE telegraph engine — server-side state machine + geometry +
visibility rules.

Per AOE_TELEGRAPH.md the grammar is asymmetric:
  - Player AOE: PREVIEW (self only) -> ACTIVE (replicated to all in range)
  - Enemy AOE: NEVER preview-visible to players. Players read the
    wind-up animation, position, chant — the skill ceiling lives in
    the visual reading. NPCs in range DO 'see' enemy AOE via
    animation cue (for mood updates).
  - Half-time rule: roughly half the cast time is the reaction window
    (1.5s cast = 0.75s window; 3.0s cast = 1.5s window).

This module owns:
  - TelegraphSpec / Instance lifecycle (TARGETING -> ACTIVE -> LANDING)
  - 7 shape containment functions (circle, donut, cone, line, square,
    chevron, irregular) — pure geometry, no rendering
  - Visibility rules (caster-only preview, faction-aware active broadcast,
    enemy AOE invisible to players)
  - Element-color palette for renderer keying
  - Reaction-window helper (half_time rule)
  - Mood-event emission for NPCs in range

Public surface:
    TelegraphShape, TelegraphState
    TelegraphSpec, TelegraphInstance
    TelegraphRegistry
    ELEMENT_COLOR_HEX
    point_inside_telegraph(instance, point)
    reaction_window_seconds(cast_duration)
    moods_to_emit(observer_archetype) -> list[(mood, delta)]
"""
from .geometry import (
    TelegraphShape,
    point_inside_telegraph,
)
from .palette import (
    ELEMENT_COLOR_HEX,
    color_for_element,
)
from .registry import (
    TelegraphInstance,
    TelegraphRegistry,
    TelegraphSpec,
    TelegraphState,
    moods_to_emit,
    reaction_window_seconds,
)

__all__ = [
    "TelegraphShape",
    "TelegraphState",
    "TelegraphSpec",
    "TelegraphInstance",
    "TelegraphRegistry",
    "ELEMENT_COLOR_HEX",
    "color_for_element",
    "point_inside_telegraph",
    "reaction_window_seconds",
    "moods_to_emit",
]
