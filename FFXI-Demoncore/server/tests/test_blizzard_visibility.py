"""Tests for blizzard_visibility."""
from __future__ import annotations

from server.blizzard_visibility import VisibilityCalculator


def test_clear_weather_no_penalty():
    v = VisibilityCalculator()
    assert v.compute_radius(
        baseline=50, weather_kind="clear", intensity=0,
    ) == 50


def test_rain_no_penalty():
    v = VisibilityCalculator()
    assert v.compute_radius(
        baseline=50, weather_kind="rain", intensity=100,
    ) == 50


def test_blizzard_70_percent_at_full():
    v = VisibilityCalculator()
    # 50 baseline, blizzard factor 0.7 → penalty 70 → 30%
    assert v.compute_radius(
        baseline=50, weather_kind="blizzard", intensity=100,
    ) == 15


def test_blizzard_partial_intensity():
    v = VisibilityCalculator()
    # intensity 50 → penalty 35 → 65%
    out = v.compute_radius(
        baseline=100, weather_kind="blizzard", intensity=50,
    )
    assert out == 65


def test_sandstorm_60_percent_at_full():
    v = VisibilityCalculator()
    # baseline 50, sandstorm 0.6 → penalty 60 → 40%
    out = v.compute_radius(
        baseline=50, weather_kind="sandstorm", intensity=100,
    )
    assert out == 20


def test_fog_full_penalty():
    v = VisibilityCalculator()
    # fog penalty = intensity, but capped at 95
    out = v.compute_radius(
        baseline=100, weather_kind="fog", intensity=100,
    )
    # 100 - 95 = 5%
    assert out == 5


def test_fog_partial():
    v = VisibilityCalculator()
    out = v.compute_radius(
        baseline=100, weather_kind="fog", intensity=40,
    )
    assert out == 60


def test_torch_helps():
    v = VisibilityCalculator()
    no_torch = v.compute_radius(
        baseline=50, weather_kind="blizzard", intensity=100,
    )
    with_torch = v.compute_radius(
        baseline=50, weather_kind="blizzard",
        intensity=100, torch_radius=12,
    )
    assert with_torch > no_torch


def test_torch_cant_exceed_baseline():
    v = VisibilityCalculator()
    out = v.compute_radius(
        baseline=50, weather_kind="clear", intensity=0,
        torch_radius=999,
    )
    assert out == 50


def test_torch_in_clear_no_change():
    v = VisibilityCalculator()
    # clear has no penalty, so radius is already baseline
    out = v.compute_radius(
        baseline=50, weather_kind="clear", intensity=0,
        torch_radius=10,
    )
    assert out == 50


def test_negative_intensity_clamps_to_zero():
    v = VisibilityCalculator()
    out = v.compute_radius(
        baseline=100, weather_kind="blizzard", intensity=-10,
    )
    # treated as 0 → no penalty
    assert out == 100


def test_intensity_above_100_capped():
    v = VisibilityCalculator()
    out = v.compute_radius(
        baseline=100, weather_kind="blizzard", intensity=200,
    )
    # treated as 100 → 70% penalty → 30
    assert out == 30


def test_zero_baseline_zero_radius():
    v = VisibilityCalculator()
    out = v.compute_radius(
        baseline=0, weather_kind="clear", intensity=0,
    )
    assert out == 0


def test_negative_baseline_zero_radius():
    v = VisibilityCalculator()
    out = v.compute_radius(
        baseline=-10, weather_kind="clear", intensity=0,
    )
    assert out == 0


def test_unknown_weather_no_penalty():
    v = VisibilityCalculator()
    out = v.compute_radius(
        baseline=50, weather_kind="auroras", intensity=100,
    )
    assert out == 50


def test_torch_partial_through_blizzard():
    v = VisibilityCalculator()
    # blizzard gives 30% × 100 = 30 yalms; torch +12 = 42
    out = v.compute_radius(
        baseline=100, weather_kind="blizzard",
        intensity=100, torch_radius=12,
    )
    assert out == 42


def test_sandstorm_no_torch():
    v = VisibilityCalculator()
    # sandstorm 60% penalty at full intensity, baseline 100
    # → 40 yalms
    out = v.compute_radius(
        baseline=100, weather_kind="sandstorm",
        intensity=100,
    )
    assert out == 40
