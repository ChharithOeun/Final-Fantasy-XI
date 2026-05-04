"""Tests for UI placement presets."""
from __future__ import annotations

from server.ui_placement_presets import (
    PanelAnchor,
    PanelKind,
    PresetKind,
    UIPlacementPresets,
)


def test_default_layout_is_classic():
    p = UIPlacementPresets()
    layout = p.layout_for(player_id="alice")
    assert layout.active_preset == PresetKind.CLASSIC
    assert PanelKind.CHATBOX in layout.panels


def test_apply_widescreen():
    p = UIPlacementPresets()
    assert p.apply_preset(
        player_id="alice", kind=PresetKind.WIDESCREEN,
    )
    layout = p.layout_for(player_id="alice")
    assert layout.active_preset == PresetKind.WIDESCREEN


def test_apply_unknown_preset_rejected():
    """CUSTOM with no snapshot saved cannot be applied."""
    p = UIPlacementPresets()
    assert not p.apply_preset(
        player_id="alice", kind=PresetKind.CUSTOM,
    )


def test_move_panel_switches_to_custom():
    p = UIPlacementPresets()
    p.move_panel(
        player_id="alice",
        anchor=PanelAnchor(
            panel=PanelKind.MINIMAP,
            screen_x=10, screen_y=10,
            width=200, height=200,
        ),
    )
    layout = p.layout_for(player_id="alice")
    assert layout.active_preset == PresetKind.CUSTOM
    mini = layout.panels[PanelKind.MINIMAP]
    assert mini.screen_x == 10


def test_save_custom_persists_snapshot():
    p = UIPlacementPresets()
    p.move_panel(
        player_id="alice",
        anchor=PanelAnchor(
            panel=PanelKind.CHATBOX,
            screen_x=99, screen_y=99,
            width=300, height=200,
        ),
    )
    assert p.save_custom(player_id="alice")
    # Switch to widescreen, then back to custom
    p.apply_preset(
        player_id="alice", kind=PresetKind.WIDESCREEN,
    )
    p.apply_preset(
        player_id="alice", kind=PresetKind.CUSTOM,
    )
    layout = p.layout_for(player_id="alice")
    assert layout.panels[PanelKind.CHATBOX].screen_x == 99


def test_reset_custom_clears_snapshot():
    p = UIPlacementPresets()
    p.save_custom(player_id="alice")
    assert p.reset_custom(player_id="alice")
    assert not p.apply_preset(
        player_id="alice", kind=PresetKind.CUSTOM,
    )


def test_reset_custom_unknown_player():
    p = UIPlacementPresets()
    assert not p.reset_custom(player_id="ghost")


def test_reset_custom_no_snapshot_returns_false():
    p = UIPlacementPresets()
    p.layout_for(player_id="alice")
    assert not p.reset_custom(player_id="alice")


def test_combat_focused_hides_quest_log():
    p = UIPlacementPresets()
    p.apply_preset(
        player_id="alice",
        kind=PresetKind.COMBAT_FOCUSED,
    )
    ql = p.layout_for(
        player_id="alice",
    ).panels[PanelKind.QUEST_LOG]
    assert not ql.visible


def test_streamer_keeps_top_clear():
    """Streamer preset puts most panels at the top to leave
    bottom area for stream overlays."""
    p = UIPlacementPresets()
    p.apply_preset(
        player_id="alice", kind=PresetKind.STREAMER,
    )
    layout = p.layout_for(player_id="alice")
    chatbox = layout.panels[PanelKind.CHATBOX]
    assert chatbox.screen_y < 400


def test_mobile_like_full_width_chatbox():
    p = UIPlacementPresets()
    p.apply_preset(
        player_id="alice",
        kind=PresetKind.MOBILE_LIKE,
    )
    layout = p.layout_for(player_id="alice")
    cb = layout.panels[PanelKind.CHATBOX]
    assert cb.width >= 1900


def test_per_player_isolation():
    p = UIPlacementPresets()
    p.apply_preset(
        player_id="alice", kind=PresetKind.WIDESCREEN,
    )
    p.apply_preset(
        player_id="bob",
        kind=PresetKind.COMBAT_FOCUSED,
    )
    assert (
        p.layout_for(player_id="alice").active_preset
        != p.layout_for(player_id="bob").active_preset
    )


def test_apply_preset_preserves_custom_snapshot():
    p = UIPlacementPresets()
    p.move_panel(
        player_id="alice",
        anchor=PanelAnchor(
            panel=PanelKind.MINIMAP,
            screen_x=5, screen_y=5,
            width=100, height=100,
        ),
    )
    p.save_custom(player_id="alice")
    p.apply_preset(
        player_id="alice", kind=PresetKind.WIDESCREEN,
    )
    layout = p.layout_for(player_id="alice")
    assert layout.custom_snapshot is not None


def test_apply_overlays_panels_completely():
    p = UIPlacementPresets()
    p.move_panel(
        player_id="alice",
        anchor=PanelAnchor(
            panel=PanelKind.MINIMAP,
            screen_x=5, screen_y=5,
            width=100, height=100,
        ),
    )
    # Now apply widescreen — minimap should NOT be at 5,5 anymore
    p.apply_preset(
        player_id="alice", kind=PresetKind.WIDESCREEN,
    )
    layout = p.layout_for(player_id="alice")
    assert (
        layout.panels[PanelKind.MINIMAP].screen_x != 5
    )


def test_move_unknown_player_creates_state():
    """move_panel on a new player should still work."""
    p = UIPlacementPresets()
    p.move_panel(
        player_id="newcomer",
        anchor=PanelAnchor(
            panel=PanelKind.MINIMAP,
            screen_x=1, screen_y=1,
            width=100, height=100,
        ),
    )
    assert p.total_states() == 1


def test_total_states_count():
    p = UIPlacementPresets()
    p.layout_for(player_id="a")
    p.layout_for(player_id="b")
    p.layout_for(player_id="c")
    assert p.total_states() == 3
