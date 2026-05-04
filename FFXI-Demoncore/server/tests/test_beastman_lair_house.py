"""Tests for the beastman lair house."""
from __future__ import annotations

from server.beastman_lair_house import (
    BeastmanLairHouse,
    LairTheme,
    LairTier,
)
from server.beastman_playable_races import BeastmanRace


def test_open_lair_yagudo():
    h = BeastmanLairHouse()
    lair = h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    assert lair is not None
    assert lair.tier == LairTier.BURROW
    assert lair.theme == LairTheme.YAGUDO


def test_open_lair_lamia_theme():
    h = BeastmanLairHouse()
    lair = h.open_lair(player_id="syrene", race=BeastmanRace.LAMIA)
    assert lair.theme == LairTheme.LAMIA


def test_open_lair_quadav_theme():
    h = BeastmanLairHouse()
    lair = h.open_lair(player_id="zlot", race=BeastmanRace.QUADAV)
    assert lair.theme == LairTheme.QUADAV


def test_open_lair_orc_theme():
    h = BeastmanLairHouse()
    lair = h.open_lair(player_id="garesh", race=BeastmanRace.ORC)
    assert lair.theme == LairTheme.ORC


def test_open_lair_double_rejected():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    res = h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    assert res is None


def test_place_furniture_basic():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    res = h.place_furniture(
        player_id="kraw",
        item_id="feather_perch",
        slots_used=2,
    )
    assert res.accepted
    assert res.decor_used_total == 2


def test_place_furniture_no_lair():
    h = BeastmanLairHouse()
    res = h.place_furniture(
        player_id="ghost",
        item_id="x",
        slots_used=1,
    )
    assert not res.accepted


def test_place_furniture_capacity():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    # BURROW capacity = 6
    h.place_furniture(
        player_id="kraw", item_id="a", slots_used=4,
    )
    res = h.place_furniture(
        player_id="kraw", item_id="b", slots_used=5,
    )
    assert not res.accepted


def test_place_furniture_duplicate_rejected():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    h.place_furniture(
        player_id="kraw", item_id="a", slots_used=1,
    )
    res = h.place_furniture(
        player_id="kraw", item_id="a", slots_used=1,
    )
    assert not res.accepted


def test_place_furniture_zero_slots():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    res = h.place_furniture(
        player_id="kraw", item_id="a", slots_used=0,
    )
    assert not res.accepted


def test_mount_trophy():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    res = h.mount_trophy(
        player_id="kraw",
        trophy_id="hume_warrior_skull",
        source="raid_san_doria",
    )
    assert res.accepted
    assert res.trophies_total == 1


def test_mount_trophy_slot_full():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    # BURROW trophy slots = 1
    h.mount_trophy(
        player_id="kraw",
        trophy_id="t1", source="raid",
    )
    res = h.mount_trophy(
        player_id="kraw",
        trophy_id="t2", source="raid",
    )
    assert not res.accepted


def test_mount_trophy_duplicate():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    h.mount_trophy(
        player_id="kraw", trophy_id="t1", source="raid",
    )
    # Bump tier so we have another slot
    h.upgrade_tier(
        player_id="kraw", gold_paid=999_999, rep_paid=99_999,
    )
    res = h.mount_trophy(
        player_id="kraw", trophy_id="t1", source="raid",
    )
    assert not res.accepted


def test_upgrade_tier_basic():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    res = h.upgrade_tier(
        player_id="kraw", gold_paid=10_000, rep_paid=300,
    )
    assert res.accepted
    assert res.new_tier == LairTier.DEN


def test_upgrade_insufficient_gold():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    res = h.upgrade_tier(
        player_id="kraw", gold_paid=100, rep_paid=300,
    )
    assert not res.accepted


def test_upgrade_insufficient_rep():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    res = h.upgrade_tier(
        player_id="kraw", gold_paid=10_000, rep_paid=10,
    )
    assert not res.accepted


def test_upgrade_no_lair():
    h = BeastmanLairHouse()
    res = h.upgrade_tier(
        player_id="ghost", gold_paid=99_999, rep_paid=99_999,
    )
    assert not res.accepted


def test_upgrade_to_max_then_block():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    h.upgrade_tier(
        player_id="kraw", gold_paid=10_000, rep_paid=300,
    )
    h.upgrade_tier(
        player_id="kraw", gold_paid=60_000, rep_paid=2_000,
    )
    h.upgrade_tier(
        player_id="kraw", gold_paid=400_000, rep_paid=10_000,
    )
    res = h.upgrade_tier(
        player_id="kraw", gold_paid=999_999, rep_paid=99_999,
    )
    assert not res.accepted


def test_lair_summary():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    h.place_furniture(
        player_id="kraw", item_id="a", slots_used=2,
    )
    s = h.lair_summary(player_id="kraw")
    assert s is not None
    assert s.decor_used == 2
    assert s.decor_capacity == 6
    assert s.trophy_slots == 1


def test_lair_summary_unknown():
    h = BeastmanLairHouse()
    assert h.lair_summary(player_id="ghost") is None


def test_summary_tier_scales():
    h = BeastmanLairHouse()
    h.open_lair(player_id="kraw", race=BeastmanRace.YAGUDO)
    h.upgrade_tier(
        player_id="kraw", gold_paid=10_000, rep_paid=300,
    )
    s = h.lair_summary(player_id="kraw")
    assert s.tier == LairTier.DEN
    assert s.decor_capacity == 12
    assert s.trophy_slots == 3
    assert s.garden_plots == 2


def test_total_lairs():
    h = BeastmanLairHouse()
    h.open_lair(player_id="a", race=BeastmanRace.YAGUDO)
    h.open_lair(player_id="b", race=BeastmanRace.ORC)
    assert h.total_lairs() == 2
