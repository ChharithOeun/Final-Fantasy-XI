"""Tests for the radial macro palette."""
from __future__ import annotations

import math

from server.macro_palette_radial import (
    InputAction,
    MacroPaletteRadial,
    SLOTS_PER_RING,
    SlotKind,
)


def test_create_set_succeeds():
    p = MacroPaletteRadial()
    rs = p.create_set(
        player_id="alice", set_id="combat",
        label="Combat Ring",
    )
    assert rs is not None
    assert len(rs.slots) == SLOTS_PER_RING


def test_double_set_rejected():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    second = p.create_set(
        player_id="alice", set_id="combat",
    )
    assert second is None


def test_first_set_becomes_active():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    active = p.active_set(player_id="alice")
    assert active.set_id == "combat"


def test_bind_slot():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    assert p.bind(
        player_id="alice", set_id="combat",
        slot_index=0, kind=SlotKind.WEAPONSKILL,
        payload="rampage", label="Rampage",
    )
    rs = p.active_set(player_id="alice")
    assert rs.slots[0].kind == SlotKind.WEAPONSKILL


def test_bind_invalid_slot():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    assert not p.bind(
        player_id="alice", set_id="combat",
        slot_index=99, kind=SlotKind.SPELL,
        payload="cure",
    )


def test_bind_unknown_set():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    assert not p.bind(
        player_id="alice", set_id="ghost",
        slot_index=0, kind=SlotKind.SPELL,
    )


def test_cycle_next_slot():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    new_idx = p.cycle(
        player_id="alice", action=InputAction.NEXT_SLOT,
    )
    assert new_idx == 1


def test_cycle_prev_slot_wraps():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    new_idx = p.cycle(
        player_id="alice", action=InputAction.PREV_SLOT,
    )
    assert new_idx == SLOTS_PER_RING - 1


def test_cycle_next_ring():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    p.create_set(player_id="alice", set_id="utility")
    p.cycle(
        player_id="alice", action=InputAction.NEXT_RING,
    )
    active = p.active_set(player_id="alice")
    assert active.set_id == "utility"


def test_cycle_prev_ring_wraps():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    p.create_set(player_id="alice", set_id="utility")
    # active is "combat" (first); prev should wrap to "utility"
    p.cycle(
        player_id="alice", action=InputAction.PREV_RING,
    )
    assert (
        p.active_set(player_id="alice").set_id == "utility"
    )


def test_point_to_slot_zero_north():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    idx = p.point(
        player_id="alice", angle_radians=0.0,
    )
    assert idx == 0


def test_point_to_slot_six_south():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    # 12 slots, halfway around = pi rad = slot 6
    idx = p.point(
        player_id="alice", angle_radians=math.pi,
    )
    assert idx == 6


def test_point_normalizes_negative_angle():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    idx = p.point(
        player_id="alice", angle_radians=-math.pi / 6,
    )
    # -pi/6 normalized = 11pi/6 -> slot 11
    assert idx == 11


def test_activate_returns_payload():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    p.bind(
        player_id="alice", set_id="combat",
        slot_index=0, kind=SlotKind.SPELL,
        payload="cure_iv", label="Cure IV",
    )
    sel = p.activate(player_id="alice")
    assert sel is not None
    assert sel.kind == SlotKind.SPELL
    assert sel.payload == "cure_iv"


def test_activate_empty_slot_returns_none():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    sel = p.activate(player_id="alice")
    assert sel is None


def test_activate_no_palette_returns_none():
    p = MacroPaletteRadial()
    assert p.activate(player_id="ghost") is None


def test_switch_set_resets_highlight():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    p.create_set(player_id="alice", set_id="utility")
    p.cycle(
        player_id="alice", action=InputAction.NEXT_SLOT,
    )
    p.switch_set(player_id="alice", set_id="utility")
    rs = p.active_set(player_id="alice")
    assert rs.set_id == "utility"
    # Highlight reset to 0
    p.bind(
        player_id="alice", set_id="utility",
        slot_index=0, kind=SlotKind.ITEM,
        payload="ether",
    )
    sel = p.activate(player_id="alice")
    assert sel.payload == "ether"


def test_switch_unknown_set_rejected():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    assert not p.switch_set(
        player_id="alice", set_id="ghost",
    )


def test_remove_set():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    p.create_set(player_id="alice", set_id="utility")
    assert p.remove_set(
        player_id="alice", set_id="combat",
    )
    # active should reroute to utility
    assert (
        p.active_set(player_id="alice").set_id == "utility"
    )


def test_remove_unknown_set():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    assert not p.remove_set(
        player_id="alice", set_id="ghost",
    )


def test_total_sets_count():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    p.create_set(player_id="alice", set_id="utility")
    assert p.total_sets(player_id="alice") == 2


def test_per_player_isolation():
    p = MacroPaletteRadial()
    p.create_set(player_id="alice", set_id="combat")
    p.create_set(player_id="bob", set_id="combat")
    p.bind(
        player_id="alice", set_id="combat",
        slot_index=0, kind=SlotKind.SPELL,
        payload="cure",
    )
    bob_active = p.active_set(player_id="bob")
    assert bob_active.slots[0].kind == SlotKind.EMPTY
