"""Tests for reverb_zones."""
from __future__ import annotations

import pytest

from server.reverb_zones import (
    ReverbProfile,
    ReverbVolume,
    ReverbZoneSystem,
    interpolate_profiles,
    populate_default_profiles,
)


def _make_profile(
    pid="p",
    rt=1.0,
    er=15.0,
    diff=0.5,
    damp=8000.0,
    hc=14000.0,
    lc=80.0,
    room=1000.0,
    wet=0.4,
):
    return ReverbProfile(
        profile_id=pid,
        rt60_seconds=rt,
        early_reflections_ms=er,
        diffusion=diff,
        damping_freq_hz=damp,
        high_cut_freq_hz=hc,
        low_cut_freq_hz=lc,
        room_size_m3=room,
        wetness=wet,
    )


# ---- profile validation ----

def test_register_profile():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile())
    assert s.profile_count() == 1


def test_register_profile_empty_id():
    s = ReverbZoneSystem()
    with pytest.raises(ValueError):
        s.register_profile(_make_profile(pid=""))


def test_register_profile_negative_rt60():
    s = ReverbZoneSystem()
    with pytest.raises(ValueError):
        s.register_profile(_make_profile(rt=-1.0))


def test_register_profile_diffusion_out_of_range():
    s = ReverbZoneSystem()
    with pytest.raises(ValueError):
        s.register_profile(_make_profile(diff=1.5))


def test_register_profile_wetness_out_of_range():
    s = ReverbZoneSystem()
    with pytest.raises(ValueError):
        s.register_profile(_make_profile(wet=-0.1))


def test_register_profile_high_cut_below_low_cut():
    s = ReverbZoneSystem()
    with pytest.raises(ValueError):
        s.register_profile(_make_profile(hc=100.0, lc=200.0))


def test_register_profile_high_cut_zero():
    s = ReverbZoneSystem()
    with pytest.raises(ValueError):
        s.register_profile(_make_profile(hc=0.0))


def test_register_profile_negative_room_size():
    s = ReverbZoneSystem()
    with pytest.raises(ValueError):
        s.register_profile(_make_profile(room=-1.0))


def test_register_profile_duplicate():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile())
    with pytest.raises(ValueError):
        s.register_profile(_make_profile())


def test_get_profile_unknown():
    s = ReverbZoneSystem()
    with pytest.raises(KeyError):
        s.get_profile("missing")


# ---- zone default ----

def test_set_zone_default_unknown_profile():
    s = ReverbZoneSystem()
    with pytest.raises(KeyError):
        s.set_zone_default("z", "missing")


def test_set_zone_default():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile())
    s.set_zone_default("z", "p")
    p = s.profile_at("z", (0.0, 0.0, 0.0))
    assert p.profile_id == "p"


# ---- volume ----

def test_register_volume():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile())
    s.register_volume(
        "v", "z", (0.0, 0.0, 0.0),
        (10.0, 10.0, 10.0), "p",
    )
    assert s.volume_count() == 1


def test_register_volume_unknown_profile():
    s = ReverbZoneSystem()
    with pytest.raises(KeyError):
        s.register_volume(
            "v", "z", (0, 0, 0), (1, 1, 1), "missing",
        )


def test_register_volume_empty_id():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile())
    with pytest.raises(ValueError):
        s.register_volume(
            "", "z", (0, 0, 0), (1, 1, 1), "p",
        )


def test_register_volume_empty_zone():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile())
    with pytest.raises(ValueError):
        s.register_volume(
            "v", "", (0, 0, 0), (1, 1, 1), "p",
        )


def test_register_volume_inverted_bounds():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile())
    with pytest.raises(ValueError):
        s.register_volume(
            "v", "z", (5, 5, 5), (1, 1, 1), "p",
        )


def test_register_volume_duplicate():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile())
    s.register_volume(
        "v", "z", (0, 0, 0), (1, 1, 1), "p",
    )
    with pytest.raises(ValueError):
        s.register_volume(
            "v", "z", (0, 0, 0), (1, 1, 1), "p",
        )


def test_volume_contains_inside():
    v = ReverbVolume(
        "v", "z", (0, 0, 0), (10, 10, 10), "p",
    )
    assert v.contains((5, 5, 5))


def test_volume_contains_outside():
    v = ReverbVolume(
        "v", "z", (0, 0, 0), (10, 10, 10), "p",
    )
    assert not v.contains((20, 5, 5))


def test_volume_contains_on_boundary():
    v = ReverbVolume(
        "v", "z", (0, 0, 0), (10, 10, 10), "p",
    )
    assert v.contains((10, 10, 10))


def test_volume_m3():
    v = ReverbVolume(
        "v", "z", (0, 0, 0), (2, 3, 5), "p",
    )
    assert v.volume_m3() == pytest.approx(30.0)


# ---- profile_at ----

def test_profile_at_uses_zone_default():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile("z_default"))
    s.set_zone_default("z", "z_default")
    p = s.profile_at("z", (5, 5, 5))
    assert p.profile_id == "z_default"


def test_profile_at_volume_overrides_default():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile("z_default"))
    s.register_profile(_make_profile("inner"))
    s.set_zone_default("z", "z_default")
    s.register_volume(
        "v", "z", (0, 0, 0), (10, 10, 10), "inner",
    )
    p = s.profile_at("z", (5, 5, 5))
    assert p.profile_id == "inner"


def test_profile_at_listener_outside_volume_uses_default():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile("z_default"))
    s.register_profile(_make_profile("inner"))
    s.set_zone_default("z", "z_default")
    s.register_volume(
        "v", "z", (0, 0, 0), (10, 10, 10), "inner",
    )
    p = s.profile_at("z", (50, 50, 50))
    assert p.profile_id == "z_default"


def test_profile_at_smallest_volume_wins():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile("outer"))
    s.register_profile(_make_profile("middle"))
    s.register_profile(_make_profile("inner"))
    s.set_zone_default("z", "outer")
    s.register_volume(
        "vm", "z", (0, 0, 0), (100, 100, 100), "middle",
    )
    s.register_volume(
        "vi", "z", (40, 40, 40), (50, 50, 50), "inner",
    )
    p = s.profile_at("z", (45, 45, 45))
    assert p.profile_id == "inner"


def test_profile_at_unknown_zone_raises():
    s = ReverbZoneSystem()
    with pytest.raises(KeyError):
        s.profile_at("nope", (0, 0, 0))


# ---- profiles_for_zone ----

def test_profiles_for_zone_default_only():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile("p"))
    s.set_zone_default("z", "p")
    profs = s.profiles_for_zone("z")
    assert len(profs) == 1
    assert profs[0].profile_id == "p"


def test_profiles_for_zone_with_volumes():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile("p"))
    s.register_profile(_make_profile("inner"))
    s.set_zone_default("z", "p")
    s.register_volume(
        "v", "z", (0, 0, 0), (1, 1, 1), "inner",
    )
    profs = s.profiles_for_zone("z")
    ids = {p.profile_id for p in profs}
    assert {"p", "inner"} <= ids


def test_profiles_for_zone_unknown_zone():
    s = ReverbZoneSystem()
    assert s.profiles_for_zone("nope") == ()


# ---- interpolate ----

def test_interpolate_at_t_zero():
    a = _make_profile("a", rt=1.0)
    b = _make_profile("b", rt=3.0)
    out = interpolate_profiles(a, b, 0.0)
    assert out.rt60_seconds == pytest.approx(1.0)


def test_interpolate_at_t_one():
    a = _make_profile("a", rt=1.0)
    b = _make_profile("b", rt=3.0)
    out = interpolate_profiles(a, b, 1.0)
    assert out.rt60_seconds == pytest.approx(3.0)


def test_interpolate_at_midpoint():
    a = _make_profile("a", rt=1.0)
    b = _make_profile("b", rt=3.0)
    out = interpolate_profiles(a, b, 0.5)
    assert out.rt60_seconds == pytest.approx(2.0)


def test_interpolate_t_out_of_range():
    a = _make_profile("a")
    b = _make_profile("b")
    with pytest.raises(ValueError):
        interpolate_profiles(a, b, 1.5)


def test_interpolate_at_boundary_uses_zone_defaults():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile("p_a", rt=1.0))
    s.register_profile(_make_profile("p_b", rt=3.0))
    s.set_zone_default("za", "p_a")
    s.set_zone_default("zb", "p_b")
    out = s.interpolate_at_boundary("za", "zb", 0.5)
    assert out.rt60_seconds == pytest.approx(2.0)


def test_interpolate_at_boundary_unknown_zone():
    s = ReverbZoneSystem()
    s.register_profile(_make_profile("p"))
    s.set_zone_default("za", "p")
    with pytest.raises(KeyError):
        s.interpolate_at_boundary("za", "zb", 0.5)


# ---- default catalog ----

def test_default_catalog_at_least_ten_profiles():
    s = ReverbZoneSystem()
    n = populate_default_profiles(s)
    assert n >= 10


def test_default_catalog_bastok_mines_long_rt60():
    s = ReverbZoneSystem()
    populate_default_profiles(s)
    p = s.get_profile("BASTOK_MINES_TUNNEL")
    assert p.rt60_seconds >= 2.0


def test_default_catalog_konschtat_almost_dry():
    s = ReverbZoneSystem()
    populate_default_profiles(s)
    p = s.get_profile("KONSCHTAT_OPEN_PLAIN")
    assert p.rt60_seconds <= 0.3
    assert p.wetness <= 0.2


def test_default_catalog_sandy_cathedral_huge():
    s = ReverbZoneSystem()
    populate_default_profiles(s)
    p = s.get_profile("SANDY_CATHEDRAL")
    assert p.rt60_seconds >= 4.0
    assert p.room_size_m3 >= 10000.0


def test_default_catalog_cids_workshop_damped():
    s = ReverbZoneSystem()
    populate_default_profiles(s)
    p = s.get_profile("CIDS_WORKSHOP")
    assert p.damping_freq_hz <= 4000.0
    assert p.rt60_seconds <= 0.5


def test_default_catalog_cids_workshop_volume_in_markets():
    s = ReverbZoneSystem()
    populate_default_profiles(s)
    # Inside the workshop volume
    p = s.profile_at("bastok_markets", (145.0, 2.0, -5.0))
    assert p.profile_id == "CIDS_WORKSHOP"


def test_default_catalog_markets_open_when_outside_workshop():
    s = ReverbZoneSystem()
    populate_default_profiles(s)
    p = s.profile_at("bastok_markets", (0.0, 0.0, 0.0))
    assert p.profile_id == "BASTOK_MARKETS_OPEN"
