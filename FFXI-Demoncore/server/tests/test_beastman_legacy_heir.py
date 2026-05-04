"""Tests for the beastman legacy heir."""
from __future__ import annotations

from server.beastman_legacy_heir import BeastmanLegacyHeir
from server.beastman_playable_races import BeastmanRace


def test_declare_heir_basic():
    h = BeastmanLegacyHeir()
    res = h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    assert res
    assert h.total_estates() == 1


def test_declare_heir_empty_id():
    h = BeastmanLegacyHeir()
    res = h.declare_heir(
        deceased_id="",
        heir_id="x",
        race=BeastmanRace.YAGUDO,
    )
    assert not res


def test_declare_heir_double_rejected():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    res = h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v3",
        race=BeastmanRace.ORC,
    )
    assert not res


def test_set_estate_basic():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    res = h.set_estate(
        deceased_id="kraw_v1",
        gil=200_000,
        bytnes=10_000,
        lair_tier_index=2,
    )
    assert res


def test_set_estate_negative_rejected():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    res = h.set_estate(
        deceased_id="kraw_v1",
        gil=-100,
        bytnes=0,
        lair_tier_index=0,
    )
    assert not res


def test_set_estate_negative_lair_rejected():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    res = h.set_estate(
        deceased_id="kraw_v1",
        gil=0, bytnes=0,
        lair_tier_index=-1,
    )
    assert not res


def test_add_heirloom_basic():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    res = h.add_heirloom(
        deceased_id="kraw_v1",
        item_id="vermillion_cloak",
    )
    assert res


def test_add_heirloom_double_rejected():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.add_heirloom(
        deceased_id="kraw_v1",
        item_id="a",
    )
    res = h.add_heirloom(
        deceased_id="kraw_v1",
        item_id="b",
    )
    assert not res


def test_add_heirloom_no_estate():
    h = BeastmanLegacyHeir()
    res = h.add_heirloom(
        deceased_id="ghost",
        item_id="a",
    )
    assert not res


def test_add_heirloom_empty_id():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    res = h.add_heirloom(deceased_id="kraw_v1", item_id="")
    assert not res


def test_execute_inheritance_basic():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.set_estate(
        deceased_id="kraw_v1",
        gil=200_000,
        bytnes=10_000,
        lair_tier_index=2,
    )
    h.add_heirloom(
        deceased_id="kraw_v1",
        item_id="phantom_jay",
    )
    res = h.execute_inheritance(deceased_id="kraw_v1")
    assert res.accepted
    assert res.gil_passed == 100_000
    assert res.bytnes_passed == 2_500
    assert res.new_lair_tier_index == 1
    assert res.heirloom_id == "phantom_jay"


def test_execute_inheritance_no_heir():
    h = BeastmanLegacyHeir()
    h.set_estate(
        deceased_id="kraw_v1",
        gil=100, bytnes=10,
        lair_tier_index=0,
    )
    res = h.execute_inheritance(deceased_id="kraw_v1")
    assert not res.accepted


def test_execute_inheritance_no_estate():
    h = BeastmanLegacyHeir()
    res = h.execute_inheritance(deceased_id="ghost")
    assert not res.accepted


def test_execute_inheritance_double_blocked():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.set_estate(
        deceased_id="kraw_v1",
        gil=100, bytnes=10,
        lair_tier_index=0,
    )
    h.execute_inheritance(deceased_id="kraw_v1")
    res = h.execute_inheritance(deceased_id="kraw_v1")
    assert not res.accepted


def test_execute_inheritance_gil_cap():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.set_estate(
        deceased_id="kraw_v1",
        gil=10_000_000,
        bytnes=0,
        lair_tier_index=0,
    )
    res = h.execute_inheritance(deceased_id="kraw_v1")
    # 50% of 10M = 5M, capped at 1M
    assert res.gil_passed == 1_000_000


def test_execute_inheritance_bytne_cap():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.set_estate(
        deceased_id="kraw_v1",
        gil=0,
        bytnes=10_000_000,
        lair_tier_index=0,
    )
    res = h.execute_inheritance(deceased_id="kraw_v1")
    # 25% of 10M = 2.5M, capped at 100k
    assert res.bytnes_passed == 100_000


def test_lair_tier_floor_at_zero():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.set_estate(
        deceased_id="kraw_v1",
        gil=0, bytnes=0,
        lair_tier_index=0,
    )
    res = h.execute_inheritance(deceased_id="kraw_v1")
    assert res.new_lair_tier_index == 0


def test_heirloom_race_lock_blocks_pass():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.set_estate(
        deceased_id="kraw_v1",
        gil=0, bytnes=0,
        lair_tier_index=0,
    )
    h.add_heirloom(
        deceased_id="kraw_v1",
        item_id="orc_skull",
        race_locked=BeastmanRace.ORC,
    )
    res = h.execute_inheritance(deceased_id="kraw_v1")
    assert res.heirloom_id == ""


def test_heirloom_race_lock_matches_pass():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.set_estate(
        deceased_id="kraw_v1",
        gil=0, bytnes=0,
        lair_tier_index=0,
    )
    h.add_heirloom(
        deceased_id="kraw_v1",
        item_id="yagudo_relic_axe",
        race_locked=BeastmanRace.YAGUDO,
    )
    res = h.execute_inheritance(deceased_id="kraw_v1")
    assert res.heirloom_id == "yagudo_relic_axe"


def test_set_estate_after_inheritance_blocked():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.set_estate(
        deceased_id="kraw_v1",
        gil=100, bytnes=10,
        lair_tier_index=0,
    )
    h.execute_inheritance(deceased_id="kraw_v1")
    res = h.set_estate(
        deceased_id="kraw_v1",
        gil=999, bytnes=999,
        lair_tier_index=3,
    )
    assert not res


def test_declare_heir_after_execute_blocked():
    h = BeastmanLegacyHeir()
    h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v2",
        race=BeastmanRace.YAGUDO,
    )
    h.execute_inheritance(deceased_id="kraw_v1")
    res = h.declare_heir(
        deceased_id="kraw_v1",
        heir_id="kraw_v3",
        race=BeastmanRace.YAGUDO,
    )
    assert not res
