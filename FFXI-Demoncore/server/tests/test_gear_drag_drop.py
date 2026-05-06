"""Tests for gear_drag_drop."""
from __future__ import annotations

from server.gear_drag_drop import (
    DragState, DropOutcome, GearDragDrop,
)
from server.gear_slot_filter import (
    GearItem, GearSlotFilter, Slot,
)


def _setup():
    f = GearSlotFilter()
    f.register_item(item=GearItem(
        item_id="murgleis", display_name="Murgleis",
        slot_compatibility=(Slot.MAIN,),
    ))
    f.register_item(item=GearItem(
        item_id="hat_x", display_name="Viti. Chapeau +4",
        slot_compatibility=(Slot.HEAD,),
    ))
    f.grant_to_owner(owner_id="alice", item_id="murgleis")
    f.grant_to_owner(owner_id="alice", item_id="hat_x")
    return f, GearDragDrop(_filter=f)


def test_pick_up_happy():
    _, dd = _setup()
    out = dd.pick_up(
        player_id="alice", item_id="murgleis",
    )
    assert out is True
    assert dd.state(player_id="alice") == DragState.DRAGGING


def test_pick_up_blank_player():
    _, dd = _setup()
    assert dd.pick_up(player_id="", item_id="murgleis") is False


def test_pick_up_blank_item():
    _, dd = _setup()
    assert dd.pick_up(player_id="alice", item_id="") is False


def test_pick_up_unknown_item():
    _, dd = _setup()
    out = dd.pick_up(player_id="alice", item_id="ghost")
    assert out is False


def test_pick_up_not_owned():
    _, dd = _setup()
    out = dd.pick_up(player_id="bob", item_id="murgleis")
    assert out is False


def test_drop_on_correct_slot_accepted():
    _, dd = _setup()
    dd.pick_up(player_id="alice", item_id="murgleis")
    out = dd.drop_on(
        player_id="alice", target_set="DT",
        target_slot=Slot.MAIN,
    )
    assert out.outcome == DropOutcome.ACCEPTED
    assert out.item_id == "murgleis"


def test_drop_on_wrong_slot_refused():
    _, dd = _setup()
    dd.pick_up(player_id="alice", item_id="murgleis")
    out = dd.drop_on(
        player_id="alice", target_set="Idle",
        target_slot=Slot.HEAD,
    )
    assert out.outcome == DropOutcome.REFUSED_WRONG_SLOT
    assert "Murgleis" in out.message


def test_drop_without_drag_refused():
    _, dd = _setup()
    out = dd.drop_on(
        player_id="alice", target_set="DT",
        target_slot=Slot.MAIN,
    )
    assert out.outcome == DropOutcome.REFUSED_NO_DRAG


def test_drop_after_drop_blocked():
    _, dd = _setup()
    dd.pick_up(player_id="alice", item_id="murgleis")
    dd.drop_on(
        player_id="alice", target_set="DT",
        target_slot=Slot.MAIN,
    )
    # State is now DROPPED — second drop refused
    out = dd.drop_on(
        player_id="alice", target_set="ACC",
        target_slot=Slot.MAIN,
    )
    assert out.outcome == DropOutcome.REFUSED_NO_DRAG


def test_cancel_clears_drag():
    _, dd = _setup()
    dd.pick_up(player_id="alice", item_id="murgleis")
    assert dd.cancel(player_id="alice") is True
    assert dd.state(player_id="alice") == DragState.IDLE


def test_cancel_no_drag():
    _, dd = _setup()
    assert dd.cancel(player_id="alice") is False


def test_cancel_after_drop_blocked():
    _, dd = _setup()
    dd.pick_up(player_id="alice", item_id="murgleis")
    dd.drop_on(
        player_id="alice", target_set="DT",
        target_slot=Slot.MAIN,
    )
    assert dd.cancel(player_id="alice") is False


def test_state_unknown_player_idle():
    _, dd = _setup()
    assert dd.state(player_id="ghost") == DragState.IDLE


def test_held_item_during_drag():
    _, dd = _setup()
    dd.pick_up(player_id="alice", item_id="murgleis")
    assert dd.held_item(player_id="alice") == "murgleis"


def test_held_item_when_idle():
    _, dd = _setup()
    assert dd.held_item(player_id="alice") is None


def test_held_item_after_drop():
    _, dd = _setup()
    dd.pick_up(player_id="alice", item_id="murgleis")
    dd.drop_on(
        player_id="alice", target_set="DT",
        target_slot=Slot.MAIN,
    )
    assert dd.held_item(player_id="alice") is None


def test_pickup_replaces_in_flight_drag():
    _, dd = _setup()
    dd.pick_up(player_id="alice", item_id="murgleis")
    dd.pick_up(player_id="alice", item_id="hat_x")
    assert dd.held_item(player_id="alice") == "hat_x"


def test_drop_carries_target_set_and_slot():
    _, dd = _setup()
    dd.pick_up(player_id="alice", item_id="murgleis")
    out = dd.drop_on(
        player_id="alice", target_set="Death Blossom",
        target_slot=Slot.MAIN,
    )
    assert out.target_set == "Death Blossom"
    assert out.target_slot == Slot.MAIN


def test_three_drag_states():
    assert len(list(DragState)) == 3


def test_four_drop_outcomes():
    assert len(list(DropOutcome)) == 4


def test_isolated_per_player():
    _, dd = _setup()
    dd._filter.grant_to_owner(
        owner_id="bob", item_id="hat_x",
    )
    dd.pick_up(player_id="alice", item_id="murgleis")
    dd.pick_up(player_id="bob", item_id="hat_x")
    assert dd.held_item(player_id="alice") == "murgleis"
    assert dd.held_item(player_id="bob") == "hat_x"
