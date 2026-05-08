"""Tests for vr_climbing."""
from __future__ import annotations

from server.vr_climbing import (
    ClimbSurface, Hand, SurfaceKind, VrClimbing,
)


def _ladder(sid="ladder_1", bottom=0.0, top=10.0):
    return ClimbSurface(
        surface_id=sid, kind=SurfaceKind.LADDER,
        bottom_y=bottom, top_y=top, rung_density_per_m=2.5,
    )


def test_register_happy():
    c = VrClimbing()
    assert c.register_surface(_ladder()) is True


def test_register_blank_id():
    c = VrClimbing()
    bad = ClimbSurface(
        surface_id="", kind=SurfaceKind.ROPE,
        bottom_y=0, top_y=5, rung_density_per_m=1,
    )
    assert c.register_surface(bad) is False


def test_register_inverted_blocked():
    c = VrClimbing()
    bad = ClimbSurface(
        surface_id="bad", kind=SurfaceKind.ROPE,
        bottom_y=10, top_y=0, rung_density_per_m=1,
    )
    assert c.register_surface(bad) is False


def test_register_zero_density_blocked():
    c = VrClimbing()
    bad = ClimbSurface(
        surface_id="bad", kind=SurfaceKind.ROPE,
        bottom_y=0, top_y=10, rung_density_per_m=0,
    )
    assert c.register_surface(bad) is False


def test_grab_happy():
    c = VrClimbing()
    c.register_surface(_ladder())
    assert c.grab(
        player_id="bob", hand=Hand.RIGHT,
        surface_id="ladder_1", height=2.0,
    ) is True


def test_grab_unknown_surface():
    c = VrClimbing()
    assert c.grab(
        player_id="bob", hand=Hand.RIGHT,
        surface_id="ghost", height=2.0,
    ) is False


def test_grab_below_bottom_blocked():
    c = VrClimbing()
    c.register_surface(_ladder(bottom=2.0, top=10.0))
    assert c.grab(
        player_id="bob", hand=Hand.RIGHT,
        surface_id="ladder_1", height=1.0,
    ) is False


def test_grab_above_top_blocked():
    c = VrClimbing()
    c.register_surface(_ladder(bottom=0, top=10))
    assert c.grab(
        player_id="bob", hand=Hand.RIGHT,
        surface_id="ladder_1", height=12.0,
    ) is False


def test_release_one_hand():
    c = VrClimbing()
    c.register_surface(_ladder())
    c.grab(
        player_id="bob", hand=Hand.LEFT,
        surface_id="ladder_1", height=2.0,
    )
    c.grab(
        player_id="bob", hand=Hand.RIGHT,
        surface_id="ladder_1", height=2.5,
    )
    assert c.release(
        player_id="bob", hand=Hand.LEFT,
    ) is True
    state = c.state(player_id="bob")
    assert state is not None
    assert state.left_hand_y is None
    assert state.right_hand_y == 2.5


def test_release_both_hands_falls():
    c = VrClimbing()
    c.register_surface(_ladder())
    c.grab(
        player_id="bob", hand=Hand.LEFT,
        surface_id="ladder_1", height=5.0,
    )
    c.release(player_id="bob", hand=Hand.LEFT)
    # Both hands now released -> fall event recorded
    falls = c.fall_events(player_id="bob")
    assert len(falls) == 1
    assert falls[0][0] == 5.0  # body height at release
    assert c.state(player_id="bob") is None


def test_move_body_requires_anchor():
    c = VrClimbing()
    c.register_surface(_ladder())
    # No grab yet; move should fail
    assert c.move_body(
        player_id="bob", new_height=3.0,
    ) is False


def test_move_body_one_hand_ok():
    c = VrClimbing()
    c.register_surface(_ladder())
    c.grab(
        player_id="bob", hand=Hand.LEFT,
        surface_id="ladder_1", height=2.0,
    )
    assert c.move_body(
        player_id="bob", new_height=2.5,
    ) is True


def test_move_body_out_of_range_blocked():
    c = VrClimbing()
    c.register_surface(_ladder(bottom=0, top=10))
    c.grab(
        player_id="bob", hand=Hand.LEFT,
        surface_id="ladder_1", height=2.0,
    )
    assert c.move_body(
        player_id="bob", new_height=15.0,
    ) is False


def test_state_unknown_player():
    c = VrClimbing()
    assert c.state(player_id="ghost") is None


def test_stamina_accumulates():
    c = VrClimbing()
    c.register_surface(_ladder())
    c.grab(
        player_id="bob", hand=Hand.LEFT,
        surface_id="ladder_1", height=2.0,
    )
    c.grab(
        player_id="bob", hand=Hand.RIGHT,
        surface_id="ladder_1", height=2.5,
    )
    c.move_body(player_id="bob", new_height=3.0)
    # 2 grabs + 1 move = 3 stamina
    assert c.stamina_consumed(player_id="bob") == 3


def test_stamina_unknown_player():
    c = VrClimbing()
    assert c.stamina_consumed(player_id="ghost") == 0


def test_two_surfaces_block_when_climbing():
    c = VrClimbing()
    c.register_surface(_ladder("la", 0, 10))
    c.register_surface(_ladder("lb", 0, 10))
    c.grab(
        player_id="bob", hand=Hand.LEFT,
        surface_id="la", height=2.0,
    )
    # Can't reach for a different surface mid-climb
    out = c.grab(
        player_id="bob", hand=Hand.RIGHT,
        surface_id="lb", height=3.0,
    )
    assert out is False


def test_reset():
    c = VrClimbing()
    c.register_surface(_ladder())
    c.grab(
        player_id="bob", hand=Hand.LEFT,
        surface_id="ladder_1", height=2.0,
    )
    assert c.reset(player_id="bob") is True
    assert c.state(player_id="bob") is None


def test_reset_unknown():
    c = VrClimbing()
    assert c.reset(player_id="ghost") is False


def test_five_surface_kinds():
    assert len(list(SurfaceKind)) == 5
