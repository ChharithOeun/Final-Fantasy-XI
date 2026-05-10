"""Tests for zone_lighting_atlas."""
from __future__ import annotations

import pytest

from server.zone_lighting_atlas import (
    DISTINCTIVE_PROFILES,
    LightingAtlas,
    LightingProfile,
)


# ---- distinctive profiles ----

def test_twelve_distinctive_profiles():
    assert len(DISTINCTIVE_PROFILES) == 12


def test_distinctive_includes_bastok_markets():
    assert "bastok_markets" in DISTINCTIVE_PROFILES


def test_distinctive_includes_pashhow():
    assert "pashhow_marshlands" in DISTINCTIVE_PROFILES


def test_distinctive_includes_crawlers_nest():
    assert "crawlers_nest" in DISTINCTIVE_PROFILES


def test_distinctive_includes_davoi():
    assert "davoi" in DISTINCTIVE_PROFILES


def test_distinctive_includes_eldieme_substitute():
    # Eldieme isn't in zone_atlas; beadeaux is the canonical
    # cold-blue moonlight zone there.
    assert "beadeaux" in DISTINCTIVE_PROFILES


def test_distinctive_includes_konschtat_substitute():
    # Konschtat substitute is north_gustaberg.
    assert "north_gustaberg" in DISTINCTIVE_PROFILES


# ---- LightingAtlas constructor / preload ----

def test_atlas_preloads_twelve_distinctive():
    atlas = LightingAtlas()
    assert len(atlas.all_profiles()) == 12


def test_atlas_lookup_distinctive():
    atlas = LightingAtlas()
    p = atlas.lookup("bastok_markets")
    assert p.zone_id == "bastok_markets"
    assert p.recommended_film_lut == "vision3_250d"


def test_atlas_lookup_unknown_raises():
    atlas = LightingAtlas()
    with pytest.raises(KeyError):
        atlas.lookup("never_seen_zone")


def test_has_profile_true_for_distinctive():
    atlas = LightingAtlas()
    assert atlas.has_profile("davoi")


def test_has_profile_false_for_unknown():
    atlas = LightingAtlas()
    assert not atlas.has_profile("never_seen")


# ---- register_profile validation ----

def _profile(
    zid: str = "test_zone",
    fill: float = 0.5,
    fog_d: float = 0.1,
    god: float = 0.5,
    atm: float = 100.0,
    fog_rgb: tuple[int, int, int] = (100, 100, 100),
) -> LightingProfile:
    return LightingProfile(
        zone_id=zid,
        mood_descriptor="test",
        key_light_kelvin=5500,
        key_light_intensity_lux=10000.0,
        fill_ratio=fill,
        back_light_kelvin=7000,
        sky_dome_uri="sky/test.hdr",
        hdri_uri="hdri/test.exr",
        sun_angle_at_noon_deg=60.0,
        fog_density=fog_d,
        fog_color_rgb=fog_rgb,
        god_ray_strength=god,
        atmospheric_perspective_meters=atm,
        recommended_film_lut="demoncore_standard",
        recommended_camera_profile="arri_alexa_35",
        recommended_lens_profile="cooke_s4_50mm",
    )


def test_register_profile_adds_new():
    atlas = LightingAtlas()
    atlas.register_profile(_profile("new_zone"))
    assert atlas.has_profile("new_zone")


def test_register_profile_empty_zone_raises():
    atlas = LightingAtlas()
    with pytest.raises(ValueError):
        atlas.register_profile(_profile(zid=""))


def test_register_profile_bad_fill_ratio_raises():
    atlas = LightingAtlas()
    with pytest.raises(ValueError):
        atlas.register_profile(_profile(fill=1.5))


def test_register_profile_bad_fog_density_raises():
    atlas = LightingAtlas()
    with pytest.raises(ValueError):
        atlas.register_profile(_profile(fog_d=-0.1))


def test_register_profile_bad_god_ray_raises():
    atlas = LightingAtlas()
    with pytest.raises(ValueError):
        atlas.register_profile(_profile(god=2.0))


def test_register_profile_bad_atm_perspective_raises():
    atlas = LightingAtlas()
    with pytest.raises(ValueError):
        atlas.register_profile(_profile(atm=-1.0))


def test_register_profile_bad_fog_color_raises():
    atlas = LightingAtlas()
    with pytest.raises(ValueError):
        atlas.register_profile(_profile(fog_rgb=(300, 0, 0)))


# ---- profile filters ----

def test_profiles_with_lut_returns_matches():
    atlas = LightingAtlas()
    result = atlas.profiles_with_lut("day_for_night")
    ids = {p.zone_id for p in result}
    # Crawlers Nest + Beadeaux both use day_for_night.
    assert "crawlers_nest" in ids
    assert "beadeaux" in ids


def test_profiles_with_lut_empty_for_unknown():
    atlas = LightingAtlas()
    assert atlas.profiles_with_lut("does_not_exist") == ()


def test_profiles_with_camera_returns_matches():
    atlas = LightingAtlas()
    result = atlas.profiles_with_camera("arri_alexa_35")
    assert len(result) >= 4


# ---- distinctive_profiles ----

def test_distinctive_profiles_returns_tuple_of_twelve():
    atlas = LightingAtlas()
    assert len(atlas.distinctive_profiles()) == 12


# ---- derive_for ----

def test_derive_for_returns_explicit_when_present():
    atlas = LightingAtlas()
    p = atlas.derive_for("bastok_markets", "nation_capital")
    assert p.zone_id == "bastok_markets"


def test_derive_for_returns_archetype_default_when_missing():
    atlas = LightingAtlas()
    p = atlas.derive_for("totally_new_zone", "open_field")
    assert p.zone_id == "totally_new_zone"
    # The base archetype default is north_gustaberg style.
    assert p.recommended_film_lut == "vision3_250d"


def test_derive_for_unknown_archetype_raises():
    atlas = LightingAtlas()
    with pytest.raises(KeyError):
        atlas.derive_for("z", "not_an_archetype")


def test_derive_for_dungeon_archetype_uses_amber():
    atlas = LightingAtlas()
    p = atlas.derive_for("new_dungeon", "dungeon_dark")
    # crawlers_nest base -> day_for_night LUT.
    assert p.recommended_film_lut == "day_for_night"


def test_derive_for_endgame_archetype_uses_aether():
    atlas = LightingAtlas()
    p = atlas.derive_for("new_endgame", "endgame_instance")
    assert p.fog_color_rgb == (200, 220, 255)


# ---- profile fields ----

def test_lighting_profile_dataclass_frozen():
    p = _profile()
    with pytest.raises(Exception):
        p.fill_ratio = 0.0  # type: ignore


def test_distinctive_profile_film_luts_are_canonical():
    atlas = LightingAtlas()
    luts = {p.recommended_film_lut
            for p in atlas.distinctive_profiles()}
    expected = {
        "vision3_500t", "vision3_250d", "eterna",
        "cinestyle", "demoncore_standard", "bleach_bypass",
        "day_for_night",
    }
    assert luts <= expected | {
        "vision3_500t", "vision3_250d", "eterna",
        "cinestyle", "demoncore_standard", "bleach_bypass",
        "day_for_night",
    }
    # All LUTs should at least be from the canonical set.
    for lut in luts:
        assert lut in expected


def test_bastok_mines_smelter_warm_kelvin_low():
    atlas = LightingAtlas()
    p = atlas.lookup("bastok_mines")
    assert p.key_light_kelvin <= 3000  # warm tungsten range


def test_beadeaux_cold_blue_kelvin_high():
    atlas = LightingAtlas()
    p = atlas.lookup("beadeaux")
    assert p.key_light_kelvin >= 7000  # cold daylight range


def test_pashhow_high_fog_density():
    atlas = LightingAtlas()
    p = atlas.lookup("pashhow_marshlands")
    assert p.fog_density >= 0.30  # overcast / marshy


def test_all_profiles_returns_after_register():
    atlas = LightingAtlas()
    atlas.register_profile(_profile("custom_zone"))
    ids = {p.zone_id for p in atlas.all_profiles()}
    assert "custom_zone" in ids
