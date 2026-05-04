"""Chat box layout — moveable, resizable, with memory.

The classic FFXI chatbox was anchored bottom-left and locked.
Demoncore makes it FREE: each player saves their own chatbox
geometry (screen position, width/height), opacity, scrollback
length, and channel filter mask. It also remembers per-channel
text color preference and a font size.

Channels routed to the chatbox:
  SAY / SHOUT / YELL / TELL / PARTY / ALLIANCE / LINKSHELL_1
  / LINKSHELL_2 / SYSTEM_NOTICE

World announcements (siege starts, server-firsts, perma-deaths)
do NOT live in the chatbox — they slide across the top of the
screen via a separate banner system.

Public surface
--------------
    ChannelKind enum
    ChatBoxLayout dataclass
    ChatBoxLayoutRegistry
        .get_or_default(player_id)
        .move(player_id, screen_x, screen_y)
        .resize(player_id, width, height)
        .set_opacity(player_id, opacity_pct)
        .set_scrollback(player_id, max_lines)
        .set_font_size(player_id, size_pt)
        .set_channel_filter(player_id, channel, enabled)
        .set_channel_color(player_id, channel, color)
        .lock / .unlock / .reset
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Defaults sized for 1920x1080.
DEFAULT_X = 30
DEFAULT_Y = 760
DEFAULT_WIDTH = 540
DEFAULT_HEIGHT = 220
DEFAULT_OPACITY_PCT = 75
DEFAULT_SCROLLBACK_LINES = 200
DEFAULT_FONT_SIZE = 14

# Bounds.
MIN_WIDTH = 220
MAX_WIDTH = 1400
MIN_HEIGHT = 100
MAX_HEIGHT = 800
MIN_OPACITY = 10
MAX_OPACITY = 100
MIN_SCROLLBACK = 50
MAX_SCROLLBACK = 5000
MIN_FONT_SIZE = 9
MAX_FONT_SIZE = 28


class ChannelKind(str, enum.Enum):
    SAY = "say"
    SHOUT = "shout"
    YELL = "yell"
    TELL = "tell"
    PARTY = "party"
    ALLIANCE = "alliance"
    LINKSHELL_1 = "linkshell_1"
    LINKSHELL_2 = "linkshell_2"
    SYSTEM_NOTICE = "system_notice"


# Default colors per channel.
_DEFAULT_CHANNEL_COLORS: dict[ChannelKind, str] = {
    ChannelKind.SAY: "white",
    ChannelKind.SHOUT: "orange",
    ChannelKind.YELL: "red",
    ChannelKind.TELL: "magenta",
    ChannelKind.PARTY: "cyan",
    ChannelKind.ALLIANCE: "lime",
    ChannelKind.LINKSHELL_1: "yellow",
    ChannelKind.LINKSHELL_2: "blue",
    ChannelKind.SYSTEM_NOTICE: "gray",
}


@dataclasses.dataclass
class ChatBoxLayout:
    player_id: str
    screen_x: int = DEFAULT_X
    screen_y: int = DEFAULT_Y
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    opacity_pct: int = DEFAULT_OPACITY_PCT
    scrollback_lines: int = DEFAULT_SCROLLBACK_LINES
    font_size: int = DEFAULT_FONT_SIZE
    locked: bool = False
    channel_filter: dict[ChannelKind, bool] = dataclasses.field(
        default_factory=lambda: {
            ch: True for ch in ChannelKind
        },
    )
    channel_colors: dict[ChannelKind, str] = dataclasses.field(
        default_factory=lambda: dict(_DEFAULT_CHANNEL_COLORS),
    )


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


@dataclasses.dataclass
class ChatBoxLayoutRegistry:
    _layouts: dict[str, ChatBoxLayout] = dataclasses.field(
        default_factory=dict,
    )

    def get_or_default(
        self, *, player_id: str,
    ) -> ChatBoxLayout:
        layout = self._layouts.get(player_id)
        if layout is None:
            layout = ChatBoxLayout(player_id=player_id)
            self._layouts[player_id] = layout
        return layout

    def get(
        self, player_id: str,
    ) -> t.Optional[ChatBoxLayout]:
        return self._layouts.get(player_id)

    def _mut(
        self, player_id: str,
    ) -> t.Optional[ChatBoxLayout]:
        layout = self.get_or_default(player_id=player_id)
        if layout.locked:
            return None
        return layout

    def move(
        self, *, player_id: str,
        screen_x: int, screen_y: int,
    ) -> bool:
        layout = self._mut(player_id)
        if layout is None:
            return False
        layout.screen_x = screen_x
        layout.screen_y = screen_y
        return True

    def resize(
        self, *, player_id: str,
        width: int, height: int,
    ) -> bool:
        layout = self._mut(player_id)
        if layout is None:
            return False
        layout.width = _clamp(width, MIN_WIDTH, MAX_WIDTH)
        layout.height = _clamp(height, MIN_HEIGHT, MAX_HEIGHT)
        return True

    def set_opacity(
        self, *, player_id: str, opacity_pct: int,
    ) -> bool:
        layout = self._mut(player_id)
        if layout is None:
            return False
        layout.opacity_pct = _clamp(
            opacity_pct, MIN_OPACITY, MAX_OPACITY,
        )
        return True

    def set_scrollback(
        self, *, player_id: str, max_lines: int,
    ) -> bool:
        layout = self._mut(player_id)
        if layout is None:
            return False
        layout.scrollback_lines = _clamp(
            max_lines, MIN_SCROLLBACK, MAX_SCROLLBACK,
        )
        return True

    def set_font_size(
        self, *, player_id: str, size_pt: int,
    ) -> bool:
        layout = self._mut(player_id)
        if layout is None:
            return False
        layout.font_size = _clamp(
            size_pt, MIN_FONT_SIZE, MAX_FONT_SIZE,
        )
        return True

    def set_channel_filter(
        self, *, player_id: str,
        channel: ChannelKind, enabled: bool,
    ) -> bool:
        layout = self._mut(player_id)
        if layout is None:
            return False
        layout.channel_filter[channel] = enabled
        return True

    def set_channel_color(
        self, *, player_id: str,
        channel: ChannelKind, color: str,
    ) -> bool:
        layout = self._mut(player_id)
        if layout is None:
            return False
        if not color:
            return False
        layout.channel_colors[channel] = color
        return True

    def lock(self, *, player_id: str) -> bool:
        layout = self.get_or_default(player_id=player_id)
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
        if layout is None or layout.locked:
            return False
        self._layouts[player_id] = ChatBoxLayout(
            player_id=player_id,
        )
        return True

    def total_layouts(self) -> int:
        return len(self._layouts)


__all__ = [
    "DEFAULT_X", "DEFAULT_Y",
    "DEFAULT_WIDTH", "DEFAULT_HEIGHT",
    "DEFAULT_OPACITY_PCT",
    "DEFAULT_SCROLLBACK_LINES",
    "DEFAULT_FONT_SIZE",
    "MIN_WIDTH", "MAX_WIDTH", "MIN_HEIGHT", "MAX_HEIGHT",
    "MIN_OPACITY", "MAX_OPACITY",
    "MIN_SCROLLBACK", "MAX_SCROLLBACK",
    "MIN_FONT_SIZE", "MAX_FONT_SIZE",
    "ChannelKind",
    "ChatBoxLayout", "ChatBoxLayoutRegistry",
]
