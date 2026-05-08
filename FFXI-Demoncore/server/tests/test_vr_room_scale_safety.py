"""Tests for vr_room_scale_safety."""
from __future__ import annotations

from server.vr_room_scale_safety import (
    HmdPosition, PlayMode, PlaySpace, SafetyState,
    VrRoomScaleSafety,
)


def _room_3x3() -> PlaySpace:
    return PlaySpace(
        width_m=3.0, depth_m=3.0, mode=PlayMode.ROOM_SCALE,
    )


def _seated() -> PlaySpace:
    return PlaySpace(
        width_m=1.0, depth_m=1.0, mode=PlayMode.SEATED,
    )


def test_register_room_scale():
    s = VrRoomScaleSafety()
    assert s.register_playspace(
        player_id="bob", playspace=_room_3x3(),
    ) is True


def test_register_seated_small_ok():
    """Seated mode allows boxes < 1.5m."""
    s = VrRoomScaleSafety()
    assert s.register_playspace(
        player_id="bob", playspace=_seated(),
    ) is True


def test_register_blank_player_blocked():
    s = VrRoomScaleSafety()
    assert s.register_playspace(
        player_id="", playspace=_room_3x3(),
    ) is False


def test_register_zero_size_blocked():
    s = VrRoomScaleSafety()
    bad = PlaySpace(
        width_m=0.0, depth_m=2.0, mode=PlayMode.ROOM_SCALE,
    )
    assert s.register_playspace(
        player_id="bob", playspace=bad,
    ) is False


def test_register_room_scale_too_small_blocked():
    """Room-scale needs 1.5m minimum each axis."""
    s = VrRoomScaleSafety()
    too_small = PlaySpace(
        width_m=1.0, depth_m=2.0, mode=PlayMode.ROOM_SCALE,
    )
    assert s.register_playspace(
        player_id="bob", playspace=too_small,
    ) is False


def test_safe_at_center():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_room_3x3())
    state = s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=0.0, z=0.0, timestamp_ms=1000),
    )
    assert state == SafetyState.SAFE


def test_warning_near_edge():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_room_3x3())
    # 3x3 box -> edges at ±1.5. Position at x=1.3 is
    # 0.2m from edge — under 0.3m warning margin.
    state = s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=1.3, z=0.0, timestamp_ms=1000),
    )
    assert state == SafetyState.WARNING


def test_edge_crossed_pauses():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_room_3x3())
    # x=2.0 is past the edge at 1.5
    state = s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=2.0, z=0.0, timestamp_ms=1000),
    )
    assert state == SafetyState.EDGE_CROSSED
    assert s.is_paused(player_id="bob") is True


def test_walk_back_in_clears_pause():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_room_3x3())
    s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=2.0, z=0.0, timestamp_ms=1000),
    )
    assert s.is_paused(player_id="bob") is True
    # Walk back to center
    state = s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=0.0, z=0.0, timestamp_ms=1100),
    )
    assert state == SafetyState.SAFE
    assert s.is_paused(player_id="bob") is False


def test_recenter_sets_recentering():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_room_3x3())
    assert s.recenter(player_id="bob") is True
    state = s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=0.0, z=0.0, timestamp_ms=1000),
    )
    assert state == SafetyState.RECENTERING


def test_recenter_unknown_player_blocked():
    s = VrRoomScaleSafety()
    assert s.recenter(player_id="ghost") is False


def test_warning_z_axis():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_room_3x3())
    # 3x3 -> Z edge at ±1.5; z=1.4 is 0.1m from edge
    state = s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=0.0, z=1.4, timestamp_ms=1000),
    )
    assert state == SafetyState.WARNING


def test_state_change_emits_event():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_room_3x3())
    s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=0.0, z=0.0, timestamp_ms=1000),
    )
    s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=1.3, z=0.0, timestamp_ms=1100),
    )
    s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=2.0, z=0.0, timestamp_ms=1200),
    )
    events = s.events_for(player_id="bob")
    # SAFE -> WARNING -> EDGE_CROSSED = at least 2 events
    # (initial state set is also an event)
    assert len(events) >= 2
    last = events[-1]
    assert last.state == SafetyState.EDGE_CROSSED


def test_no_state_change_no_extra_event():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_room_3x3())
    s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=0.0, z=0.0, timestamp_ms=1000),
    )
    s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=0.1, z=0.1, timestamp_ms=1100),
    )
    # Both samples were SAFE; should not log a state change
    events = s.events_for(player_id="bob")
    assert len(events) == 0


def test_unknown_player_returns_safe():
    """No playspace registered = unrestricted."""
    s = VrRoomScaleSafety()
    state = s.update_hmd(
        player_id="ghost",
        hmd=HmdPosition(x=10.0, z=10.0, timestamp_ms=1000),
    )
    assert state == SafetyState.SAFE


def test_clear_player_removes_state():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_room_3x3())
    s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=2.0, z=0.0, timestamp_ms=1000),
    )
    assert s.clear_player(player_id="bob") is True
    # After clearing, events_for returns empty
    assert s.events_for(player_id="bob") == []


def test_clear_unknown_player():
    s = VrRoomScaleSafety()
    assert s.clear_player(player_id="ghost") is False


def test_seated_mode_smaller_box():
    s = VrRoomScaleSafety()
    s.register_playspace(player_id="bob", playspace=_seated())
    # 1m box -> edges at ±0.5; lean to x=0.3 is well within
    state = s.update_hmd(
        player_id="bob",
        hmd=HmdPosition(x=0.3, z=0.0, timestamp_ms=1000),
    )
    # 0.5 - 0.3 = 0.2 — under 0.3m margin = WARNING
    assert state == SafetyState.WARNING


def test_two_play_modes():
    assert len(list(PlayMode)) == 2


def test_four_safety_states():
    assert len(list(SafetyState)) == 4
