"""Tests for camera_lock_pin."""
from __future__ import annotations

from server.camera_lock_pin import CameraLockPin, StickyKind


def test_pin_happy():
    p = CameraLockPin()
    out = p.pin(
        player_id="bob", distance=25.0, pitch_deg=-30.0,
        sticky_through=[StickyKind.ENGAGE,
                        StickyKind.ZONE_CHANGE],
        pinned_at=1000,
    )
    assert out is True
    assert p.is_pinned(player_id="bob") is True


def test_pin_blank_player_blocked():
    p = CameraLockPin()
    out = p.pin(
        player_id="", distance=25.0, pitch_deg=-30.0,
        sticky_through=[], pinned_at=1000,
    )
    assert out is False


def test_pin_negative_distance_blocked():
    p = CameraLockPin()
    out = p.pin(
        player_id="bob", distance=-1.0, pitch_deg=0.0,
        sticky_through=[], pinned_at=1000,
    )
    assert out is False


def test_pin_too_far_blocked():
    p = CameraLockPin()
    out = p.pin(
        player_id="bob", distance=200.0, pitch_deg=-90.0,
        sticky_through=[], pinned_at=1000,
    )
    assert out is False


def test_pin_pitch_out_of_range():
    p = CameraLockPin()
    out = p.pin(
        player_id="bob", distance=25.0, pitch_deg=120.0,
        sticky_through=[], pinned_at=1000,
    )
    assert out is False


def test_pin_dedupes_sticky():
    p = CameraLockPin()
    p.pin(
        player_id="bob", distance=25.0, pitch_deg=-30.0,
        sticky_through=[
            StickyKind.ENGAGE, StickyKind.ENGAGE,
            StickyKind.ZONE_CHANGE,
        ],
        pinned_at=1000,
    )
    pin = p.pin_for(player_id="bob")
    assert len(pin.sticky_through) == 2


def test_unpin_happy():
    p = CameraLockPin()
    p.pin(
        player_id="bob", distance=25.0, pitch_deg=-30.0,
        sticky_through=[], pinned_at=1000,
    )
    assert p.unpin(player_id="bob") is True
    assert p.is_pinned(player_id="bob") is False


def test_unpin_unknown():
    p = CameraLockPin()
    assert p.unpin(player_id="ghost") is False


def test_pin_overwrites_prior():
    p = CameraLockPin()
    p.pin(
        player_id="bob", distance=25.0, pitch_deg=-30.0,
        sticky_through=[StickyKind.ENGAGE],
        pinned_at=1000,
    )
    p.pin(
        player_id="bob", distance=50.0, pitch_deg=-60.0,
        sticky_through=[StickyKind.ZONE_CHANGE],
        pinned_at=2000,
    )
    pin = p.pin_for(player_id="bob")
    assert pin.pinned_distance == 50.0
    assert StickyKind.ZONE_CHANGE in pin.sticky_through
    assert StickyKind.ENGAGE not in pin.sticky_through


def test_should_override_listed_kind():
    p = CameraLockPin()
    p.pin(
        player_id="bob", distance=25.0, pitch_deg=-30.0,
        sticky_through=[StickyKind.ENGAGE,
                        StickyKind.ZONE_CHANGE],
        pinned_at=1000,
    )
    assert p.should_override(
        player_id="bob", trigger=StickyKind.ENGAGE,
    ) is True
    assert p.should_override(
        player_id="bob",
        trigger=StickyKind.ZONE_CHANGE,
    ) is True


def test_should_override_unlisted_kind():
    p = CameraLockPin()
    p.pin(
        player_id="bob", distance=25.0, pitch_deg=-30.0,
        sticky_through=[StickyKind.ENGAGE],
        pinned_at=1000,
    )
    assert p.should_override(
        player_id="bob",
        trigger=StickyKind.CUTSCENE_END,
    ) is False


def test_should_override_no_pin():
    p = CameraLockPin()
    assert p.should_override(
        player_id="bob", trigger=StickyKind.ENGAGE,
    ) is False


def test_pin_for_unknown_none():
    p = CameraLockPin()
    assert p.pin_for(player_id="ghost") is None


def test_total_pinned():
    p = CameraLockPin()
    p.pin(
        player_id="bob", distance=25.0, pitch_deg=-30.0,
        sticky_through=[], pinned_at=1000,
    )
    p.pin(
        player_id="cara", distance=50.0, pitch_deg=-45.0,
        sticky_through=[], pinned_at=1000,
    )
    assert p.total_pinned() == 2


def test_five_sticky_kinds():
    assert len(list(StickyKind)) == 5
