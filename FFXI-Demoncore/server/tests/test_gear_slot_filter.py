"""Tests for gear_slot_filter."""
from __future__ import annotations

from server.gear_slot_filter import GearItem, GearSlotFilter, Slot


def _murgleis():
    return GearItem(
        item_id="murgleis", display_name="Murgleis",
        slot_compatibility=(Slot.MAIN,),
    )


def _stikini_ring():
    return GearItem(
        item_id="stikini_ring_1", display_name="Stikini Ring +1",
        slot_compatibility=(Slot.RING1, Slot.RING2),
    )


def test_register_happy():
    f = GearSlotFilter()
    assert f.register_item(item=_murgleis()) is True


def test_register_blank_id_blocked():
    f = GearSlotFilter()
    bad = GearItem(item_id="", display_name="X",
                   slot_compatibility=(Slot.MAIN,))
    assert f.register_item(item=bad) is False


def test_register_blank_name_blocked():
    f = GearSlotFilter()
    bad = GearItem(item_id="x", display_name="",
                   slot_compatibility=(Slot.MAIN,))
    assert f.register_item(item=bad) is False


def test_register_no_slots_blocked():
    f = GearSlotFilter()
    bad = GearItem(item_id="x", display_name="X",
                   slot_compatibility=())
    assert f.register_item(item=bad) is False


def test_register_duplicate_blocked():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    assert f.register_item(item=_murgleis()) is False


def test_can_equip_match():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    assert f.can_equip(item_id="murgleis", slot=Slot.MAIN) is True


def test_can_equip_wrong_slot():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    assert f.can_equip(item_id="murgleis", slot=Slot.SUB) is False


def test_can_equip_unknown_item():
    f = GearSlotFilter()
    assert f.can_equip(item_id="ghost", slot=Slot.MAIN) is False


def test_ring_fits_either_ring_slot():
    f = GearSlotFilter()
    f.register_item(item=_stikini_ring())
    assert f.can_equip(item_id="stikini_ring_1", slot=Slot.RING1)
    assert f.can_equip(item_id="stikini_ring_1", slot=Slot.RING2)


def test_candidates_for_slot_global():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    f.register_item(item=GearItem(
        item_id="naegling", display_name="Naegling",
        slot_compatibility=(Slot.MAIN,),
    ))
    f.register_item(item=GearItem(
        item_id="daybreak", display_name="Daybreak",
        slot_compatibility=(Slot.SUB,),
    ))
    out = f.candidates_for_slot(slot=Slot.MAIN)
    names = [i.display_name for i in out]
    # alphabetic order: Murgleis, Naegling
    assert names == ["Murgleis", "Naegling"]


def test_candidates_owned_only():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    f.register_item(item=GearItem(
        item_id="naegling", display_name="Naegling",
        slot_compatibility=(Slot.MAIN,),
    ))
    f.grant_to_owner(owner_id="alice", item_id="murgleis")
    out = f.candidates_for_slot(
        slot=Slot.MAIN, owned_only=True, owner_id="alice",
    )
    assert len(out) == 1
    assert out[0].display_name == "Murgleis"


def test_candidates_owned_only_other_player():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    f.grant_to_owner(owner_id="alice", item_id="murgleis")
    out = f.candidates_for_slot(
        slot=Slot.MAIN, owned_only=True, owner_id="bob",
    )
    assert out == []


def test_grant_blank_owner_blocked():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    out = f.grant_to_owner(owner_id="", item_id="murgleis")
    assert out is False


def test_grant_unknown_item_blocked():
    f = GearSlotFilter()
    out = f.grant_to_owner(owner_id="alice", item_id="ghost")
    assert out is False


def test_grant_duplicate_blocked():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    f.grant_to_owner(owner_id="alice", item_id="murgleis")
    out = f.grant_to_owner(owner_id="alice", item_id="murgleis")
    assert out is False


def test_revoke():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    f.grant_to_owner(owner_id="alice", item_id="murgleis")
    out = f.revoke_from_owner(
        owner_id="alice", item_id="murgleis",
    )
    assert out is True
    assert f.total_owned(owner_id="alice") == 0


def test_revoke_unknown():
    f = GearSlotFilter()
    out = f.revoke_from_owner(
        owner_id="alice", item_id="ghost",
    )
    assert out is False


def test_item_lookup():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    out = f.item_lookup(item_id="murgleis")
    assert out is not None
    assert out.display_name == "Murgleis"


def test_item_lookup_unknown():
    f = GearSlotFilter()
    assert f.item_lookup(item_id="ghost") is None


def test_sixteen_slots():
    assert len(list(Slot)) == 16


def test_total_items_grows():
    f = GearSlotFilter()
    f.register_item(item=_murgleis())
    f.register_item(item=_stikini_ring())
    assert f.total_items() == 2
