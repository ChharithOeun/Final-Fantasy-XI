"""Tests for exposure_damage."""
from __future__ import annotations

from server.exposure_damage import ExposureCalculator, ExposureKind


def test_neutral_zone_no_damage():
    e = ExposureCalculator()
    out = e.compute(exposure_level=0, dt_seconds=10)
    assert out.kind == ExposureKind.NEUTRAL
    assert out.hp_damage == 0
    assert out.mp_damage == 0


def test_below_threshold_no_damage():
    e = ExposureCalculator()
    out = e.compute(exposure_level=-20, dt_seconds=10)
    assert out.kind == ExposureKind.COLD
    assert out.hp_damage == 0


def test_cold_above_threshold_drains_hp():
    e = ExposureCalculator()
    out = e.compute(exposure_level=-50, dt_seconds=1)
    # (50-30)/5 = 4 per sec * 1
    assert out.kind == ExposureKind.COLD
    assert out.hp_damage == 4
    assert out.mp_damage == 0


def test_hot_above_threshold_drains_mp():
    e = ExposureCalculator()
    out = e.compute(exposure_level=80, dt_seconds=1)
    # (80-30)/5 = 10 per sec
    assert out.kind == ExposureKind.HOT
    assert out.mp_damage == 10
    assert out.hp_damage == 0


def test_insulation_mitigates():
    e = ExposureCalculator()
    out = e.compute(
        exposure_level=-50, dt_seconds=1,
        insulation_rating=20,
    )
    # magnitude becomes 30 → at threshold → no damage
    assert out.hp_damage == 0


def test_insulation_partial():
    e = ExposureCalculator()
    out = e.compute(
        exposure_level=-100, dt_seconds=1,
        insulation_rating=30,
    )
    # magnitude = 70 → (70-30)/5 = 8
    assert out.hp_damage == 8


def test_shelter_halves_damage():
    e = ExposureCalculator()
    out_no_shelter = e.compute(
        exposure_level=-100, dt_seconds=1,
    )
    out_shelter = e.compute(
        exposure_level=-100, dt_seconds=1,
        shelter_active=True,
    )
    assert out_shelter.hp_damage <= out_no_shelter.hp_damage // 2 + 1


def test_zero_dt_no_damage():
    e = ExposureCalculator()
    out = e.compute(exposure_level=-100, dt_seconds=0)
    assert out.hp_damage == 0
    assert out.mp_damage == 0


def test_long_tick_accumulates():
    e = ExposureCalculator()
    out = e.compute(exposure_level=-50, dt_seconds=10)
    # 4 per sec * 10 = 40
    assert out.hp_damage == 40


def test_extreme_cold():
    e = ExposureCalculator()
    out = e.compute(exposure_level=-100, dt_seconds=1)
    # (100-30)/5 = 14
    assert out.hp_damage == 14


def test_extreme_hot():
    e = ExposureCalculator()
    out = e.compute(exposure_level=100, dt_seconds=1)
    assert out.mp_damage == 14


def test_full_insulation_negates():
    e = ExposureCalculator()
    out = e.compute(
        exposure_level=-50, dt_seconds=10,
        insulation_rating=100,
    )
    assert out.hp_damage == 0
    assert out.kind == ExposureKind.NEUTRAL


def test_effective_exposure_returned():
    e = ExposureCalculator()
    out = e.compute(
        exposure_level=-100, dt_seconds=1,
        insulation_rating=20,
    )
    assert out.effective_exposure == -80


def test_three_exposure_kinds():
    assert len(list(ExposureKind)) == 3


def test_minimum_per_sec_one():
    e = ExposureCalculator()
    # exposure 35 → (35-30)/5 = 1 per sec
    out = e.compute(exposure_level=35, dt_seconds=1)
    assert out.mp_damage == 1


def test_shelter_minimum_one():
    e = ExposureCalculator()
    # 35 hot → 1 per sec → halved → still 1 minimum
    out = e.compute(
        exposure_level=35, dt_seconds=1,
        shelter_active=True,
    )
    assert out.mp_damage == 1


def test_negative_dt_no_damage():
    e = ExposureCalculator()
    out = e.compute(exposure_level=-100, dt_seconds=-1)
    assert out.hp_damage == 0
