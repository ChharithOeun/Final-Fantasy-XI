"""Tests for water_skin."""
from __future__ import annotations

from server.water_skin import SkinTier, WaterSkinRegistry


def test_craft_happy():
    r = WaterSkinRegistry()
    ok = r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.BASIC_LEATHER, crafted_at=10,
    )
    assert ok is True
    assert r.capacity(skin_id="ws1") == 6


def test_blank_id_blocked():
    r = WaterSkinRegistry()
    out = r.craft(
        skin_id="", owner_id="alice",
        tier=SkinTier.BASIC_LEATHER, crafted_at=10,
    )
    assert out is False


def test_blank_owner_blocked():
    r = WaterSkinRegistry()
    out = r.craft(
        skin_id="ws1", owner_id="",
        tier=SkinTier.BASIC_LEATHER, crafted_at=10,
    )
    assert out is False


def test_duplicate_blocked():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.BASIC_LEATHER, crafted_at=10,
    )
    again = r.craft(
        skin_id="ws1", owner_id="bob",
        tier=SkinTier.OILED_LEATHER, crafted_at=20,
    )
    assert again is False


def test_starts_full():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.OILED_LEATHER, crafted_at=10,
    )
    assert r.level(skin_id="ws1") == 10


def test_drink_restores_thirst():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.OILED_LEATHER, crafted_at=10,
    )
    out = r.drink(skin_id="ws1")
    assert out == 10
    assert r.level(skin_id="ws1") == 9


def test_drink_when_empty():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.BASIC_LEATHER, crafted_at=10,
    )
    for _ in range(6):
        r.drink(skin_id="ws1")
    out = r.drink(skin_id="ws1")
    assert out == 0


def test_drink_unknown():
    r = WaterSkinRegistry()
    out = r.drink(skin_id="ghost")
    assert out == 0


def test_refill_at_spring():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.OILED_LEATHER, crafted_at=10,
    )
    # drink down
    for _ in range(5):
        r.drink(skin_id="ws1")
    # refill 3 sec at spring (rate 1/sec)
    out = r.refill(
        skin_id="ws1", source_kind="spring",
        dt_seconds=3,
    )
    assert out == 8


def test_refill_caps_at_capacity():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.OILED_LEATHER, crafted_at=10,
    )
    out = r.refill(
        skin_id="ws1", source_kind="spring",
        dt_seconds=999,
    )
    assert out == 10


def test_refill_invalid_source():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.BASIC_LEATHER, crafted_at=10,
    )
    r.drink(skin_id="ws1")
    out = r.refill(
        skin_id="ws1", source_kind="lake_with_fish",
        dt_seconds=10,
    )
    # not refilled
    assert out == 5


def test_refill_clean_water_source():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.OILED_LEATHER, crafted_at=10,
    )
    r.drink(skin_id="ws1")
    out = r.refill(
        skin_id="ws1", source_kind="clean_water",
        dt_seconds=1,
    )
    assert out == 10


def test_refill_zero_dt_no_change():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.OILED_LEATHER, crafted_at=10,
    )
    r.drink(skin_id="ws1")
    out = r.refill(
        skin_id="ws1", source_kind="spring",
        dt_seconds=0,
    )
    assert out == 9


def test_higher_tier_more_capacity():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="basic", owner_id="alice",
        tier=SkinTier.BASIC_LEATHER, crafted_at=10,
    )
    r.craft(
        skin_id="dragon", owner_id="alice",
        tier=SkinTier.DRAGONHIDE, crafted_at=20,
    )
    assert r.capacity(skin_id="basic") == 6
    assert r.capacity(skin_id="dragon") == 24


def test_dragonhide_refill_rate():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="ws1", owner_id="alice",
        tier=SkinTier.DRAGONHIDE, crafted_at=10,
    )
    # drink down to 0
    for _ in range(24):
        r.drink(skin_id="ws1")
    # refill 5 sec at rate 3/sec → 15
    out = r.refill(
        skin_id="ws1", source_kind="spring",
        dt_seconds=5,
    )
    assert out == 15


def test_total_skins():
    r = WaterSkinRegistry()
    r.craft(
        skin_id="a", owner_id="alice",
        tier=SkinTier.BASIC_LEATHER, crafted_at=10,
    )
    r.craft(
        skin_id="b", owner_id="alice",
        tier=SkinTier.OILED_LEATHER, crafted_at=20,
    )
    assert r.total_skins() == 2


def test_four_tiers():
    assert len(list(SkinTier)) == 4


def test_unknown_skin_zero_capacity():
    r = WaterSkinRegistry()
    assert r.capacity(skin_id="ghost") == 0
    assert r.level(skin_id="ghost") == 0


def test_refill_unknown_skin():
    r = WaterSkinRegistry()
    out = r.refill(
        skin_id="ghost", source_kind="spring", dt_seconds=10,
    )
    assert out == 0
