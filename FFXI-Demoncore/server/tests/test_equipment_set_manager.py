"""Tests for the equipment set manager."""
from __future__ import annotations

from server.equipment_compare import EquipSlot
from server.equipment_set_manager import (
    EquipmentSetManager,
    MAX_SETS_PER_PLAYER,
    SetKind,
)


def test_save_set():
    m = EquipmentSetManager()
    s = m.save_set(
        player_id="alice", name="war_melee",
        kind=SetKind.ENGAGED_MELEE,
        slot_map={
            EquipSlot.MAIN: "iron_sword",
            EquipSlot.HEAD: "iron_helm",
        },
    )
    assert s is not None


def test_save_empty_name_rejected():
    m = EquipmentSetManager()
    s = m.save_set(
        player_id="alice", name="",
        slot_map={EquipSlot.MAIN: "x"},
    )
    assert s is None


def test_save_empty_slot_map_rejected():
    m = EquipmentSetManager()
    s = m.save_set(
        player_id="alice", name="x",
        slot_map={},
    )
    assert s is None


def test_save_all_empty_items_rejected():
    m = EquipmentSetManager()
    s = m.save_set(
        player_id="alice", name="x",
        slot_map={EquipSlot.MAIN: ""},
    )
    assert s is None


def test_save_overwrite_existing():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="x",
        slot_map={EquipSlot.MAIN: "iron"},
    )
    m.save_set(
        player_id="alice", name="x",
        slot_map={EquipSlot.MAIN: "steel"},
    )
    s = m.get_set(player_id="alice", name="x")
    assert s.slot_map[EquipSlot.MAIN] == "steel"


def test_max_sets_cap():
    m = EquipmentSetManager(max_sets_per_player=3)
    for i in range(3):
        m.save_set(
            player_id="alice", name=f"set_{i}",
            slot_map={EquipSlot.MAIN: f"item_{i}"},
        )
    res = m.save_set(
        player_id="alice", name="overflow",
        slot_map={EquipSlot.MAIN: "x"},
    )
    assert res is None


def test_max_sets_cap_constant():
    assert MAX_SETS_PER_PLAYER == 30


def test_delete_set():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="x",
        slot_map={EquipSlot.MAIN: "iron"},
    )
    assert m.delete_set(
        player_id="alice", name="x",
    )
    assert m.get_set(
        player_id="alice", name="x",
    ) is None


def test_delete_unknown():
    m = EquipmentSetManager()
    assert not m.delete_set(
        player_id="alice", name="ghost",
    )


def test_rename_set():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="war_set",
        slot_map={EquipSlot.MAIN: "iron"},
    )
    assert m.rename_set(
        player_id="alice",
        old_name="war_set", new_name="warrior_set",
    )
    assert m.get_set(
        player_id="alice", name="warrior_set",
    ) is not None
    assert m.get_set(
        player_id="alice", name="war_set",
    ) is None


def test_rename_to_existing_rejected():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="a",
        slot_map={EquipSlot.MAIN: "iron"},
    )
    m.save_set(
        player_id="alice", name="b",
        slot_map={EquipSlot.MAIN: "iron"},
    )
    assert not m.rename_set(
        player_id="alice", old_name="a", new_name="b",
    )


def test_rename_to_empty_rejected():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="a",
        slot_map={EquipSlot.MAIN: "iron"},
    )
    assert not m.rename_set(
        player_id="alice", old_name="a", new_name="",
    )


def test_rename_unknown_old():
    m = EquipmentSetManager()
    assert not m.rename_set(
        player_id="alice",
        old_name="ghost", new_name="x",
    )


def test_sets_for_sorted():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="b",
        slot_map={EquipSlot.MAIN: "x"},
    )
    m.save_set(
        player_id="alice", name="a",
        slot_map={EquipSlot.MAIN: "x"},
    )
    sets = m.sets_for(player_id="alice")
    assert [s.name for s in sets] == ["a", "b"]


def test_build_swap_plan():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="war_set",
        slot_map={
            EquipSlot.MAIN: "steel_sword",
            EquipSlot.HEAD: "iron_helm",
        },
    )
    plan = m.build_swap_plan(
        player_id="alice", set_name="war_set",
        currently_equipped={
            EquipSlot.MAIN: "iron_sword",
            EquipSlot.HEAD: "iron_helm",
        },
    )
    swaps = {sw.slot: sw for sw in plan.swaps}
    assert EquipSlot.MAIN in swaps
    assert EquipSlot.HEAD not in swaps
    assert plan.no_change_count == 1


def test_build_swap_plan_unknown_set():
    m = EquipmentSetManager()
    assert m.build_swap_plan(
        player_id="alice", set_name="ghost",
    ) is None


def test_swap_plan_unequips_unset_slots():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="naked",
        slot_map={EquipSlot.MAIN: "sword"},
    )
    plan = m.build_swap_plan(
        player_id="alice", set_name="naked",
        currently_equipped={
            EquipSlot.HEAD: "old_helm",
            EquipSlot.MAIN: "sword",
        },
    )
    head_swap = next(
        sw for sw in plan.swaps
        if sw.slot == EquipSlot.HEAD
    )
    assert head_swap.to_item_id is None


def test_total_sets_count():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="a",
        slot_map={EquipSlot.MAIN: "x"},
    )
    m.save_set(
        player_id="alice", name="b",
        slot_map={EquipSlot.MAIN: "x"},
    )
    assert m.total_sets(player_id="alice") == 2


def test_per_player_isolation():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="x",
        slot_map={EquipSlot.MAIN: "iron"},
    )
    assert m.total_sets(player_id="bob") == 0


def test_save_with_empty_item_filtered():
    m = EquipmentSetManager()
    s = m.save_set(
        player_id="alice", name="x",
        slot_map={
            EquipSlot.MAIN: "iron",
            EquipSlot.HEAD: "",
        },
    )
    assert EquipSlot.HEAD not in s.slot_map


def test_swap_plan_deterministic_order():
    m = EquipmentSetManager()
    m.save_set(
        player_id="alice", name="x",
        slot_map={
            EquipSlot.MAIN: "a",
            EquipSlot.HEAD: "b",
            EquipSlot.FEET: "c",
        },
    )
    plan = m.build_swap_plan(
        player_id="alice", set_name="x",
        currently_equipped={},
    )
    slots_order = [sw.slot.value for sw in plan.swaps]
    assert slots_order == sorted(slots_order)
