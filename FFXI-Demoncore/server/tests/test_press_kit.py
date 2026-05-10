"""Tests for press_kit."""
from __future__ import annotations

import pytest

from server.press_kit import (
    AccessGrant,
    AssetFormat,
    AssetSpec,
    AssetVersion,
    PressAsset,
    PressKitBundle,
    PressKitSystem,
)


def _sys() -> PressKitSystem:
    return PressKitSystem()


def _seed(s: PressKitSystem) -> None:
    """Register all required assets at minimum."""
    s.register_asset(
        PressAsset.LOGO_PRIMARY,
        formats=(
            AssetFormat.PNG_4K, AssetFormat.SVG, AssetFormat.EPS,
        ),
        resolution_options=("4k", "8k"),
    )
    s.register_asset(
        PressAsset.KEY_ART_HERO,
        formats=(AssetFormat.PNG_8K, AssetFormat.PNG_4K),
    )
    s.register_asset(
        PressAsset.SCREENSHOT_GAMEPLAY,
        formats=(AssetFormat.PNG_4K,),
    )
    s.register_asset(
        PressAsset.FACTSHEET_PDF,
        formats=(AssetFormat.PDF,),
    )
    s.register_asset(
        PressAsset.CONTACT_CARD,
        formats=(AssetFormat.TXT, AssetFormat.JSON),
    )
    s.register_asset(
        PressAsset.EMBARGO_NOTICE,
        formats=(AssetFormat.TXT,),
    )


# ---- enums ----

def test_press_asset_count():
    assert len(list(PressAsset)) == 19


def test_press_asset_has_rating_bundle():
    assert (
        PressAsset.RATING_BUNDLE_ESRB_PEGI_USK_CERO
        in list(PressAsset)
    )


def test_press_asset_has_accessibility():
    assert (
        PressAsset.ACCESSIBILITY_STATEMENT
        in list(PressAsset)
    )


def test_asset_format_count():
    assert len(list(AssetFormat)) == 9


def test_asset_format_has_eps():
    assert AssetFormat.EPS in list(AssetFormat)


# ---- register_asset ----

def test_register_asset_returns_spec():
    s = _sys()
    spec = s.register_asset(
        PressAsset.LOGO_PRIMARY,
        formats=(AssetFormat.PNG_4K,),
    )
    assert isinstance(spec, AssetSpec)
    assert spec.kind == PressAsset.LOGO_PRIMARY


def test_register_asset_marks_required():
    s = _sys()
    spec = s.register_asset(
        PressAsset.LOGO_PRIMARY,
        formats=(AssetFormat.PNG_4K,),
    )
    assert spec.required is True


def test_register_asset_marks_non_required():
    s = _sys()
    spec = s.register_asset(
        PressAsset.LOGO_MARK_ONLY,
        formats=(AssetFormat.SVG,),
    )
    assert spec.required is False


def test_register_asset_empty_formats_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.register_asset(
            PressAsset.LOGO_PRIMARY,
            formats=(),
        )


def test_get_asset_spec_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.get_asset_spec(PressAsset.LOGO_PRIMARY)


def test_is_required_logo():
    s = _sys()
    assert s.is_required(PressAsset.LOGO_PRIMARY)


def test_is_required_not_logo_mark():
    s = _sys()
    assert not s.is_required(PressAsset.LOGO_MARK_ONLY)


def test_asset_count():
    s = _sys()
    _seed(s)
    assert s.asset_count() == 6


# ---- asset versions ----

def test_asset_versions_tracks_history():
    s = _sys()
    s.register_asset(
        PressAsset.LOGO_PRIMARY,
        formats=(AssetFormat.PNG_4K,),
        version="v1",
    )
    s.register_asset(
        PressAsset.LOGO_PRIMARY,
        formats=(AssetFormat.PNG_4K, AssetFormat.SVG),
        version="v2",
    )
    versions = s.asset_versions(PressAsset.LOGO_PRIMARY)
    assert len(versions) == 2
    assert versions[0].version == "v1"
    assert versions[1].version == "v2"


def test_asset_versions_unknown_empty():
    s = _sys()
    assert s.asset_versions(PressAsset.LOGO_PRIMARY) == ()


# ---- build kit ----

def test_build_kit_returns_bundle():
    s = _sys()
    b = s.build_kit(
        title="March Reveal",
        embargo_until_iso="2026-03-15T17:00:00Z",
        assets=[PressAsset.LOGO_PRIMARY],
    )
    assert isinstance(b, PressKitBundle)
    assert b.title == "March Reveal"


def test_build_kit_empty_title_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.build_kit(
            title="",
            embargo_until_iso="2026-03-15T17:00:00Z",
            assets=[],
        )


def test_build_kit_empty_embargo_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.build_kit(
            title="x",
            embargo_until_iso="",
            assets=[],
        )


def test_build_kit_counter_increments():
    s = _sys()
    b1 = s.build_kit(
        "k1", "2026-03-15T17:00:00Z", [],
    )
    b2 = s.build_kit(
        "k2", "2026-03-15T17:00:00Z", [],
    )
    assert b1.kit_id != b2.kit_id
    assert s.kit_count() == 2


def test_get_kit_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.get_kit("ghost")


# ---- validate kit ----

def test_validate_complete_kit_clean():
    s = _sys()
    _seed(s)
    b = s.build_kit(
        title="Reveal",
        embargo_until_iso="2026-03-15T17:00:00Z",
        assets=[
            PressAsset.LOGO_PRIMARY,
            PressAsset.KEY_ART_HERO,
            PressAsset.SCREENSHOT_GAMEPLAY,
            PressAsset.FACTSHEET_PDF,
            PressAsset.CONTACT_CARD,
            PressAsset.EMBARGO_NOTICE,
        ],
    )
    assert s.validate_kit(b.kit_id) == ()


def test_validate_missing_logo_flagged():
    s = _sys()
    _seed(s)
    b = s.build_kit(
        title="x",
        embargo_until_iso="2026-03-15T17:00:00Z",
        assets=[
            PressAsset.KEY_ART_HERO,
            PressAsset.SCREENSHOT_GAMEPLAY,
            PressAsset.FACTSHEET_PDF,
            PressAsset.CONTACT_CARD,
            PressAsset.EMBARGO_NOTICE,
        ],
    )
    issues = s.validate_kit(b.kit_id)
    assert any("logo_primary" in i for i in issues)


def test_validate_unregistered_asset_flagged():
    s = _sys()
    _seed(s)
    b = s.build_kit(
        title="x",
        embargo_until_iso="2026-03-15T17:00:00Z",
        assets=[
            PressAsset.LOGO_PRIMARY,
            PressAsset.KEY_ART_HERO,
            PressAsset.SCREENSHOT_GAMEPLAY,
            PressAsset.FACTSHEET_PDF,
            PressAsset.CONTACT_CARD,
            PressAsset.EMBARGO_NOTICE,
            PressAsset.BIO_SHEET,  # not registered
        ],
    )
    issues = s.validate_kit(b.kit_id)
    assert any("bio_sheet" in i for i in issues)


def test_validate_unknown_kit_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.validate_kit("ghost")


# ---- access grant ----

def test_grant_access_returns_grant():
    s = _sys()
    _seed(s)
    b = s.build_kit(
        "x", "2026-03-15T17:00:00Z", [],
    )
    g = s.grant_access(
        b.kit_id,
        "kotaku_reviewer",
        allowed_assets=[PressAsset.LOGO_PRIMARY],
    )
    assert isinstance(g, AccessGrant)
    assert g.journalist_id == "kotaku_reviewer"


def test_grant_access_appends_recipient():
    s = _sys()
    _seed(s)
    b = s.build_kit(
        "x", "2026-03-15T17:00:00Z", [],
    )
    s.grant_access(
        b.kit_id, "kotaku_reviewer", allowed_assets=[],
    )
    updated = s.get_kit(b.kit_id)
    assert "kotaku_reviewer" in updated.recipient_list


def test_grant_access_empty_journalist_raises():
    s = _sys()
    b = s.build_kit(
        "x", "2026-03-15T17:00:00Z", [],
    )
    with pytest.raises(ValueError):
        s.grant_access(b.kit_id, "", allowed_assets=[])


def test_grant_access_unknown_kit_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.grant_access(
            "ghost", "j", allowed_assets=[],
        )


def test_get_grant_unknown_raises():
    s = _sys()
    b = s.build_kit("x", "2026-03-15T17:00:00Z", [])
    with pytest.raises(KeyError):
        s.get_grant(b.kit_id, "ghost")


# ---- tokens ----

def test_generate_token_returns_token():
    s = _sys()
    b = s.build_kit("x", "2026-03-15T17:00:00Z", [])
    s.grant_access(b.kit_id, "j", allowed_assets=[])
    tok = s.generate_download_token(b.kit_id, "j")
    assert tok.startswith("dl_")


def test_generate_token_requires_grant():
    s = _sys()
    b = s.build_kit("x", "2026-03-15T17:00:00Z", [])
    with pytest.raises(ValueError):
        s.generate_download_token(b.kit_id, "ungranted")


def test_generate_token_unknown_kit_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.generate_download_token("ghost", "j")


def test_token_for_returns_token():
    s = _sys()
    b = s.build_kit("x", "2026-03-15T17:00:00Z", [])
    s.grant_access(b.kit_id, "j", allowed_assets=[])
    tok = s.generate_download_token(b.kit_id, "j")
    assert s.token_for(b.kit_id, "j") == tok


def test_token_for_unknown_recipient_raises():
    s = _sys()
    b = s.build_kit("x", "2026-03-15T17:00:00Z", [])
    with pytest.raises(KeyError):
        s.token_for(b.kit_id, "ghost")


# ---- embargo ----

def test_embargo_active_before():
    s = _sys()
    b = s.build_kit(
        "x", "2026-03-15T17:00:00Z", [],
    )
    assert s.is_embargo_active(
        b.kit_id, "2026-03-01T00:00:00Z",
    )


def test_embargo_inactive_after():
    s = _sys()
    b = s.build_kit(
        "x", "2026-03-15T17:00:00Z", [],
    )
    assert not s.is_embargo_active(
        b.kit_id, "2026-04-01T00:00:00Z",
    )


def test_log_violation_increments():
    s = _sys()
    b = s.build_kit(
        "x", "2026-03-15T17:00:00Z", [],
    )
    s.log_embargo_violation(
        b.kit_id, "indieblog", "2026-03-10T00:00:00Z",
    )
    s.log_embargo_violation(
        b.kit_id, "leakers", "2026-03-11T00:00:00Z",
    )
    assert s.violation_count(b.kit_id) == 2


# ---- summary ----

def test_kit_summary_has_keys():
    s = _sys()
    b = s.build_kit(
        "March Reveal",
        "2026-03-15T17:00:00Z",
        [PressAsset.LOGO_PRIMARY],
    )
    summ = s.kit_summary(b.kit_id)
    for k in (
        "kit_id", "title", "embargo_until_iso",
        "asset_count", "recipients", "grants",
        "tokens_issued", "violations", "expiry_iso",
    ):
        assert k in summ


def test_kit_summary_counts():
    s = _sys()
    b = s.build_kit(
        "x", "2026-03-15T17:00:00Z",
        [PressAsset.LOGO_PRIMARY, PressAsset.KEY_ART_HERO],
    )
    s.grant_access(b.kit_id, "j1", allowed_assets=[])
    s.grant_access(b.kit_id, "j2", allowed_assets=[])
    s.generate_download_token(b.kit_id, "j1")
    summ = s.kit_summary(b.kit_id)
    assert summ["asset_count"] == 2
    assert len(summ["grants"]) == 2
    assert summ["tokens_issued"] == 1


def test_kit_summary_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.kit_summary("ghost")
