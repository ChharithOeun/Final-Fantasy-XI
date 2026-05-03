"""Tests for the minimap layout."""
from __future__ import annotations

from server.minimap_layout import (
    AnchorCorner,
    DEFAULT_HEIGHT,
    DEFAULT_OPACITY_PCT,
    DEFAULT_TILT_DEGREES,
    DEFAULT_WIDTH,
    DEFAULT_ZOOM_PCT,
    MAX_HEIGHT,
    MAX_OPACITY,
    MAX_TILT,
    MAX_WIDTH,
    MAX_ZOOM,
    MIN_OPACITY,
    MIN_TILT,
    MinimapLayoutRegistry,
)


def test_get_or_default_creates_layout():
    reg = MinimapLayoutRegistry()
    layout = reg.get_or_default(player_id="alice")
    assert layout.width == DEFAULT_WIDTH
    assert layout.height == DEFAULT_HEIGHT
    assert layout.zoom_pct == DEFAULT_ZOOM_PCT
    assert layout.opacity_pct == DEFAULT_OPACITY_PCT
    assert layout.tilt_degrees == DEFAULT_TILT_DEGREES


def test_get_returns_none_for_unknown():
    reg = MinimapLayoutRegistry()
    assert reg.get("ghost") is None


def test_move_updates_position():
    reg = MinimapLayoutRegistry()
    assert reg.move(
        player_id="alice", screen_x=100, screen_y=200,
        anchor=AnchorCorner.FREE,
    )
    layout = reg.get_or_default(player_id="alice")
    assert layout.screen_x == 100
    assert layout.screen_y == 200
    assert layout.anchor == AnchorCorner.FREE


def test_resize_clamps_to_bounds():
    reg = MinimapLayoutRegistry()
    reg.resize(
        player_id="alice", width=10000, height=10000,
    )
    layout = reg.get_or_default(player_id="alice")
    assert layout.width == MAX_WIDTH
    assert layout.height == MAX_HEIGHT


def test_zoom_clamps():
    reg = MinimapLayoutRegistry()
    reg.set_zoom(player_id="alice", zoom_pct=99999)
    assert reg.get_or_default(
        player_id="alice",
    ).zoom_pct == MAX_ZOOM


def test_opacity_clamps_low():
    reg = MinimapLayoutRegistry()
    reg.set_opacity(player_id="alice", opacity_pct=-5)
    assert reg.get_or_default(
        player_id="alice",
    ).opacity_pct == MIN_OPACITY


def test_opacity_clamps_high():
    reg = MinimapLayoutRegistry()
    reg.set_opacity(player_id="alice", opacity_pct=200)
    assert reg.get_or_default(
        player_id="alice",
    ).opacity_pct == MAX_OPACITY


def test_height_pop_clamps():
    reg = MinimapLayoutRegistry()
    reg.set_height_pop(
        player_id="alice", pop_strength=300,
    )
    assert reg.get_or_default(
        player_id="alice",
    ).height_pop_strength == 100


def test_tilt_clamps():
    reg = MinimapLayoutRegistry()
    reg.set_tilt(player_id="alice", degrees=300)
    assert reg.get_or_default(
        player_id="alice",
    ).tilt_degrees == MAX_TILT
    reg.set_tilt(player_id="alice", degrees=-10)
    assert reg.get_or_default(
        player_id="alice",
    ).tilt_degrees == MIN_TILT


def test_lock_blocks_mutations():
    reg = MinimapLayoutRegistry()
    reg.get_or_default(player_id="alice")
    assert reg.lock(player_id="alice")
    assert not reg.move(
        player_id="alice", screen_x=10, screen_y=10,
    )
    assert not reg.resize(
        player_id="alice", width=200, height=200,
    )
    assert not reg.set_zoom(
        player_id="alice", zoom_pct=50,
    )


def test_lock_twice_returns_false():
    reg = MinimapLayoutRegistry()
    reg.get_or_default(player_id="alice")
    reg.lock(player_id="alice")
    assert not reg.lock(player_id="alice")


def test_unlock_allows_mutation():
    reg = MinimapLayoutRegistry()
    reg.lock(player_id="alice")
    assert reg.unlock(player_id="alice")
    assert reg.move(
        player_id="alice", screen_x=10, screen_y=20,
    )


def test_unlock_unlocked_returns_false():
    reg = MinimapLayoutRegistry()
    reg.get_or_default(player_id="alice")
    assert not reg.unlock(player_id="alice")


def test_reset_restores_defaults():
    reg = MinimapLayoutRegistry()
    reg.move(
        player_id="alice", screen_x=99, screen_y=88,
        anchor=AnchorCorner.BOTTOM_LEFT,
    )
    reg.set_zoom(player_id="alice", zoom_pct=200)
    assert reg.reset(player_id="alice")
    layout = reg.get_or_default(player_id="alice")
    assert layout.zoom_pct == DEFAULT_ZOOM_PCT
    assert layout.anchor == AnchorCorner.TOP_RIGHT


def test_reset_unknown_returns_false():
    reg = MinimapLayoutRegistry()
    assert not reg.reset(player_id="ghost")


def test_reset_locked_returns_false():
    reg = MinimapLayoutRegistry()
    reg.get_or_default(player_id="alice")
    reg.lock(player_id="alice")
    assert not reg.reset(player_id="alice")


def test_per_player_isolation():
    reg = MinimapLayoutRegistry()
    reg.set_zoom(player_id="alice", zoom_pct=200)
    reg.set_zoom(player_id="bob", zoom_pct=50)
    assert reg.get_or_default(
        player_id="alice",
    ).zoom_pct == 200
    assert reg.get_or_default(
        player_id="bob",
    ).zoom_pct == 50


def test_total_layouts():
    reg = MinimapLayoutRegistry()
    reg.get_or_default(player_id="a")
    reg.get_or_default(player_id="b")
    reg.get_or_default(player_id="c")
    assert reg.total_layouts() == 3


def test_anchor_default_top_right():
    reg = MinimapLayoutRegistry()
    layout = reg.get_or_default(player_id="alice")
    assert layout.anchor == AnchorCorner.TOP_RIGHT
