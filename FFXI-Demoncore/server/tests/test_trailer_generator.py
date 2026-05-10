"""Tests for trailer_generator."""
from __future__ import annotations

import pytest

from server.trailer_generator import (
    ShotSlot,
    SourceKind,
    TitleCard,
    TrailerBuildPlan,
    TrailerInput,
    TrailerKind,
    TrailerSystem,
)


def _sys() -> TrailerSystem:
    return TrailerSystem()


# ---- enum coverage ----

def test_trailer_kind_count():
    assert len(list(TrailerKind)) == 7


def test_trailer_kind_has_teaser():
    assert TrailerKind.TEASER_30S in list(TrailerKind)


def test_trailer_kind_has_deep_dive():
    assert TrailerKind.DEEP_DIVE_5MIN in list(TrailerKind)


def test_trailer_kind_has_vertical():
    assert (
        TrailerKind.FEATURE_VERTICAL_VIDEO_30S
        in list(TrailerKind)
    )


def test_source_kind_count():
    assert len(list(SourceKind)) == 4


def test_source_kind_has_mixed():
    assert SourceKind.MIXED in list(SourceKind)


# ---- estimated_runtime ----

def test_estimated_runtime_teaser():
    assert _sys().estimated_runtime(
        TrailerKind.TEASER_30S,
    ) == 30


def test_estimated_runtime_story():
    assert _sys().estimated_runtime(
        TrailerKind.STORY_60S,
    ) == 60


def test_estimated_runtime_gameplay():
    assert _sys().estimated_runtime(
        TrailerKind.GAMEPLAY_2MIN,
    ) == 120


def test_estimated_runtime_deep_dive():
    assert _sys().estimated_runtime(
        TrailerKind.DEEP_DIVE_5MIN,
    ) == 300


def test_estimated_runtime_launch():
    assert _sys().estimated_runtime(
        TrailerKind.LAUNCH_PROMO_90S,
    ) == 90


def test_estimated_runtime_convention():
    assert _sys().estimated_runtime(
        TrailerKind.CONVENTION_SIZZLE_90S,
    ) == 90


# ---- shots_per_kind ----

def test_shots_per_kind_teaser_fast():
    n = _sys().shots_per_kind(TrailerKind.TEASER_30S)
    assert n >= 10  # 30s / ~1.5s per shot - title cards


def test_shots_per_kind_deep_dive_slow():
    # 300s / ~6.5s -> ~45 shots
    n = _sys().shots_per_kind(TrailerKind.DEEP_DIVE_5MIN)
    assert 30 <= n <= 60


def test_shots_per_kind_positive():
    for k in TrailerKind:
        assert _sys().shots_per_kind(k) > 0


# ---- voice cast ----

def test_register_voice_cast():
    s = _sys()
    s.register_voice_cast("Aria")
    s.register_voice_cast("Drest")
    assert "Aria" in s.voice_cast()
    assert "Drest" in s.voice_cast()


def test_voice_cast_dedupes():
    s = _sys()
    s.register_voice_cast("Aria")
    s.register_voice_cast("Aria")
    assert s.voice_cast().count("Aria") == 1


def test_voice_cast_empty_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.register_voice_cast("")


# ---- build trailer ----

def test_build_trailer_returns_plan():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.TEASER_30S,
        music_cue_id="cue1",
        showcase_seq_name="first_play_intro",
    ))
    assert isinstance(p, TrailerBuildPlan)
    assert p.target_kind == TrailerKind.TEASER_30S
    assert p.target_runtime_s == 30


def test_build_trailer_missing_music_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.build_trailer(TrailerInput(
            source_kind=SourceKind.CHOREOGRAPHY,
            target_kind=TrailerKind.TEASER_30S,
            music_cue_id="",
        ))


def test_build_trailer_has_title_cards():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.LAUNCH_PROMO_90S,
        music_cue_id="cue1",
    ))
    assert len(p.title_cards) == 3
    positions = [c.position for c in p.title_cards]
    assert positions == ["open", "mid", "end"]


def test_build_trailer_mid_card_available_now_for_launch():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.LAUNCH_PROMO_90S,
        music_cue_id="cue1",
    ))
    mid = [c for c in p.title_cards if c.position == "mid"][0]
    assert mid.text == "Available Now"


def test_build_trailer_mid_card_coming_soon_for_teaser():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.TEASER_30S,
        music_cue_id="cue1",
    ))
    mid = [c for c in p.title_cards if c.position == "mid"][0]
    assert mid.text == "Coming Soon"


def test_build_trailer_first_shot_is_hero():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.STORY_60S,
        music_cue_id="cue1",
    ))
    assert p.shot_list[0].is_hero
    assert p.shot_list[-1].is_hero


def test_build_trailer_first_shot_wide_establishing():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.STORY_60S,
        music_cue_id="cue1",
    ))
    assert p.shot_list[0].label == "wide_establishing"


def test_build_trailer_replay_buffer_source():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.REPLAY_BUFFER,
        target_kind=TrailerKind.STORY_60S,
        music_cue_id="cue1",
        replay_event_ids=("intro_e1", "conflict_e1", "resolution_e1"),
    ))
    refs = [s.source_ref for s in p.shot_list]
    assert "intro_e1" in refs


def test_build_trailer_manual_shot_list():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MANUAL_SHOT_LIST,
        target_kind=TrailerKind.TEASER_30S,
        music_cue_id="cue1",
        manual_shot_list=tuple(f"sh_{i}" for i in range(40)),
    ))
    # Should be capped at the per-kind shot count.
    assert len(p.shot_list) == s.shots_per_kind(
        TrailerKind.TEASER_30S,
    )


def test_build_trailer_mixed_source():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MIXED,
        target_kind=TrailerKind.GAMEPLAY_2MIN,
        music_cue_id="cue1",
        replay_event_ids=("combat_e1", "combat_e2"),
        showcase_seq_name="demo_walk",
    ))
    assert len(p.shot_list) > 0


def test_build_trailer_estimated_runtime_close_to_budget():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.STORY_60S,
        music_cue_id="cue1",
    ))
    assert abs(p.estimated_runtime_s - 60) <= 3


def test_build_trailer_plan_counter_increments():
    s = _sys()
    p1 = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.TEASER_30S,
        music_cue_id="cue1",
    ))
    p2 = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.TEASER_30S,
        music_cue_id="cue1",
    ))
    assert p1.plan_id != p2.plan_id
    assert s.plan_count() == 2


def test_build_trailer_voice_cast_credited():
    s = _sys()
    s.register_voice_cast("Aria")
    s.register_voice_cast("Drest")
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.CHOREOGRAPHY,
        target_kind=TrailerKind.TEASER_30S,
        music_cue_id="cue1",
    ))
    assert p.end_credits_voice_cast == ("Aria", "Drest")


# ---- get_plan ----

def test_get_plan_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.get_plan("ghost")


# ---- validate ----

def test_validate_teaser_no_spoilers_clean():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MANUAL_SHOT_LIST,
        target_kind=TrailerKind.TEASER_30S,
        music_cue_id="cue1",
        manual_shot_list=("hero_zone", "town_hall", "marketplace_close", "merchant_wide"),
    ))
    issues = s.validate(p)
    spoiler_issues = [i for i in issues if "spoiler" in i]
    assert spoiler_issues == []


def test_validate_teaser_with_spoiler_flagged():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MANUAL_SHOT_LIST,
        target_kind=TrailerKind.TEASER_30S,
        music_cue_id="cue1",
        manual_shot_list=("intro_hero", "final_boss_reveal", "marketplace", "town"),
    ))
    issues = s.validate(p)
    assert any("spoiler" in i for i in issues)


def test_validate_story_missing_intro():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MANUAL_SHOT_LIST,
        target_kind=TrailerKind.STORY_60S,
        music_cue_id="cue1",
        manual_shot_list=tuple(
            ["conflict_battle"] * 10
            + ["resolution_victory"] * 10
        ),
    ))
    issues = s.validate(p)
    assert any("intro" in i for i in issues)


def test_validate_story_missing_conflict():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MANUAL_SHOT_LIST,
        target_kind=TrailerKind.STORY_60S,
        music_cue_id="cue1",
        manual_shot_list=tuple(
            ["intro_establishing"] * 10
            + ["resolution_victory"] * 10
        ),
    ))
    issues = s.validate(p)
    assert any("conflict" in i for i in issues)


def test_validate_story_missing_resolution():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MANUAL_SHOT_LIST,
        target_kind=TrailerKind.STORY_60S,
        music_cue_id="cue1",
        manual_shot_list=tuple(
            ["intro_establishing"] * 10
            + ["conflict_battle"] * 10
        ),
    ))
    issues = s.validate(p)
    assert any("resolution" in i for i in issues)


def test_validate_story_complete_clean():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MANUAL_SHOT_LIST,
        target_kind=TrailerKind.STORY_60S,
        music_cue_id="cue1",
        manual_shot_list=tuple(
            ["intro_establishing"] * 7
            + ["conflict_battle"] * 7
            + ["resolution_victory"] * 7
        ),
    ))
    issues = s.validate(p)
    structural = [
        i for i in issues
        if any(k in i for k in ("intro", "conflict", "resolution"))
    ]
    assert structural == []


def test_validate_gameplay_missing_mechanics():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MANUAL_SHOT_LIST,
        target_kind=TrailerKind.GAMEPLAY_2MIN,
        music_cue_id="cue1",
        manual_shot_list=tuple(
            ["scenery_shot"] * 40
        ),
    ))
    issues = s.validate(p)
    assert any("mechanic" in i for i in issues)


def test_validate_gameplay_has_mechanics():
    s = _sys()
    p = s.build_trailer(TrailerInput(
        source_kind=SourceKind.MANUAL_SHOT_LIST,
        target_kind=TrailerKind.GAMEPLAY_2MIN,
        music_cue_id="cue1",
        manual_shot_list=tuple(
            ["combat_close"] * 40
        ),
    ))
    issues = s.validate(p)
    assert not any("mechanic" in i for i in issues)


# ---- auto trailer ----

def test_trailer_for_event_returns_plan():
    s = _sys()
    p = s.trailer_for_event(
        "evt_kill_42",
        zone_id="bastok_markets",
        character_id="p1",
    )
    assert isinstance(p, TrailerBuildPlan)
    assert p.target_kind == TrailerKind.FEATURE_VERTICAL_VIDEO_30S


def test_trailer_for_event_empty_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.trailer_for_event("")


def test_trailer_for_event_default_music():
    s = _sys()
    p = s.trailer_for_event("evt1")
    assert p.music_cue_id == "demoncore_share_loop"
