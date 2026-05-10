"""Tests for release_manifest."""
from __future__ import annotations

import pytest

from server.release_manifest import (
    AgeRatingBoard,
    DemoBuildConfig,
    DrmKind,
    FeatureFlag,
    PlatformSpec,
    ReleaseBuild,
    ReleaseManifestSystem,
    ReleasePlatform,
    TechRequirements,
    Watermark,
)


def _sys() -> ReleaseManifestSystem:
    return ReleaseManifestSystem()


# ---- enums ----

def test_release_platform_count():
    assert len(list(ReleasePlatform)) == 14


def test_release_platform_has_switch_2():
    assert (
        ReleasePlatform.NINTENDO_ESHOP_SWITCH_2
        in list(ReleasePlatform)
    )


def test_release_platform_has_web():
    assert ReleasePlatform.WEB_BROWSER in list(
        ReleasePlatform,
    )


def test_release_platform_has_streaming_luna():
    assert ReleasePlatform.STREAMING_LUNA in list(
        ReleasePlatform,
    )


def test_age_rating_board_count():
    assert len(list(AgeRatingBoard)) == 6


def test_drm_kind_has_denuvo():
    assert DrmKind.DENUVO in list(DrmKind)


def test_watermark_count():
    assert len(list(Watermark)) == 4


def test_feature_flag_count():
    assert len(list(FeatureFlag)) == 4


# ---- register platform ----

def test_register_platform_returns_spec():
    s = _sys()
    spec = s.register_platform(
        ReleasePlatform.STEAM,
        cpu="i7-10700",
        ram_gb=16,
        drm=DrmKind.STEAM_DRM,
    )
    assert isinstance(spec, PlatformSpec)
    assert spec.technical_requirements.cpu == "i7-10700"
    assert spec.drm == DrmKind.STEAM_DRM


def test_register_platform_default_board_for_switch():
    s = _sys()
    spec = s.register_platform(
        ReleasePlatform.NINTENDO_ESHOP_SWITCH,
    )
    assert spec.age_rating_board == AgeRatingBoard.CERO


def test_register_platform_default_board_for_steam():
    s = _sys()
    spec = s.register_platform(ReleasePlatform.STEAM)
    assert spec.age_rating_board == AgeRatingBoard.ESRB


def test_register_platform_explicit_board():
    s = _sys()
    spec = s.register_platform(
        ReleasePlatform.STEAM,
        age_rating_board=AgeRatingBoard.PEGI,
    )
    assert spec.age_rating_board == AgeRatingBoard.PEGI


def test_get_spec_auto_registers():
    s = _sys()
    spec = s.get_spec(ReleasePlatform.STEAM)
    assert spec.platform == ReleasePlatform.STEAM


def test_spec_count():
    s = _sys()
    s.register_platform(ReleasePlatform.STEAM)
    s.register_platform(ReleasePlatform.GOG)
    assert s.spec_count() == 2


# ---- region locks / languages ----

def test_platforms_for_region_unrestricted():
    s = _sys()
    plats = s.platforms_for_region("US")
    assert len(plats) == 14


def test_platforms_for_region_restricted():
    s = _sys()
    s.register_platform(
        ReleasePlatform.STEAM, region_lock=["KP"],
    )
    plats = s.platforms_for_region("KP")
    assert ReleasePlatform.STEAM not in plats


def test_languages_for_platform_default():
    s = _sys()
    langs = s.languages_for_platform(
        ReleasePlatform.STEAM,
    )
    assert "en-US" in langs


def test_languages_for_platform_custom():
    s = _sys()
    s.register_platform(
        ReleasePlatform.STEAM,
        language_support=["en-US", "ja-JP", "fr-FR"],
    )
    langs = s.languages_for_platform(
        ReleasePlatform.STEAM,
    )
    assert "ja-JP" in langs
    assert "fr-FR" in langs


# ---- age rating validation ----

def test_validate_age_rating_esrb_clean():
    s = _sys()
    issues = s.validate_age_rating(
        ReleasePlatform.STEAM,
        ["violence_stylized", "language_mild"],
    )
    assert issues == ()


def test_validate_age_rating_esrb_unknown_descriptor():
    s = _sys()
    issues = s.validate_age_rating(
        ReleasePlatform.STEAM,
        ["violence_stylized", "made_up_descriptor"],
    )
    assert any("made_up_descriptor" in i for i in issues)


def test_validate_age_rating_cero_for_switch():
    s = _sys()
    issues = s.validate_age_rating(
        ReleasePlatform.NINTENDO_ESHOP_SWITCH,
        ["violence", "gambling"],
    )
    assert issues == ()


def test_board_vocabulary_pegi():
    s = _sys()
    v = s.board_vocabulary(AgeRatingBoard.PEGI)
    assert "violence_low" in v
    assert "online_interactions" in v


def test_board_vocabulary_usk():
    s = _sys()
    v = s.board_vocabulary(AgeRatingBoard.USK)
    assert "gewalt_stilisiert" in v


# ---- build_release ----

def test_build_release_returns_build():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM,
        "demo_manifest_2026_03",
    )
    assert isinstance(r, ReleaseBuild)
    assert r.platform == ReleasePlatform.STEAM


def test_build_release_empty_manifest_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.build_release(ReleasePlatform.STEAM, "")


def test_build_release_negative_time_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.build_release(
            ReleasePlatform.STEAM,
            "demo_manifest",
            time_limit_minutes=-1,
        )


def test_build_release_time_limit():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM,
        "demo_manifest",
        time_limit_minutes=30,
    )
    assert r.config.time_limit_minutes == 30


def test_build_release_feature_flags():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM,
        "demo_manifest",
        feature_flags=[
            FeatureFlag.MULTIPLAYER,
            FeatureFlag.PHOTO_MODE,
        ],
    )
    assert FeatureFlag.MULTIPLAYER in r.config.feature_flags
    assert FeatureFlag.PHOTO_MODE in r.config.feature_flags


def test_build_release_watermark_press():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM,
        "demo_manifest",
        watermark=Watermark.PRESS,
    )
    assert r.config.watermark == Watermark.PRESS


def test_build_release_submission_blob_has_keys():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM,
        "demo_manifest",
        content_descriptors=["violence_stylized"],
    )
    for k in (
        "platform", "manifest_id", "board",
        "descriptors", "drm", "watermark",
        "checksum", "feature_flags",
    ):
        assert k in r.submission_blob


def test_build_release_counter_increments():
    s = _sys()
    r1 = s.build_release(
        ReleasePlatform.STEAM, "m1",
    )
    r2 = s.build_release(
        ReleasePlatform.STEAM, "m2",
    )
    assert r1.build_id != r2.build_id
    assert s.build_count() == 2


def test_get_build_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.get_build("ghost")


# ---- signing ----

def test_sign_build_sets_key():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM, "demo_manifest",
    )
    signed = s.sign_build(r.build_id, "key_2026_release")
    assert signed.config.signing_key_id == "key_2026_release"
    assert signed.config.signed_by


def test_sign_build_marks_signed():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM, "demo_manifest",
    )
    assert not s.is_signed(r.build_id)
    s.sign_build(r.build_id, "key_2026")
    assert s.is_signed(r.build_id)


def test_sign_build_empty_key_raises():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM, "demo_manifest",
    )
    with pytest.raises(ValueError):
        s.sign_build(r.build_id, "")


def test_sign_build_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.sign_build("ghost", "key")


# ---- summary ----

def test_release_summary_has_keys():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM,
        "demo_manifest",
        feature_flags=[FeatureFlag.PHOTO_MODE],
        watermark=Watermark.PRESS,
    )
    summ = s.release_summary(r.build_id)
    for k in (
        "build_id", "platform", "manifest_id",
        "time_limit_minutes", "watermark", "feature_flags",
        "drm", "price_usd", "board", "descriptor_count",
        "signed", "signing_key_id", "languages",
    ):
        assert k in summ


def test_release_summary_signed_false_then_true():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM, "demo_manifest",
    )
    assert s.release_summary(r.build_id)["signed"] is False
    s.sign_build(r.build_id, "key_x")
    assert s.release_summary(r.build_id)["signed"] is True


def test_release_summary_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.release_summary("ghost")


# ---- dataclass identity ----

def test_tech_requirements_frozen():
    tr = TechRequirements(
        cpu="x", gpu="y", ram_gb=8, storage_gb=10,
    )
    with pytest.raises(dataclasses_FrozenInstanceError := __import__(
        "dataclasses",
    ).FrozenInstanceError):
        tr.cpu = "z"


def test_demo_build_config_dataclass_field():
    s = _sys()
    r = s.build_release(
        ReleasePlatform.STEAM, "demo_manifest",
    )
    assert isinstance(r.config, DemoBuildConfig)
