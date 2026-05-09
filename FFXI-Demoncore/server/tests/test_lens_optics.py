"""Tests for lens_optics."""
from __future__ import annotations

import pytest

from server.lens_optics import (
    BokehShape, FlareColor, LENSES, LensOpticsSystem,
    LensProfile, list_lenses,
)


def test_lens_count():
    # Cooke 5 + Atlas 3 + Zeiss 3 + Helios 1 = 12
    assert len(LENSES) == 12


def test_cooke_set():
    cooke = [n for n in LENSES if n.startswith("cooke_s4_")]
    assert len(cooke) == 5


def test_atlas_set():
    atlas = [n for n in LENSES if n.startswith("atlas_orion_")]
    assert len(atlas) == 3


def test_zeiss_set():
    zeiss = [n for n in LENSES if n.startswith("zeiss_master_")]
    assert len(zeiss) == 3


def test_helios_set():
    assert "helios_44_2_58mm" in LENSES


def test_select_lens_happy():
    s = LensOpticsSystem()
    p = s.select_lens("cooke_s4_50mm")
    assert isinstance(p, LensProfile)
    assert s.lens is p


def test_select_lens_unknown_raises():
    s = LensOpticsSystem()
    with pytest.raises(ValueError):
        s.select_lens("leica_summilux")


def test_set_aperture_happy():
    s = LensOpticsSystem()
    s.select_lens("zeiss_master_50mm")
    s.set_aperture(2.0)
    assert s.aperture == 2.0


def test_set_aperture_no_lens_raises():
    s = LensOpticsSystem()
    with pytest.raises(RuntimeError):
        s.set_aperture(2.8)


def test_set_aperture_too_wide_blocked():
    s = LensOpticsSystem()
    s.select_lens("cooke_s4_50mm")  # T2.0 minimum
    with pytest.raises(ValueError):
        s.set_aperture(1.4)


def test_set_aperture_too_narrow_blocked():
    s = LensOpticsSystem()
    s.select_lens("atlas_orion_40mm")  # T16 max
    with pytest.raises(ValueError):
        s.set_aperture(22.0)


def test_atlas_is_anamorphic():
    assert LENSES["atlas_orion_40mm"].anamorphic_squeeze == 2.0


def test_cooke_is_spherical():
    assert LENSES["cooke_s4_50mm"].anamorphic_squeeze == 1.0


def test_atlas_blue_flare():
    assert LENSES["atlas_orion_65mm"].flare_color == FlareColor.BLUE


def test_helios_cat_eye_bokeh():
    s = LensOpticsSystem()
    s.select_lens("helios_44_2_58mm")
    assert s.bokeh_shape() == BokehShape.CAT_EYE


def test_atlas_oval_bokeh():
    s = LensOpticsSystem()
    s.select_lens("atlas_orion_100mm")
    assert s.bokeh_shape() == BokehShape.OVAL


def test_bokeh_no_lens_raises():
    s = LensOpticsSystem()
    with pytest.raises(RuntimeError):
        s.bokeh_shape()


def test_flare_intensity_scales_with_lux():
    s = LensOpticsSystem()
    s.select_lens("zeiss_master_50mm")
    low = s.flare_intensity(100)
    high = s.flare_intensity(50000)
    assert high > low


def test_flare_intensity_anamorphic_boost():
    s = LensOpticsSystem()
    s.select_lens("zeiss_master_50mm")
    spherical = s.flare_intensity(10000)
    s.select_lens("atlas_orion_65mm")
    anamorphic = s.flare_intensity(10000)
    assert anamorphic > spherical


def test_flare_intensity_capped_at_one():
    s = LensOpticsSystem()
    s.select_lens("atlas_orion_40mm")
    assert s.flare_intensity(1e9) <= 1.0


def test_flare_intensity_negative_lux_raises():
    s = LensOpticsSystem()
    s.select_lens("cooke_s4_50mm")
    with pytest.raises(ValueError):
        s.flare_intensity(-10)


def test_dof_wider_aperture_shallower():
    s = LensOpticsSystem()
    s.select_lens("zeiss_master_85mm")
    s.set_aperture(1.4)
    shallow = s.depth_of_field_meters(focus_distance=2.0)
    s.set_aperture(11.0)
    deep = s.depth_of_field_meters(focus_distance=2.0)
    assert deep > shallow


def test_dof_longer_lens_shallower():
    s = LensOpticsSystem()
    s.select_lens("cooke_s4_32mm")
    s.set_aperture(2.8)
    wide_dof = s.depth_of_field_meters(focus_distance=3.0)
    s.select_lens("cooke_s4_100mm")
    s.set_aperture(2.8)
    long_dof = s.depth_of_field_meters(focus_distance=3.0)
    assert long_dof < wide_dof


def test_dof_no_lens_raises():
    s = LensOpticsSystem()
    with pytest.raises(RuntimeError):
        s.depth_of_field_meters(focus_distance=2.0)


def test_dof_zero_distance_raises():
    s = LensOpticsSystem()
    s.select_lens("cooke_s4_50mm")
    with pytest.raises(ValueError):
        s.depth_of_field_meters(focus_distance=0)


def test_set_focus_distance_negative_blocked():
    s = LensOpticsSystem()
    with pytest.raises(ValueError):
        s.set_focus_distance(-1)


def test_render_intent_carries_squeeze():
    s = LensOpticsSystem()
    s.select_lens("atlas_orion_65mm")
    intent = s.get_render_intent()
    assert intent["anamorphic_squeeze"] == 2.0
    assert intent["flare_color"] == "blue"


def test_list_lenses_sorted():
    names = list_lenses()
    assert names == tuple(sorted(names))
