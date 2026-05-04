"""Tests for the equipment compare."""
from __future__ import annotations

from server.equipment_compare import (
    EquipmentCompare,
    EquipSlot,
    SkillKind,
    StatKind,
)


def test_register_item():
    e = EquipmentCompare()
    item = e.register_item(
        item_id="iron_sword", label="Iron Sword",
        slot=EquipSlot.MAIN,
        stats={StatKind.ATTACK: 30, StatKind.STR: 5},
    )
    assert item is not None


def test_double_register_rejected():
    e = EquipmentCompare()
    e.register_item(
        item_id="x", label="X", slot=EquipSlot.MAIN,
    )
    second = e.register_item(
        item_id="x", label="Y", slot=EquipSlot.MAIN,
    )
    assert second is None


def test_equip_unknown_item():
    e = EquipmentCompare()
    assert not e.equip(
        player_id="alice", item_id="ghost",
    )


def test_equip_succeeds():
    e = EquipmentCompare()
    e.register_item(
        item_id="iron_sword", label="Iron Sword",
        slot=EquipSlot.MAIN,
    )
    assert e.equip(
        player_id="alice", item_id="iron_sword",
    )
    assert e.equipped_in_slot(
        player_id="alice", slot=EquipSlot.MAIN,
    ) == "iron_sword"


def test_compare_unknown_candidate():
    e = EquipmentCompare()
    assert e.compare(
        player_id="alice", candidate_item_id="ghost",
    ) is None


def test_compare_with_no_equipped_yields_pure_positive():
    e = EquipmentCompare()
    e.register_item(
        item_id="iron_sword", label="Iron Sword",
        slot=EquipSlot.MAIN,
        stats={StatKind.ATTACK: 30, StatKind.STR: 5},
    )
    res = e.compare(
        player_id="alice",
        candidate_item_id="iron_sword",
    )
    assert res.currently_equipped_item_id is None
    deltas = {d.stat: d.delta for d in res.stat_deltas}
    assert deltas[StatKind.ATTACK] == 30
    assert deltas[StatKind.STR] == 5
    assert res.net_score == 35


def test_compare_with_equipped_diff():
    e = EquipmentCompare()
    e.register_item(
        item_id="iron_sword", label="Iron Sword",
        slot=EquipSlot.MAIN,
        stats={StatKind.ATTACK: 30, StatKind.STR: 5},
    )
    e.register_item(
        item_id="steel_sword", label="Steel Sword",
        slot=EquipSlot.MAIN,
        stats={StatKind.ATTACK: 50, StatKind.STR: 3},
    )
    e.equip(player_id="alice", item_id="iron_sword")
    res = e.compare(
        player_id="alice",
        candidate_item_id="steel_sword",
    )
    deltas = {d.stat: d.delta for d in res.stat_deltas}
    assert deltas[StatKind.ATTACK] == 20
    assert deltas[StatKind.STR] == -2
    assert res.net_score == 18


def test_skill_deltas_separated():
    e = EquipmentCompare()
    e.register_item(
        item_id="apprentice_robe", label="Apprentice Robe",
        slot=EquipSlot.BODY,
        skills={
            SkillKind.HEALING_MAGIC: 5,
            SkillKind.ELEMENTAL: 3,
        },
    )
    res = e.compare(
        player_id="alice",
        candidate_item_id="apprentice_robe",
    )
    skill_deltas = {
        d.skill: d.delta for d in res.skill_deltas
    }
    assert skill_deltas[SkillKind.HEALING_MAGIC] == 5
    assert skill_deltas[SkillKind.ELEMENTAL] == 3


def test_negative_skill_in_compare():
    e = EquipmentCompare()
    e.register_item(
        item_id="archer_robe", label="Archer Robe",
        slot=EquipSlot.BODY,
        skills={SkillKind.ARCHERY: 10},
    )
    e.register_item(
        item_id="cleric_robe", label="Cleric Robe",
        slot=EquipSlot.BODY,
        skills={SkillKind.HEALING_MAGIC: 7},
    )
    e.equip(player_id="alice", item_id="archer_robe")
    res = e.compare(
        player_id="alice",
        candidate_item_id="cleric_robe",
    )
    deltas = {
        d.skill: d.delta for d in res.skill_deltas
    }
    assert deltas[SkillKind.ARCHERY] == -10
    assert deltas[SkillKind.HEALING_MAGIC] == 7


def test_net_score_includes_skills():
    e = EquipmentCompare()
    e.register_item(
        item_id="x", label="X", slot=EquipSlot.HANDS,
        stats={StatKind.STR: 2},
        skills={SkillKind.SWORD: 5},
    )
    res = e.compare(
        player_id="alice", candidate_item_id="x",
    )
    assert res.net_score == 7


def test_equip_overwrites_slot():
    e = EquipmentCompare()
    e.register_item(
        item_id="a", label="A", slot=EquipSlot.MAIN,
    )
    e.register_item(
        item_id="b", label="B", slot=EquipSlot.MAIN,
    )
    e.equip(player_id="alice", item_id="a")
    e.equip(player_id="alice", item_id="b")
    assert e.equipped_in_slot(
        player_id="alice", slot=EquipSlot.MAIN,
    ) == "b"


def test_compare_slot_propagates():
    e = EquipmentCompare()
    e.register_item(
        item_id="cape", label="Cape",
        slot=EquipSlot.BACK,
    )
    res = e.compare(
        player_id="alice", candidate_item_id="cape",
    )
    assert res.slot == EquipSlot.BACK


def test_per_player_isolation():
    e = EquipmentCompare()
    e.register_item(
        item_id="x", label="X", slot=EquipSlot.MAIN,
    )
    e.equip(player_id="alice", item_id="x")
    assert e.equipped_in_slot(
        player_id="alice", slot=EquipSlot.MAIN,
    ) == "x"
    assert e.equipped_in_slot(
        player_id="bob", slot=EquipSlot.MAIN,
    ) is None


def test_total_items():
    e = EquipmentCompare()
    e.register_item(
        item_id="a", label="A", slot=EquipSlot.MAIN,
    )
    e.register_item(
        item_id="b", label="B", slot=EquipSlot.MAIN,
    )
    assert e.total_items() == 2


def test_stat_deltas_sorted_positive_first():
    e = EquipmentCompare()
    e.register_item(
        item_id="x", label="X", slot=EquipSlot.MAIN,
        stats={
            StatKind.ATTACK: 50,
            StatKind.DEX: -3,
            StatKind.STR: 5,
        },
    )
    res = e.compare(
        player_id="alice", candidate_item_id="x",
    )
    first_delta = res.stat_deltas[0].delta
    last_delta = res.stat_deltas[-1].delta
    assert first_delta >= last_delta


def test_compare_includes_currently_equipped_id():
    e = EquipmentCompare()
    e.register_item(
        item_id="iron", label="Iron",
        slot=EquipSlot.MAIN,
    )
    e.register_item(
        item_id="steel", label="Steel",
        slot=EquipSlot.MAIN,
    )
    e.equip(player_id="alice", item_id="iron")
    res = e.compare(
        player_id="alice", candidate_item_id="steel",
    )
    assert res.currently_equipped_item_id == "iron"
