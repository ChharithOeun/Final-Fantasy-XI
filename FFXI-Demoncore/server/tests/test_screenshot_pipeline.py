"""Tests for screenshot_pipeline."""
from __future__ import annotations

import pytest

from server.screenshot_pipeline import (
    Archetype,
    CameraSettings,
    CapturePass,
    QualityRating,
    Screenshot,
    ScreenshotFormat,
    ScreenshotPipeline,
)


def _sys() -> ScreenshotPipeline:
    return ScreenshotPipeline()


# ---- enums ----

def test_capture_pass_count():
    assert len(list(CapturePass)) == 6


def test_capture_pass_has_marketing_beauty():
    assert (
        CapturePass.MARKETING_BEAUTY in list(CapturePass)
    )


def test_capture_pass_has_environment_detail():
    assert (
        CapturePass.ENVIRONMENT_DETAIL in list(CapturePass)
    )


def test_archetype_count():
    assert len(list(Archetype)) == 3


def test_screenshot_format_has_exr():
    assert ScreenshotFormat.EXR_HDR in list(ScreenshotFormat)


# ---- register pass ----

def test_register_pass_returns_params():
    s = _sys()
    p = s.register_pass(
        CapturePass.HERO_ZONE_SET, weather="rain",
    )
    assert p["weather"] == "rain"


def test_register_pass_keeps_defaults():
    s = _sys()
    p = s.register_pass(CapturePass.HERO_ZONE_SET)
    assert p["format"] == ScreenshotFormat.PNG_8K


def test_pass_count():
    s = _sys()
    s.register_pass(CapturePass.HERO_ZONE_SET)
    s.register_pass(CapturePass.COMBAT_MOMENTS)
    assert s.pass_count() == 2


def test_pass_params_unregistered_default():
    s = _sys()
    p = s.pass_params(CapturePass.MARKETING_BEAUTY)
    assert "format" in p


# ---- capture ----

def test_capture_returns_id():
    s = _sys()
    sid = s.capture(
        CapturePass.HERO_ZONE_SET, "bastok_markets",
    )
    assert sid.startswith("ss_")


def test_capture_empty_zone_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.capture(CapturePass.HERO_ZONE_SET, "")


def test_capture_returns_unique_ids():
    s = _sys()
    sid1 = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    sid2 = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    assert sid1 != sid2


def test_capture_count():
    s = _sys()
    s.capture(CapturePass.HERO_ZONE_SET, "z1")
    s.capture(CapturePass.HERO_ZONE_SET, "z2")
    assert s.count() == 2


def test_count_for_pass():
    s = _sys()
    s.capture(CapturePass.HERO_ZONE_SET, "z1")
    s.capture(CapturePass.COMBAT_MOMENTS, "z2")
    assert s.count_for_pass(CapturePass.HERO_ZONE_SET) == 1
    assert s.count_for_pass(CapturePass.COMBAT_MOMENTS) == 1


def test_get_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.get("ghost")


def test_capture_stores_camera_settings():
    s = _sys()
    sid = s.capture(
        CapturePass.HERO_ZONE_SET,
        "z1",
        focal_length_mm=85.0,
        t_stop=1.4,
    )
    shot = s.get(sid)
    assert shot.camera_settings.focal_length_mm == 85.0
    assert shot.camera_settings.t_stop == 1.4


def test_capture_stores_format():
    s = _sys()
    sid = s.capture(
        CapturePass.HERO_ZONE_SET,
        "z1",
        format_=ScreenshotFormat.JPG_WEB,
    )
    assert s.get(sid).format == ScreenshotFormat.JPG_WEB


# ---- auto tag ----

def test_auto_tag_includes_zone():
    s = _sys()
    sid = s.capture(
        CapturePass.HERO_ZONE_SET, "bastok_markets",
    )
    tags = s.auto_tag(sid)
    assert "zone:bastok_markets" in tags


def test_auto_tag_includes_archetype():
    s = _sys()
    sid = s.capture(
        CapturePass.HERO_ZONE_SET, "z1",
        archetype=Archetype.VILLAIN,
    )
    tags = s.auto_tag(sid)
    assert "archetype:villain" in tags


def test_auto_tag_includes_weather():
    s = _sys()
    sid = s.capture(
        CapturePass.HERO_ZONE_SET, "z1", weather="rain",
    )
    assert "weather:rain" in s.auto_tag(sid)


def test_auto_tag_time_of_day_evening():
    s = _sys()
    sid = s.capture(
        CapturePass.HERO_ZONE_SET, "z1", hour=18.0,
    )
    assert "tod:evening" in s.auto_tag(sid)


def test_auto_tag_time_of_day_night():
    s = _sys()
    sid = s.capture(
        CapturePass.HERO_ZONE_SET, "z1", hour=2.0,
    )
    assert "tod:night" in s.auto_tag(sid)


def test_auto_tag_has_combat():
    s = _sys()
    sid = s.capture(
        CapturePass.COMBAT_MOMENTS, "z1", has_combat=True,
    )
    assert "has_combat" in s.auto_tag(sid)


def test_auto_tag_has_dialogue():
    s = _sys()
    sid = s.capture(
        CapturePass.CHARACTER_PORTRAITS, "z1",
        has_dialogue=True,
    )
    assert "has_dialogue" in s.auto_tag(sid)


def test_auto_tag_races():
    s = _sys()
    sid = s.capture(
        CapturePass.CHARACTER_PORTRAITS,
        "z1", races=["hume", "elvaan"],
    )
    tags = s.auto_tag(sid)
    assert "race:hume" in tags
    assert "race:elvaan" in tags


def test_add_tag():
    s = _sys()
    sid = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    tags = s.add_tag(sid, "custom_tag")
    assert "custom_tag" in tags


def test_add_empty_tag_raises():
    s = _sys()
    sid = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    with pytest.raises(ValueError):
        s.add_tag(sid, "")


def test_search_by_tag():
    s = _sys()
    s.capture(CapturePass.HERO_ZONE_SET, "bastok_markets")
    s.capture(CapturePass.HERO_ZONE_SET, "sandoria_castle")
    results = s.search_by_tag("zone:bastok_markets")
    assert len(results) == 1


# ---- rate quality ----

def test_rate_quality_returns_rating():
    s = _sys()
    sid = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    r = s.rate_quality(sid)
    assert isinstance(r, QualityRating)
    assert 0.0 <= r.auto_score <= 5.0


def test_rate_quality_perfect():
    s = _sys()
    sid = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    r = s.rate_quality(
        sid, composition=1.0, face=1.0, exposure=1.0,
    )
    assert r.auto_score == 5.0


def test_rate_quality_persists_rating_on_shot():
    s = _sys()
    sid = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    s.rate_quality(
        sid, composition=1.0, face=1.0, exposure=1.0,
    )
    shot = s.get(sid)
    assert shot.rating == 5.0


def test_rate_quality_out_of_range_raises():
    s = _sys()
    sid = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    with pytest.raises(ValueError):
        s.rate_quality(sid, composition=1.5)


def test_rating_for_unrated_none():
    s = _sys()
    sid = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    assert s.rating_for(sid) is None


# ---- curated set ----

def test_curated_set_returns_top_n():
    s = _sys()
    for i in range(20):
        sid = s.capture(
            CapturePass.MARKETING_BEAUTY, f"zone_{i}",
        )
        # Higher quality for higher i.
        v = min(1.0, 0.1 + i * 0.05)
        s.rate_quality(
            sid, composition=v, face=v, exposure=v,
        )
    top = s.curated_set_for(
        CapturePass.MARKETING_BEAUTY, count=12,
    )
    assert len(top) == 12


def test_curated_set_sorted_by_rating():
    s = _sys()
    sid_low = s.capture(
        CapturePass.MARKETING_BEAUTY, "z1",
    )
    s.rate_quality(
        sid_low, composition=0.1, face=0.1, exposure=0.1,
    )
    sid_high = s.capture(
        CapturePass.MARKETING_BEAUTY, "z2",
    )
    s.rate_quality(
        sid_high, composition=1.0, face=1.0, exposure=1.0,
    )
    top = s.curated_set_for(
        CapturePass.MARKETING_BEAUTY, count=2,
    )
    assert top[0] == sid_high


def test_curated_set_zero_count_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.curated_set_for(
            CapturePass.MARKETING_BEAUTY, count=0,
        )


def test_curated_set_empty_pass():
    s = _sys()
    assert s.curated_set_for(
        CapturePass.MARKETING_BEAUTY, count=12,
    ) == ()


# ---- annotate ----

def test_annotate_sets_notes():
    s = _sys()
    sid = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    new = s.annotate(sid, "Hero shot — Eero golden hour")
    assert new.curator_notes.startswith("Hero shot")


# ---- bulk export ----

def test_bulk_export_returns_paths():
    s = _sys()
    sid1 = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    sid2 = s.capture(CapturePass.HERO_ZONE_SET, "z2")
    paths = s.bulk_export(
        [sid1, sid2], ScreenshotFormat.PNG_8K,
    )
    assert len(paths) == 2
    assert all(p.endswith(".png") for p in paths)


def test_bulk_export_exr_extension():
    s = _sys()
    sid = s.capture(CapturePass.HERO_ZONE_SET, "z1")
    paths = s.bulk_export(
        [sid], ScreenshotFormat.EXR_HDR,
    )
    assert paths[0].endswith(".exr")
