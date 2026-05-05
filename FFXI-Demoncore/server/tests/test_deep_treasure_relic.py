"""Tests for deep treasure relic."""
from __future__ import annotations

from server.deep_treasure_relic import DeepTreasureRelic, RelicGrade


def test_seed_wreck_happy():
    d = DeepTreasureRelic()
    ok = d.seed_wreck(
        ship_id="argo", grade=RelicGrade.AMBER, capacity=3,
    )
    assert ok is True
    assert d.remaining_capacity(ship_id="argo") == 3


def test_seed_wreck_blank_id():
    d = DeepTreasureRelic()
    ok = d.seed_wreck(
        ship_id="", grade=RelicGrade.AMBER, capacity=1,
    )
    assert ok is False


def test_seed_wreck_zero_capacity():
    d = DeepTreasureRelic()
    ok = d.seed_wreck(
        ship_id="x", grade=RelicGrade.AMBER, capacity=0,
    )
    assert ok is False


def test_seed_wreck_duplicate():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.AMBER, capacity=1)
    ok = d.seed_wreck(ship_id="x", grade=RelicGrade.AMBER, capacity=1)
    assert ok is False


def test_roll_amber_success():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.AMBER, capacity=2)
    r = d.roll(
        ship_id="x", diver_skill=70,
        treasure_hunter=0, has_abyss_permit=False,
    )
    assert r.accepted is True
    assert r.grade == RelicGrade.AMBER
    assert r.piece_index == 1
    assert d.remaining_capacity(ship_id="x") == 1


def test_roll_amber_failure_below_threshold():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.AMBER, capacity=1)
    r = d.roll(
        ship_id="x", diver_skill=20,
        treasure_hunter=0, has_abyss_permit=False,
    )
    assert r.accepted is False
    assert r.reason == "failed roll"


def test_roll_th_helps():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.AMBER, capacity=1)
    # 50 + TH 4 * 10 = 90 >= 60
    r = d.roll(
        ship_id="x", diver_skill=50,
        treasure_hunter=4, has_abyss_permit=False,
    )
    assert r.accepted is True


def test_roll_gold_threshold():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.GOLD, capacity=1)
    # gold threshold 120 — skill 100 + TH 5*10 = 150
    r = d.roll(
        ship_id="x", diver_skill=100,
        treasure_hunter=5, has_abyss_permit=False,
    )
    assert r.accepted is True


def test_roll_abyssal_requires_permit():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.ABYSSAL, capacity=1)
    r = d.roll(
        ship_id="x", diver_skill=400,
        treasure_hunter=10, has_abyss_permit=False,
    )
    assert r.accepted is False
    assert r.reason == "abyss permit required"


def test_roll_abyssal_with_permit_succeeds():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.ABYSSAL, capacity=1)
    # abyssal threshold 200 — skill 250 clears
    r = d.roll(
        ship_id="x", diver_skill=250,
        treasure_hunter=0, has_abyss_permit=True,
    )
    assert r.accepted is True
    assert r.grade == RelicGrade.ABYSSAL


def test_roll_unknown_wreck():
    d = DeepTreasureRelic()
    r = d.roll(
        ship_id="ghost", diver_skill=999,
        treasure_hunter=10, has_abyss_permit=True,
    )
    assert r.accepted is False
    assert r.reason == "unknown wreck"


def test_roll_negative_skill():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.AMBER, capacity=1)
    r = d.roll(
        ship_id="x", diver_skill=-1,
        treasure_hunter=0, has_abyss_permit=False,
    )
    assert r.accepted is False


def test_capacity_drains_to_exhaustion():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.AMBER, capacity=2)
    r1 = d.roll(
        ship_id="x", diver_skill=70,
        treasure_hunter=0, has_abyss_permit=False,
    )
    assert r1.accepted is True
    assert r1.exhausted is False
    r2 = d.roll(
        ship_id="x", diver_skill=70,
        treasure_hunter=0, has_abyss_permit=False,
    )
    assert r2.accepted is True
    assert r2.exhausted is True
    r3 = d.roll(
        ship_id="x", diver_skill=70,
        treasure_hunter=0, has_abyss_permit=False,
    )
    assert r3.accepted is False
    assert r3.reason == "exhausted"


def test_piece_index_increments():
    d = DeepTreasureRelic()
    d.seed_wreck(ship_id="x", grade=RelicGrade.AMBER, capacity=3)
    r1 = d.roll(
        ship_id="x", diver_skill=70,
        treasure_hunter=0, has_abyss_permit=False,
    )
    r2 = d.roll(
        ship_id="x", diver_skill=70,
        treasure_hunter=0, has_abyss_permit=False,
    )
    assert r1.piece_index == 1
    assert r2.piece_index == 2
