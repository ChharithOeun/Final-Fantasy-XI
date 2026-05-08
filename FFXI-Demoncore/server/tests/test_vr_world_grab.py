"""Tests for vr_world_grab."""
from __future__ import annotations

from server.vr_world_grab import (
    GrabbableKind, GrabState, Grabbable, Hand, VrWorldGrab,
)


def _chest(gid="chest_1", x=0, y=0.5, z=2,
           two_hands=True):
    return Grabbable(
        grabbable_id=gid, kind=GrabbableKind.LOOT_CHEST,
        x=x, y=y, z=z, requires_two_hands=two_hands,
    )


def _item(gid="potion_1", x=0, y=1.0, z=1):
    return Grabbable(
        grabbable_id=gid, kind=GrabbableKind.SMALL_ITEM,
        x=x, y=y, z=z, requires_two_hands=False,
    )


def test_register_happy():
    g = VrWorldGrab()
    assert g.register(_chest()) is True


def test_register_blank_blocked():
    g = VrWorldGrab()
    bad = Grabbable(
        grabbable_id="", kind=GrabbableKind.LEVER,
        x=0, y=0, z=0,
    )
    assert g.register(bad) is False


def test_register_dup_blocked():
    g = VrWorldGrab()
    g.register(_chest())
    assert g.register(_chest()) is False


def test_grab_in_reach():
    g = VrWorldGrab()
    g.register(_item(x=0.2, y=1.0, z=0.3))
    out = g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="potion_1",
        hand_x=0.0, hand_y=1.0, hand_z=0.0,
    )
    assert out is True
    assert g.state(grabbable_id="potion_1") == GrabState.GRABBED


def test_grab_out_of_reach():
    g = VrWorldGrab()
    g.register(_item(x=10, y=1.0, z=0))
    out = g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="potion_1",
        hand_x=0.0, hand_y=1.0, hand_z=0.0,
    )
    assert out is False


def test_grab_unknown_item_blocked():
    g = VrWorldGrab()
    out = g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="ghost",
        hand_x=0.0, hand_y=0.0, hand_z=0.0,
    )
    assert out is False


def test_grab_other_player_blocked():
    g = VrWorldGrab()
    g.register(_item(x=0, y=1.0, z=0))
    g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="potion_1",
        hand_x=0, hand_y=1.0, hand_z=0,
    )
    # Cara tries to grab the same potion bob holds
    out = g.request_grab(
        player_id="cara", hand=Hand.RIGHT,
        grabbable_id="potion_1",
        hand_x=0, hand_y=1.0, hand_z=0,
    )
    assert out is False


def test_grab_same_player_both_hands_chest():
    g = VrWorldGrab()
    g.register(_chest(x=0, y=0.5, z=0))
    assert g.request_grab(
        player_id="bob", hand=Hand.LEFT,
        grabbable_id="chest_1",
        hand_x=-0.1, hand_y=0.5, hand_z=0,
    ) is True
    assert g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="chest_1",
        hand_x=0.1, hand_y=0.5, hand_z=0,
    ) is True


def test_release_unbinds():
    g = VrWorldGrab()
    g.register(_item(x=0, y=1.0, z=0))
    g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="potion_1",
        hand_x=0, hand_y=1.0, hand_z=0,
    )
    assert g.release(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="potion_1",
    ) is True
    assert g.state(
        grabbable_id="potion_1",
    ) == GrabState.OPEN


def test_release_not_holder():
    g = VrWorldGrab()
    g.register(_item(x=0, y=1.0, z=0))
    g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="potion_1",
        hand_x=0, hand_y=1.0, hand_z=0,
    )
    out = g.release(
        player_id="cara", hand=Hand.RIGHT,
        grabbable_id="potion_1",
    )
    assert out is False


def test_consume_one_handed_item():
    g = VrWorldGrab()
    g.register(_item(x=0, y=1.0, z=0))
    g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="potion_1",
        hand_x=0, hand_y=1.0, hand_z=0,
    )
    assert g.consume(
        player_id="bob", grabbable_id="potion_1",
    ) is True
    assert g.state(
        grabbable_id="potion_1",
    ) == GrabState.CONSUMED


def test_consume_two_hands_required_one_hand_blocks():
    g = VrWorldGrab()
    g.register(_chest(x=0, y=0.5, z=0))
    g.request_grab(
        player_id="bob", hand=Hand.LEFT,
        grabbable_id="chest_1",
        hand_x=-0.1, hand_y=0.5, hand_z=0,
    )
    # Only one hand on chest
    out = g.consume(
        player_id="bob", grabbable_id="chest_1",
    )
    assert out is False


def test_consume_two_hands_succeeds():
    g = VrWorldGrab()
    g.register(_chest(x=0, y=0.5, z=0))
    g.request_grab(
        player_id="bob", hand=Hand.LEFT,
        grabbable_id="chest_1",
        hand_x=-0.1, hand_y=0.5, hand_z=0,
    )
    g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="chest_1",
        hand_x=0.1, hand_y=0.5, hand_z=0,
    )
    assert g.consume(
        player_id="bob", grabbable_id="chest_1",
    ) is True


def test_consume_when_open_blocked():
    g = VrWorldGrab()
    g.register(_item(x=0, y=1.0, z=0))
    out = g.consume(
        player_id="bob", grabbable_id="potion_1",
    )
    assert out is False


def test_grab_consumed_blocked():
    g = VrWorldGrab()
    g.register(_item(x=0, y=1.0, z=0))
    g.request_grab(
        player_id="bob", hand=Hand.RIGHT,
        grabbable_id="potion_1",
        hand_x=0, hand_y=1.0, hand_z=0,
    )
    g.consume(player_id="bob", grabbable_id="potion_1")
    out = g.request_grab(
        player_id="cara", hand=Hand.RIGHT,
        grabbable_id="potion_1",
        hand_x=0, hand_y=1.0, hand_z=0,
    )
    assert out is False


def test_holder_returns_holder():
    g = VrWorldGrab()
    g.register(_item(x=0, y=1.0, z=0))
    g.request_grab(
        player_id="bob", hand=Hand.LEFT,
        grabbable_id="potion_1",
        hand_x=0, hand_y=1.0, hand_z=0,
    )
    h = g.holder(grabbable_id="potion_1")
    assert h is not None
    assert h[0] == "bob"
    assert h[1] == Hand.LEFT


def test_holder_open_returns_none():
    g = VrWorldGrab()
    g.register(_item(x=0, y=1.0, z=0))
    assert g.holder(grabbable_id="potion_1") is None


def test_three_grabbable_kinds():
    assert len(list(GrabbableKind)) == 3


def test_three_states():
    assert len(list(GrabState)) == 3
