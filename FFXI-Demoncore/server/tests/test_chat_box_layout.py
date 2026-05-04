"""Tests for the chat box layout."""
from __future__ import annotations

from server.chat_box_layout import (
    ChannelKind,
    ChatBoxLayoutRegistry,
    DEFAULT_FONT_SIZE,
    DEFAULT_OPACITY_PCT,
    DEFAULT_SCROLLBACK_LINES,
    DEFAULT_WIDTH,
    MAX_FONT_SIZE,
    MAX_OPACITY,
    MAX_SCROLLBACK,
    MAX_WIDTH,
    MIN_FONT_SIZE,
)


def test_get_or_default_creates_layout():
    reg = ChatBoxLayoutRegistry()
    layout = reg.get_or_default(player_id="alice")
    assert layout.width == DEFAULT_WIDTH
    assert layout.font_size == DEFAULT_FONT_SIZE
    assert layout.scrollback_lines == DEFAULT_SCROLLBACK_LINES
    assert layout.opacity_pct == DEFAULT_OPACITY_PCT


def test_default_filters_all_enabled():
    reg = ChatBoxLayoutRegistry()
    layout = reg.get_or_default(player_id="alice")
    assert all(layout.channel_filter.values())


def test_default_colors_present_for_all_channels():
    reg = ChatBoxLayoutRegistry()
    layout = reg.get_or_default(player_id="alice")
    for ch in ChannelKind:
        assert ch in layout.channel_colors


def test_move_updates_position():
    reg = ChatBoxLayoutRegistry()
    assert reg.move(
        player_id="alice", screen_x=100, screen_y=200,
    )
    layout = reg.get_or_default(player_id="alice")
    assert layout.screen_x == 100
    assert layout.screen_y == 200


def test_resize_clamps():
    reg = ChatBoxLayoutRegistry()
    reg.resize(
        player_id="alice", width=99999, height=99999,
    )
    layout = reg.get_or_default(player_id="alice")
    assert layout.width == MAX_WIDTH


def test_opacity_clamps():
    reg = ChatBoxLayoutRegistry()
    reg.set_opacity(player_id="alice", opacity_pct=200)
    assert reg.get_or_default(
        player_id="alice",
    ).opacity_pct == MAX_OPACITY


def test_scrollback_clamps():
    reg = ChatBoxLayoutRegistry()
    reg.set_scrollback(player_id="alice", max_lines=10000)
    assert reg.get_or_default(
        player_id="alice",
    ).scrollback_lines == MAX_SCROLLBACK


def test_font_size_clamps():
    reg = ChatBoxLayoutRegistry()
    reg.set_font_size(player_id="alice", size_pt=100)
    assert reg.get_or_default(
        player_id="alice",
    ).font_size == MAX_FONT_SIZE
    reg.set_font_size(player_id="alice", size_pt=1)
    assert reg.get_or_default(
        player_id="alice",
    ).font_size == MIN_FONT_SIZE


def test_set_channel_filter_off():
    reg = ChatBoxLayoutRegistry()
    reg.set_channel_filter(
        player_id="alice",
        channel=ChannelKind.SHOUT, enabled=False,
    )
    assert (
        reg.get_or_default(
            player_id="alice",
        ).channel_filter[ChannelKind.SHOUT]
        is False
    )


def test_set_channel_color():
    reg = ChatBoxLayoutRegistry()
    reg.set_channel_color(
        player_id="alice",
        channel=ChannelKind.SHOUT, color="#ff0000",
    )
    assert (
        reg.get_or_default(
            player_id="alice",
        ).channel_colors[ChannelKind.SHOUT]
        == "#ff0000"
    )


def test_set_empty_color_rejected():
    reg = ChatBoxLayoutRegistry()
    assert not reg.set_channel_color(
        player_id="alice",
        channel=ChannelKind.SHOUT, color="",
    )


def test_lock_blocks_mutations():
    reg = ChatBoxLayoutRegistry()
    reg.lock(player_id="alice")
    assert not reg.move(
        player_id="alice", screen_x=10, screen_y=10,
    )
    assert not reg.resize(
        player_id="alice", width=300, height=300,
    )
    assert not reg.set_opacity(
        player_id="alice", opacity_pct=50,
    )
    assert not reg.set_channel_filter(
        player_id="alice",
        channel=ChannelKind.SAY, enabled=False,
    )


def test_lock_twice_returns_false():
    reg = ChatBoxLayoutRegistry()
    reg.lock(player_id="alice")
    assert not reg.lock(player_id="alice")


def test_unlock_allows_mutation():
    reg = ChatBoxLayoutRegistry()
    reg.lock(player_id="alice")
    reg.unlock(player_id="alice")
    assert reg.move(
        player_id="alice", screen_x=5, screen_y=5,
    )


def test_reset_restores_defaults():
    reg = ChatBoxLayoutRegistry()
    reg.move(
        player_id="alice", screen_x=999, screen_y=999,
    )
    reg.set_opacity(player_id="alice", opacity_pct=20)
    reg.reset(player_id="alice")
    layout = reg.get_or_default(player_id="alice")
    assert layout.opacity_pct == DEFAULT_OPACITY_PCT


def test_reset_locked_rejected():
    reg = ChatBoxLayoutRegistry()
    reg.lock(player_id="alice")
    assert not reg.reset(player_id="alice")


def test_reset_unknown_returns_false():
    reg = ChatBoxLayoutRegistry()
    assert not reg.reset(player_id="ghost")


def test_per_player_isolation():
    reg = ChatBoxLayoutRegistry()
    reg.set_opacity(player_id="alice", opacity_pct=20)
    reg.set_opacity(player_id="bob", opacity_pct=80)
    assert (
        reg.get_or_default(player_id="alice").opacity_pct
        != reg.get_or_default(player_id="bob").opacity_pct
    )


def test_total_layouts():
    reg = ChatBoxLayoutRegistry()
    reg.get_or_default(player_id="a")
    reg.get_or_default(player_id="b")
    assert reg.total_layouts() == 2
