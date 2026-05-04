"""UI placement presets — preset layouts + custom drag-drop.

Players pick from named PRESETS (CLASSIC / WIDESCREEN /
COMBAT_FOCUSED / STREAMER / MOBILE_LIKE) or build a CUSTOM
layout by dragging UI panels into place. Each preset slot
holds a set of panel anchors keyed by PanelKind:
chatbox, minimap, party_list, target_card, action_bar,
quest_log, macro_palette, compass, etc.

A player can apply a preset, then optionally save their
edits as their CUSTOM preset which persists to memory.
Switching back to a built-in preset overlays the built-in
on top of the custom slot — the custom slot never erases
unless explicitly overwritten.

Public surface
--------------
    PresetKind enum
    PanelKind enum
    PanelAnchor dataclass
    UIPlacementPreset dataclass
    UIPlacementPresets
        .apply_preset(player_id, kind)
        .move_panel(player_id, kind, anchor)
        .save_custom(player_id)
        .reset_custom(player_id)
        .layout_for(player_id) -> UIPlacementPreset
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PresetKind(str, enum.Enum):
    CLASSIC = "classic"
    WIDESCREEN = "widescreen"
    COMBAT_FOCUSED = "combat_focused"
    STREAMER = "streamer"
    MOBILE_LIKE = "mobile_like"
    CUSTOM = "custom"


class PanelKind(str, enum.Enum):
    CHATBOX = "chatbox"
    MINIMAP = "minimap"
    PARTY_LIST = "party_list"
    TARGET_CARD = "target_card"
    ACTION_BAR = "action_bar"
    QUEST_LOG = "quest_log"
    MACRO_PALETTE = "macro_palette"
    COMPASS = "compass"
    BANNER_AREA = "banner_area"
    SUBTITLE_AREA = "subtitle_area"


@dataclasses.dataclass(frozen=True)
class PanelAnchor:
    panel: PanelKind
    screen_x: int
    screen_y: int
    width: int
    height: int
    visible: bool = True


# Built-in presets (1920x1080 reference).
_BUILTIN_PRESETS: dict[
    PresetKind, dict[PanelKind, PanelAnchor],
] = {
    PresetKind.CLASSIC: {
        PanelKind.CHATBOX: PanelAnchor(
            PanelKind.CHATBOX, 30, 760, 540, 220,
        ),
        PanelKind.MINIMAP: PanelAnchor(
            PanelKind.MINIMAP, 1620, 60, 280, 280,
        ),
        PanelKind.PARTY_LIST: PanelAnchor(
            PanelKind.PARTY_LIST, 1620, 380, 280, 280,
        ),
        PanelKind.TARGET_CARD: PanelAnchor(
            PanelKind.TARGET_CARD, 760, 60, 400, 100,
        ),
        PanelKind.ACTION_BAR: PanelAnchor(
            PanelKind.ACTION_BAR, 660, 980, 600, 80,
        ),
        PanelKind.QUEST_LOG: PanelAnchor(
            PanelKind.QUEST_LOG, 30, 60, 300, 400,
        ),
        PanelKind.MACRO_PALETTE: PanelAnchor(
            PanelKind.MACRO_PALETTE, 800, 540, 320, 320,
        ),
        PanelKind.COMPASS: PanelAnchor(
            PanelKind.COMPASS, 1380, 60, 220, 80,
        ),
        PanelKind.BANNER_AREA: PanelAnchor(
            PanelKind.BANNER_AREA, 0, 30, 1920, 60,
        ),
        PanelKind.SUBTITLE_AREA: PanelAnchor(
            PanelKind.SUBTITLE_AREA, 360, 880, 1200, 80,
        ),
    },
    PresetKind.WIDESCREEN: {
        PanelKind.CHATBOX: PanelAnchor(
            PanelKind.CHATBOX, 30, 800, 720, 250,
        ),
        PanelKind.MINIMAP: PanelAnchor(
            PanelKind.MINIMAP, 1560, 30, 340, 340,
        ),
        PanelKind.PARTY_LIST: PanelAnchor(
            PanelKind.PARTY_LIST, 1560, 400, 340, 340,
        ),
        PanelKind.TARGET_CARD: PanelAnchor(
            PanelKind.TARGET_CARD, 760, 30, 400, 100,
        ),
        PanelKind.ACTION_BAR: PanelAnchor(
            PanelKind.ACTION_BAR, 760, 1000, 400, 60,
        ),
        PanelKind.QUEST_LOG: PanelAnchor(
            PanelKind.QUEST_LOG, 30, 30, 360, 500,
        ),
        PanelKind.MACRO_PALETTE: PanelAnchor(
            PanelKind.MACRO_PALETTE, 800, 540, 320, 320,
        ),
        PanelKind.COMPASS: PanelAnchor(
            PanelKind.COMPASS, 1300, 30, 240, 80,
        ),
        PanelKind.BANNER_AREA: PanelAnchor(
            PanelKind.BANNER_AREA, 0, 0, 1920, 60,
        ),
        PanelKind.SUBTITLE_AREA: PanelAnchor(
            PanelKind.SUBTITLE_AREA, 360, 900, 1200, 80,
        ),
    },
    PresetKind.COMBAT_FOCUSED: {
        PanelKind.CHATBOX: PanelAnchor(
            PanelKind.CHATBOX, 30, 880, 380, 180,
            visible=True,
        ),
        PanelKind.MINIMAP: PanelAnchor(
            PanelKind.MINIMAP, 1700, 30, 200, 200,
        ),
        PanelKind.PARTY_LIST: PanelAnchor(
            PanelKind.PARTY_LIST, 1700, 250, 200, 350,
        ),
        PanelKind.TARGET_CARD: PanelAnchor(
            PanelKind.TARGET_CARD, 760, 30, 400, 100,
        ),
        PanelKind.ACTION_BAR: PanelAnchor(
            PanelKind.ACTION_BAR, 660, 980, 600, 80,
        ),
        PanelKind.QUEST_LOG: PanelAnchor(
            PanelKind.QUEST_LOG, 30, 30, 220, 200,
            visible=False,
        ),
        PanelKind.MACRO_PALETTE: PanelAnchor(
            PanelKind.MACRO_PALETTE, 800, 540, 320, 320,
        ),
        PanelKind.COMPASS: PanelAnchor(
            PanelKind.COMPASS, 1450, 30, 220, 80,
        ),
        PanelKind.BANNER_AREA: PanelAnchor(
            PanelKind.BANNER_AREA, 0, 30, 1920, 60,
        ),
        PanelKind.SUBTITLE_AREA: PanelAnchor(
            PanelKind.SUBTITLE_AREA, 360, 880, 1200, 80,
        ),
    },
    PresetKind.STREAMER: {
        # Tighter top, leaves bottom clear for overlays
        PanelKind.CHATBOX: PanelAnchor(
            PanelKind.CHATBOX, 30, 30, 540, 220,
        ),
        PanelKind.MINIMAP: PanelAnchor(
            PanelKind.MINIMAP, 1620, 30, 280, 280,
        ),
        PanelKind.PARTY_LIST: PanelAnchor(
            PanelKind.PARTY_LIST, 600, 30, 280, 220,
        ),
        PanelKind.TARGET_CARD: PanelAnchor(
            PanelKind.TARGET_CARD, 760, 280, 400, 100,
        ),
        PanelKind.ACTION_BAR: PanelAnchor(
            PanelKind.ACTION_BAR, 660, 280, 600, 80,
        ),
        PanelKind.QUEST_LOG: PanelAnchor(
            PanelKind.QUEST_LOG, 30, 280, 300, 360,
        ),
        PanelKind.MACRO_PALETTE: PanelAnchor(
            PanelKind.MACRO_PALETTE, 800, 540, 320, 320,
        ),
        PanelKind.COMPASS: PanelAnchor(
            PanelKind.COMPASS, 1380, 30, 220, 80,
        ),
        PanelKind.BANNER_AREA: PanelAnchor(
            PanelKind.BANNER_AREA, 0, 320, 1920, 60,
        ),
        PanelKind.SUBTITLE_AREA: PanelAnchor(
            PanelKind.SUBTITLE_AREA, 360, 380, 1200, 80,
        ),
    },
    PresetKind.MOBILE_LIKE: {
        # Big touch-friendly anchors
        PanelKind.CHATBOX: PanelAnchor(
            PanelKind.CHATBOX, 0, 800, 1920, 280,
        ),
        PanelKind.MINIMAP: PanelAnchor(
            PanelKind.MINIMAP, 1500, 30, 400, 400,
        ),
        PanelKind.PARTY_LIST: PanelAnchor(
            PanelKind.PARTY_LIST, 30, 30, 360, 400,
        ),
        PanelKind.TARGET_CARD: PanelAnchor(
            PanelKind.TARGET_CARD, 660, 30, 600, 130,
        ),
        PanelKind.ACTION_BAR: PanelAnchor(
            PanelKind.ACTION_BAR, 0, 700, 1920, 100,
        ),
        PanelKind.QUEST_LOG: PanelAnchor(
            PanelKind.QUEST_LOG, 30, 460, 360, 240,
        ),
        PanelKind.MACRO_PALETTE: PanelAnchor(
            PanelKind.MACRO_PALETTE, 800, 540, 320, 320,
        ),
        PanelKind.COMPASS: PanelAnchor(
            PanelKind.COMPASS, 1300, 30, 200, 100,
        ),
        PanelKind.BANNER_AREA: PanelAnchor(
            PanelKind.BANNER_AREA, 0, 0, 1920, 50,
        ),
        PanelKind.SUBTITLE_AREA: PanelAnchor(
            PanelKind.SUBTITLE_AREA, 0, 660, 1920, 60,
        ),
    },
}


@dataclasses.dataclass
class UIPlacementPreset:
    player_id: str
    active_preset: PresetKind = PresetKind.CLASSIC
    panels: dict[PanelKind, PanelAnchor] = dataclasses.field(
        default_factory=dict,
    )
    custom_snapshot: t.Optional[
        dict[PanelKind, PanelAnchor]
    ] = None


@dataclasses.dataclass
class UIPlacementPresets:
    _states: dict[str, UIPlacementPreset] = dataclasses.field(
        default_factory=dict,
    )

    def _state(
        self, player_id: str,
    ) -> UIPlacementPreset:
        st = self._states.get(player_id)
        if st is None:
            st = UIPlacementPreset(player_id=player_id)
            st.panels = dict(
                _BUILTIN_PRESETS[PresetKind.CLASSIC],
            )
            self._states[player_id] = st
        return st

    def apply_preset(
        self, *, player_id: str, kind: PresetKind,
    ) -> bool:
        st = self._state(player_id)
        if kind == PresetKind.CUSTOM:
            if st.custom_snapshot is None:
                return False
            st.panels = dict(st.custom_snapshot)
            st.active_preset = PresetKind.CUSTOM
            return True
        if kind not in _BUILTIN_PRESETS:
            return False
        st.panels = dict(_BUILTIN_PRESETS[kind])
        st.active_preset = kind
        return True

    def move_panel(
        self, *, player_id: str, anchor: PanelAnchor,
    ) -> bool:
        st = self._state(player_id)
        st.panels[anchor.panel] = anchor
        # Mutating the preset implicitly switches to CUSTOM
        st.active_preset = PresetKind.CUSTOM
        return True

    def save_custom(
        self, *, player_id: str,
    ) -> bool:
        st = self._state(player_id)
        st.custom_snapshot = dict(st.panels)
        st.active_preset = PresetKind.CUSTOM
        return True

    def reset_custom(
        self, *, player_id: str,
    ) -> bool:
        st = self._states.get(player_id)
        if st is None or st.custom_snapshot is None:
            return False
        st.custom_snapshot = None
        return True

    def layout_for(
        self, *, player_id: str,
    ) -> UIPlacementPreset:
        return self._state(player_id)

    def total_states(self) -> int:
        return len(self._states)


__all__ = [
    "PresetKind", "PanelKind",
    "PanelAnchor", "UIPlacementPreset",
    "UIPlacementPresets",
]
