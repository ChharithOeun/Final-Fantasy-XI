"""Tests for film_grade."""
from __future__ import annotations

import math

import pytest

from server.film_grade import (
    FilmGradeSystem, LUT, LUTS, Look, SourceSpace,
    SKIN_TONE_TARGET, list_luts, wb_label,
)


def test_seven_luts_seeded():
    assert len(LUTS) == 7


def test_lut_names():
    expected = {
        "kodak_vision3_250d", "kodak_vision3_500t",
        "fuji_eterna_250d", "cinestyle_technicolor",
        "bleach_bypass", "day_for_night",
        "demoncore_standard",
    }
    assert set(LUTS) == expected


def test_lut_dataclass_frozen():
    import dataclasses as _dc
    lut = LUTS["demoncore_standard"]
    with pytest.raises(_dc.FrozenInstanceError):
        lut.name = "x"  # type: ignore[misc]


def test_apply_lut_happy():
    s = FilmGradeSystem()
    lut = s.apply_lut("kodak_vision3_250d")
    assert isinstance(lut, LUT)
    assert s.current_lut is lut


def test_apply_lut_unknown_raises():
    s = FilmGradeSystem()
    with pytest.raises(ValueError):
        s.apply_lut("kodak_kodachrome")


def test_exposure_meter_underexposed_returns_positive_ev():
    s = FilmGradeSystem()
    # half of zone V => need +1 EV
    ev = s.exposure_meter(SKIN_TONE_TARGET / 2)
    assert ev == pytest.approx(1.0)


def test_exposure_meter_overexposed_returns_negative_ev():
    s = FilmGradeSystem()
    ev = s.exposure_meter(SKIN_TONE_TARGET * 2)
    assert ev == pytest.approx(-1.0)


def test_exposure_meter_at_target_zero_ev():
    s = FilmGradeSystem()
    ev = s.exposure_meter(SKIN_TONE_TARGET)
    assert ev == pytest.approx(0.0)


def test_exposure_meter_zero_lum_raises():
    s = FilmGradeSystem()
    with pytest.raises(ValueError):
        s.exposure_meter(0)


def test_exposure_meter_negative_lum_raises():
    s = FilmGradeSystem()
    with pytest.raises(ValueError):
        s.exposure_meter(-0.1)


def test_white_balance_tungsten():
    s = FilmGradeSystem()
    assert s.white_balance_kelvin_set(3200) == "tungsten"


def test_white_balance_daylight():
    s = FilmGradeSystem()
    assert s.white_balance_kelvin_set(5600) == "daylight"


def test_white_balance_overcast():
    s = FilmGradeSystem()
    assert s.white_balance_kelvin_set(10000) == "overcast"


def test_white_balance_out_of_range():
    s = FilmGradeSystem()
    with pytest.raises(ValueError):
        s.white_balance_kelvin_set(500)


def test_aces_transform_neutral_no_lut():
    s = FilmGradeSystem()
    out = s.aces_transform((0.5, 0.5, 0.5))
    assert out == (0.5, 0.5, 0.5)


def test_aces_transform_applies_exposure():
    s = FilmGradeSystem()
    s.exposure_ev = 1.0  # +1 stop
    r, g, b = s.aces_transform((0.1, 0.1, 0.1))
    assert r == pytest.approx(0.2)


def test_aces_transform_applies_lut_tint():
    s = FilmGradeSystem()
    s.apply_lut("kodak_vision3_500t")  # cool tint
    r, g, b = s.aces_transform((0.5, 0.5, 0.5))
    # blue channel boosted relative to red
    assert b > r


def test_aces_transform_negative_input_raises():
    s = FilmGradeSystem()
    with pytest.raises(ValueError):
        s.aces_transform((-0.1, 0, 0))


def test_render_intent_has_rrt_odt():
    s = FilmGradeSystem()
    intent = s.get_render_intent()
    assert "RRT" in intent["rrt"]
    assert "ODT" in intent["odt"]


def test_render_intent_carries_lut_meta_when_set():
    s = FilmGradeSystem()
    s.apply_lut("bleach_bypass")
    intent = s.get_render_intent()
    assert intent["lut"] == "bleach_bypass"
    assert intent["target_look"] == "high_contrast"


def test_render_intent_has_skin_tone_target():
    s = FilmGradeSystem()
    intent = s.get_render_intent()
    assert intent["skin_tone_target"] == SKIN_TONE_TARGET


def test_list_luts_sorted():
    names = list_luts()
    assert names == tuple(sorted(names))


def test_wb_label_rounding_picks_nearest():
    # 5200K is between 4300 (fluorescent) and 5600 (daylight)
    # — closer to daylight
    assert wb_label(5200) == "daylight"


def test_source_space_enum_count():
    assert len(list(SourceSpace)) == 3


def test_look_enum_count():
    assert len(list(Look)) == 7
