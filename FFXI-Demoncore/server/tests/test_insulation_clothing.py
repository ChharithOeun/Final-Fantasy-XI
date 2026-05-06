"""Tests for insulation_clothing."""
from __future__ import annotations

from server.insulation_clothing import (
    GarmentSlot,
    InsulationCalculator,
)


def _setup():
    c = InsulationCalculator()
    c.define_garment(
        garment_id="fur_cap", slot=GarmentSlot.HEAD,
        cold_rating=10, heat_rating=0, seasonal="winter",
    )
    c.define_garment(
        garment_id="fur_cloak", slot=GarmentSlot.CLOAK,
        cold_rating=20, heat_rating=0, seasonal="winter",
    )
    c.define_garment(
        garment_id="silk_robe", slot=GarmentSlot.BODY,
        cold_rating=0, heat_rating=15, seasonal="summer",
    )
    c.define_garment(
        garment_id="leather_boots", slot=GarmentSlot.FEET,
        cold_rating=5, heat_rating=5,
    )
    return c


def test_define_garment_happy():
    c = _setup()
    assert c.total_garments_defined() == 4


def test_define_blank_id_blocked():
    c = InsulationCalculator()
    out = c.define_garment(
        garment_id="", slot=GarmentSlot.HEAD,
        cold_rating=5, heat_rating=0,
    )
    assert out is False


def test_negative_rating_blocked():
    c = InsulationCalculator()
    out = c.define_garment(
        garment_id="x", slot=GarmentSlot.HEAD,
        cold_rating=-1, heat_rating=0,
    )
    assert out is False


def test_duplicate_garment_blocked():
    c = _setup()
    again = c.define_garment(
        garment_id="fur_cap", slot=GarmentSlot.HEAD,
        cold_rating=99, heat_rating=0,
    )
    assert again is False


def test_equip_happy():
    c = _setup()
    ok = c.equip(
        player_id="alice", garment_id="fur_cap",
    )
    assert ok is True


def test_equip_unknown_garment():
    c = _setup()
    out = c.equip(
        player_id="alice", garment_id="ghost",
    )
    assert out is False


def test_equip_blank_player():
    c = _setup()
    out = c.equip(player_id="", garment_id="fur_cap")
    assert out is False


def test_total_cold_aggregate():
    c = _setup()
    c.equip(player_id="alice", garment_id="fur_cap")
    c.equip(player_id="alice", garment_id="fur_cloak")
    c.equip(player_id="alice", garment_id="leather_boots")
    # 10 + 20 + 5 = 35
    assert c.total_cold(player_id="alice") == 35


def test_total_heat_aggregate():
    c = _setup()
    c.equip(player_id="alice", garment_id="silk_robe")
    c.equip(player_id="alice", garment_id="leather_boots")
    # 15 + 5 = 20
    assert c.total_heat(player_id="alice") == 20


def test_seasonal_mismatch_penalty():
    c = _setup()
    c.equip(player_id="alice", garment_id="fur_cap")
    # winter cap in summer climate → -5 penalty
    no_climate = c.total_cold(player_id="alice")
    summer_climate = c.total_cold(
        player_id="alice", current_climate="summer",
    )
    assert no_climate == 10
    assert summer_climate == 5


def test_seasonal_match_no_penalty():
    c = _setup()
    c.equip(player_id="alice", garment_id="fur_cap")
    out = c.total_cold(
        player_id="alice", current_climate="winter",
    )
    assert out == 10


def test_unseasonal_garment_no_penalty():
    c = _setup()
    c.equip(player_id="alice", garment_id="leather_boots")
    out = c.total_cold(
        player_id="alice", current_climate="summer",
    )
    # leather_boots has no seasonal → unaffected
    assert out == 5


def test_unequip_happy():
    c = _setup()
    c.equip(player_id="alice", garment_id="fur_cap")
    assert c.unequip(
        player_id="alice", slot=GarmentSlot.HEAD,
    ) is True


def test_unequip_when_not_equipped():
    c = _setup()
    out = c.unequip(
        player_id="alice", slot=GarmentSlot.HEAD,
    )
    assert out is False


def test_equip_replaces_slot():
    c = _setup()
    c.define_garment(
        garment_id="straw_hat", slot=GarmentSlot.HEAD,
        cold_rating=0, heat_rating=8,
    )
    c.equip(player_id="alice", garment_id="fur_cap")
    c.equip(player_id="alice", garment_id="straw_hat")
    out = c.equipped_in_slot(
        player_id="alice", slot=GarmentSlot.HEAD,
    )
    assert out == "straw_hat"


def test_equipped_in_slot_unknown():
    c = _setup()
    out = c.equipped_in_slot(
        player_id="ghost", slot=GarmentSlot.HEAD,
    )
    assert out is None


def test_six_garment_slots():
    assert len(list(GarmentSlot)) == 6


def test_total_for_unknown_player_zero():
    c = _setup()
    assert c.total_cold(player_id="ghost") == 0
    assert c.total_heat(player_id="ghost") == 0


def test_floor_at_zero_with_penalty():
    c = InsulationCalculator()
    # rating below penalty → floors at 0
    c.define_garment(
        garment_id="thin_summer_shirt",
        slot=GarmentSlot.BODY,
        cold_rating=2, heat_rating=10,
        seasonal="summer",
    )
    c.equip(
        player_id="alice", garment_id="thin_summer_shirt",
    )
    out = c.total_cold(
        player_id="alice", current_climate="winter",
    )
    # 2 - 5 → 0 (floored)
    assert out == 0
