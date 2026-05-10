"""Tests for social_clip_generator."""
from __future__ import annotations

import pytest

from server.social_clip_generator import (
    CaptionLine,
    ClipBuildPlan,
    CropBox,
    Platform,
    PlatformSpec,
    SocialClipSystem,
)


def _sys() -> SocialClipSystem:
    return SocialClipSystem()


# ---- enums ----

def test_platform_count():
    assert len(list(Platform)) == 8


def test_platform_has_tiktok():
    assert Platform.TIKTOK in list(Platform)


def test_platform_has_linkedin():
    assert Platform.LINKEDIN in list(Platform)


def test_platform_has_bluesky():
    assert Platform.BLUESKY in list(Platform)


def test_platform_has_mastodon():
    assert Platform.MASTODON in list(Platform)


# ---- spec registration ----

def test_register_default_tiktok_spec():
    s = _sys()
    spec = s.register_platform_spec(Platform.TIKTOK)
    assert isinstance(spec, PlatformSpec)
    assert spec.aspect_ratio == "9:16"
    assert spec.music_required is True


def test_register_default_linkedin_spec():
    s = _sys()
    spec = s.register_platform_spec(Platform.LINKEDIN)
    assert spec.aspect_ratio == "16:9"
    assert spec.music_required is False


def test_register_override_aspect():
    s = _sys()
    spec = s.register_platform_spec(
        Platform.TWITTER, aspect_ratio="9:16",
    )
    assert spec.aspect_ratio == "9:16"


def test_get_spec_auto_registers():
    s = _sys()
    spec = s.get_spec(Platform.TIKTOK)
    assert spec.platform == Platform.TIKTOK


def test_spec_count():
    s = _sys()
    s.register_platform_spec(Platform.TIKTOK)
    s.register_platform_spec(Platform.LINKEDIN)
    assert s.spec_count() == 2


def test_recommended_duration_tiktok():
    s = _sys()
    assert s.recommended_duration_for(Platform.TIKTOK) == 30


def test_recommended_duration_linkedin():
    s = _sys()
    assert s.recommended_duration_for(Platform.LINKEDIN) == 60


def test_recommended_duration_twitter():
    s = _sys()
    assert s.recommended_duration_for(Platform.TWITTER) == 45


# ---- auto crop ----

def test_auto_crop_same_aspect():
    s = _sys()
    box = s.auto_crop_box("16:9", "16:9", (0.5, 0.5))
    assert box.w == 1.0
    assert box.h == 1.0


def test_auto_crop_16_9_to_9_16_horizontal_crop():
    s = _sys()
    box = s.auto_crop_box("16:9", "9:16", (0.5, 0.5))
    # Source taller in target -> crop vertically, not the
    # other direction. Actually 16:9 wider than 9:16 means
    # source aspect (16/9 ≈ 1.78) > target aspect
    # (9/16 ≈ 0.56). So crop horizontally.
    assert box.w < 1.0
    assert box.h == 1.0


def test_auto_crop_9_16_to_16_9_vertical_crop():
    s = _sys()
    box = s.auto_crop_box("9:16", "16:9", (0.5, 0.5))
    assert box.h < 1.0
    assert box.w == 1.0


def test_auto_crop_focus_left():
    s = _sys()
    box = s.auto_crop_box("16:9", "9:16", (0.1, 0.5))
    # Focus is far left; x should be 0 (clamped).
    assert box.x == 0.0


def test_auto_crop_focus_right():
    s = _sys()
    box = s.auto_crop_box("16:9", "9:16", (0.95, 0.5))
    # Crop should clamp to right edge.
    assert box.x + box.w == pytest.approx(1.0, abs=1e-3)


def test_auto_crop_invalid_focus_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.auto_crop_box("16:9", "9:16", (1.5, 0.5))


def test_auto_crop_invalid_aspect_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.auto_crop_box("nope", "9:16", (0.5, 0.5))


# ---- captions ----

def test_push_caption_grows_track():
    s = _sys()
    n = s.push_caption(
        "rep1",
        CaptionLine(
            start_ms=0, end_ms=1000,
            text="Hello", style="default",
        ),
    )
    assert n == 1


def test_caption_track_empty():
    s = _sys()
    assert s.caption_track("nope") == ()


def test_caption_track_ordered():
    s = _sys()
    s.push_caption(
        "r1",
        CaptionLine(
            start_ms=0, end_ms=1000,
            text="A", style="d",
        ),
    )
    s.push_caption(
        "r1",
        CaptionLine(
            start_ms=1000, end_ms=2000,
            text="B", style="d",
        ),
    )
    track = s.caption_track("r1")
    assert track[0].text == "A"
    assert track[1].text == "B"


def test_push_caption_empty_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.push_caption(
            "",
            CaptionLine(
                start_ms=0, end_ms=1,
                text="x", style="d",
            ),
        )


# ---- generate_clip ----

def test_generate_clip_returns_plan():
    s = _sys()
    p = s.generate_clip(
        Platform.TIKTOK,
        "replay_kill_42",
        music_cue_id="cue1",
    )
    assert isinstance(p, ClipBuildPlan)
    assert p.platform == Platform.TIKTOK


def test_generate_clip_uses_recommended_duration():
    s = _sys()
    p = s.generate_clip(
        Platform.TIKTOK,
        "replay_kill_42",
        music_cue_id="cue1",
    )
    assert p.target_duration_s == 30


def test_generate_clip_explicit_duration():
    s = _sys()
    p = s.generate_clip(
        Platform.TIKTOK,
        "replay_kill_42",
        target_duration_s=45,
        music_cue_id="cue1",
    )
    assert p.target_duration_s == 45


def test_generate_clip_aspect_matches_platform():
    s = _sys()
    p = s.generate_clip(
        Platform.LINKEDIN,
        "replay_42",
    )
    assert p.aspect_ratio == "16:9"


def test_generate_clip_attaches_captions():
    s = _sys()
    s.push_caption(
        "rep1",
        CaptionLine(
            start_ms=0, end_ms=1000,
            text="Magic Burst!", style="d",
        ),
    )
    p = s.generate_clip(
        Platform.TIKTOK, "rep1", music_cue_id="cue1",
    )
    assert len(p.captions) == 1
    assert p.captions[0].text == "Magic Burst!"


def test_generate_clip_no_source_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.generate_clip(Platform.TIKTOK, "")


def test_generate_clip_zero_duration_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.generate_clip(
            Platform.TIKTOK,
            "rep1",
            target_duration_s=0,
        )


def test_generate_clip_counter_increments():
    s = _sys()
    p1 = s.generate_clip(
        Platform.TIKTOK, "rep1", music_cue_id="cue1",
    )
    p2 = s.generate_clip(
        Platform.TIKTOK, "rep2", music_cue_id="cue1",
    )
    assert p1.plan_id != p2.plan_id
    assert s.plan_count() == 2


def test_get_plan_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.get_plan("ghost")


# ---- validate ----

def test_validate_clean_tiktok():
    s = _sys()
    s.push_caption(
        "r1",
        CaptionLine(0, 1000, "Hi", "default"),
    )
    p = s.generate_clip(
        Platform.TIKTOK, "r1", music_cue_id="cue1",
    )
    issues = s.validate_clip(p, Platform.TIKTOK)
    assert issues == ()


def test_validate_missing_music_for_tiktok():
    s = _sys()
    s.push_caption(
        "r1",
        CaptionLine(0, 1000, "Hi", "default"),
    )
    p = s.generate_clip(Platform.TIKTOK, "r1")
    issues = s.validate_clip(p, Platform.TIKTOK)
    assert any("music" in i for i in issues)


def test_validate_missing_captions_for_youtube():
    s = _sys()
    p = s.generate_clip(Platform.YOUTUBE_SHORTS, "r1")
    issues = s.validate_clip(p, Platform.YOUTUBE_SHORTS)
    assert any("caption" in i for i in issues)


def test_validate_duration_exceeds():
    s = _sys()
    s.push_caption(
        "r1",
        CaptionLine(0, 1000, "Hi", "default"),
    )
    p = s.generate_clip(
        Platform.TIKTOK,
        "r1",
        target_duration_s=120,
        music_cue_id="cue1",
    )
    issues = s.validate_clip(p, Platform.TIKTOK)
    assert any("duration" in i for i in issues)


def test_validate_platform_mismatch():
    s = _sys()
    p = s.generate_clip(Platform.TIKTOK, "r1")
    issues = s.validate_clip(p, Platform.LINKEDIN)
    assert any("mismatch" in i for i in issues)


def test_validate_aspect_mismatch():
    s = _sys()
    s.register_platform_spec(
        Platform.YOUTUBE_SHORTS, aspect_ratio="16:9",
    )
    # Generate clip, then change platform spec under us.
    p = s.generate_clip(Platform.YOUTUBE_SHORTS, "r1")
    # Re-register to expect a different aspect.
    s.register_platform_spec(
        Platform.YOUTUBE_SHORTS, aspect_ratio="9:16",
    )
    issues = s.validate_clip(p, Platform.YOUTUBE_SHORTS)
    assert any("aspect" in i for i in issues)


# ---- bulk ----

def test_bulk_render_produces_all():
    s = _sys()
    s.push_caption(
        "r1",
        CaptionLine(0, 1000, "Hi", "default"),
    )
    s.push_caption(
        "r2",
        CaptionLine(0, 1000, "Hey", "default"),
    )
    plans = s.bulk_render(
        ["r1", "r2"],
        [Platform.TIKTOK, Platform.LINKEDIN],
    )
    assert len(plans) == 4


def test_bulk_render_empty_inputs():
    s = _sys()
    plans = s.bulk_render([], [Platform.TIKTOK])
    assert plans == ()


# ---- hashtag cultures ----

def test_hashtag_tiktok_has_fyp():
    s = _sys()
    spec = s.get_spec(Platform.TIKTOK)
    assert "#FYP" in spec.hashtag_culture


def test_hashtag_linkedin_no_fyp():
    s = _sys()
    spec = s.get_spec(Platform.LINKEDIN)
    assert "#FYP" not in spec.hashtag_culture
