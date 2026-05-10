"""Tests for character_animation."""
from __future__ import annotations

import pytest

from server.character_animation import (
    AnimationKind,
    AnimationSystem,
    AnimClip,
    Gender,
    OverlayLayer,
    Race,
    make_default_clip,
    populate_default_library,
)


# ---- enums ----

def test_animation_kind_at_least_25():
    assert len(list(AnimationKind)) >= 25


def test_five_races_present():
    assert {r for r in Race} == {
        Race.HUME, Race.ELVAAN, Race.TARUTARU,
        Race.MITHRA, Race.GALKA,
    }


def test_two_genders():
    assert {g for g in Gender} == {
        Gender.MALE, Gender.FEMALE,
    }


def test_three_overlay_layers():
    assert {ol for ol in OverlayLayer} == {
        OverlayLayer.NONE,
        OverlayLayer.UPPER_BODY,
        OverlayLayer.FACE_ONLY,
    }


# ---- register / lookup ----

def test_register_and_get():
    s = AnimationSystem()
    c = make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
    )
    s.register_clip(c)
    assert s.get(c.clip_id) is c


def test_get_missing_raises():
    s = AnimationSystem()
    with pytest.raises(KeyError):
        s.get("missing")


def test_register_empty_id_raises():
    s = AnimationSystem()
    with pytest.raises(ValueError):
        s.register_clip(AnimClip(
            clip_id="",
            kind=AnimationKind.IDLE,
            race=Race.HUME,
            gender=Gender.MALE,
            clip_uri="anim://x",
            duration_s=1.0,
            looping=True,
        ))


def test_register_zero_duration_raises():
    s = AnimationSystem()
    with pytest.raises(ValueError):
        s.register_clip(AnimClip(
            clip_id="c",
            kind=AnimationKind.IDLE,
            race=Race.HUME,
            gender=Gender.MALE,
            clip_uri="anim://x",
            duration_s=0.0,
            looping=True,
        ))


def test_register_duplicate_raises():
    s = AnimationSystem()
    c = make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
    )
    s.register_clip(c)
    with pytest.raises(ValueError):
        s.register_clip(c)


def test_lookup_returns_only_exact_match():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
    ))
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.FEMALE,
    ))
    out = s.lookup(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
    )
    assert len(out) == 1
    assert out[0].gender == Gender.MALE


def test_lookup_empty_when_missing():
    s = AnimationSystem()
    assert s.lookup(
        AnimationKind.IDLE, Race.GALKA, Gender.MALE,
    ) == ()


# ---- best_match fallback chain ----

def test_best_match_exact_hits_first():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.WALK, Race.GALKA, Gender.MALE,
        clip_id="galka_m_walk",
    ))
    s.register_clip(make_default_clip(
        AnimationKind.WALK, Race.HUME, Gender.MALE,
        clip_id="hume_m_walk",
    ))
    out = s.best_match(
        AnimationKind.WALK, Race.GALKA, Gender.MALE,
    )
    assert out is not None
    assert out.clip_id == "galka_m_walk"


def test_best_match_falls_back_other_gender_same_race():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.WALK, Race.MITHRA, Gender.FEMALE,
        clip_id="mithra_f_walk",
    ))
    out = s.best_match(
        AnimationKind.WALK, Race.MITHRA, Gender.MALE,
    )
    assert out is not None
    assert out.clip_id == "mithra_f_walk"


def test_best_match_falls_back_to_hume_same_gender():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.WALK, Race.HUME, Gender.MALE,
        clip_id="hume_m_walk",
    ))
    out = s.best_match(
        AnimationKind.WALK, Race.GALKA, Gender.MALE,
    )
    assert out is not None
    assert out.clip_id == "hume_m_walk"


def test_best_match_falls_back_to_hume_other_gender():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.WALK, Race.HUME, Gender.FEMALE,
        clip_id="hume_f_walk",
    ))
    out = s.best_match(
        AnimationKind.WALK, Race.GALKA, Gender.MALE,
    )
    assert out is not None
    assert out.clip_id == "hume_f_walk"


def test_best_match_returns_none_when_kind_missing():
    s = AnimationSystem()
    out = s.best_match(
        AnimationKind.KO_FALL, Race.HUME, Gender.MALE,
    )
    assert out is None


# ---- all_for_race ----

def test_all_for_race_returns_only_that_race():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.GALKA, Gender.MALE,
    ))
    s.register_clip(make_default_clip(
        AnimationKind.WALK, Race.GALKA, Gender.MALE,
    ))
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
    ))
    out = s.all_for_race(Race.GALKA)
    assert len(out) == 2
    assert all(c.race == Race.GALKA for c in out)


def test_all_for_race_sorted_by_clip_id():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.WALK, Race.HUME, Gender.MALE,
        clip_id="zzz",
    ))
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
        clip_id="aaa",
    ))
    out = s.all_for_race(Race.HUME)
    assert [c.clip_id for c in out] == ["aaa", "zzz"]


def test_all_kinds_for_race_gender():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
    ))
    s.register_clip(make_default_clip(
        AnimationKind.WALK, Race.HUME, Gender.MALE,
    ))
    out = s.all_kinds_for(Race.HUME, Gender.MALE)
    assert AnimationKind.IDLE in out
    assert AnimationKind.WALK in out
    assert AnimationKind.SPRINT not in out


# ---- can_blend ----

def test_can_blend_self_false():
    s = AnimationSystem()
    assert not s.can_blend(
        AnimationKind.WALK, AnimationKind.WALK,
    )


def test_can_blend_walk_and_talk_head():
    s = AnimationSystem()
    assert s.can_blend(
        AnimationKind.WALK, AnimationKind.TALK_HEAD,
    )


def test_can_blend_walk_and_gesture_point():
    s = AnimationSystem()
    assert s.can_blend(
        AnimationKind.WALK, AnimationKind.GESTURE_POINT,
    )


def test_can_blend_gesture_and_talk_head():
    s = AnimationSystem()
    assert s.can_blend(
        AnimationKind.GESTURE_BECKON, AnimationKind.TALK_HEAD,
    )


def test_combat_stance_blocks_walk():
    s = AnimationSystem()
    assert not s.can_blend(
        AnimationKind.COMBAT_STANCE, AnimationKind.WALK,
    )


def test_combat_stance_blocks_walk_other_order():
    s = AnimationSystem()
    assert not s.can_blend(
        AnimationKind.WALK, AnimationKind.COMBAT_STANCE,
    )


def test_walk_run_dont_blend():
    s = AnimationSystem()
    assert not s.can_blend(
        AnimationKind.WALK, AnimationKind.RUN,
    )


def test_two_face_only_dont_blend():
    s = AnimationSystem()
    assert not s.can_blend(
        AnimationKind.TALK_HEAD, AnimationKind.EMOTE_NOD,
    )


def test_two_upper_body_dont_blend():
    s = AnimationSystem()
    assert not s.can_blend(
        AnimationKind.GESTURE_POINT, AnimationKind.GESTURE_BECKON,
    )


def test_sit_blocks_locomotion():
    s = AnimationSystem()
    assert not s.can_blend(
        AnimationKind.SIT, AnimationKind.WALK,
    )


def test_sit_can_blend_with_talk_head():
    s = AnimationSystem()
    assert s.can_blend(
        AnimationKind.SIT, AnimationKind.TALK_HEAD,
    )


def test_combat_and_cast_dont_blend():
    s = AnimationSystem()
    # both lower-body-locking
    assert not s.can_blend(
        AnimationKind.COMBAT_STANCE, AnimationKind.CAST_BEGIN,
    )


# ---- emotion_to_anim ----

def test_emotion_happy_to_laugh():
    s = AnimationSystem()
    assert s.emotion_to_anim("HAPPY") == (
        AnimationKind.REACTION_LAUGH
    )


def test_emotion_afraid_to_fear():
    s = AnimationSystem()
    assert s.emotion_to_anim("AFRAID") == (
        AnimationKind.REACTION_FEAR
    )


def test_emotion_angry_to_anger():
    s = AnimationSystem()
    assert s.emotion_to_anim("ANGRY") == (
        AnimationKind.REACTION_ANGER
    )


def test_emotion_unknown_falls_to_idle():
    s = AnimationSystem()
    assert s.emotion_to_anim("MYSTERY") == AnimationKind.IDLE


def test_emotion_lowercase_works():
    s = AnimationSystem()
    assert s.emotion_to_anim("happy") == (
        AnimationKind.REACTION_LAUGH
    )


# ---- idle_variation_for ----

def test_idle_variation_round_robin():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.MITHRA, Gender.FEMALE,
        clip_id="mithra_f_idle_a",
    ))
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.MITHRA, Gender.FEMALE,
        clip_id="mithra_f_idle_b",
    ))
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.MITHRA, Gender.FEMALE,
        clip_id="mithra_f_idle_c",
    ))
    seen = []
    for _ in range(6):
        c = s.idle_variation_for(Race.MITHRA, Gender.FEMALE)
        assert c is not None
        seen.append(c.clip_id)
    # First 3 cycles all 3 clips, next 3 cycle again.
    assert set(seen[:3]) == {
        "mithra_f_idle_a",
        "mithra_f_idle_b",
        "mithra_f_idle_c",
    }
    assert seen[:3] == seen[3:]


def test_idle_variation_falls_back_when_missing():
    s = AnimationSystem()
    s.register_clip(make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
        clip_id="hume_m_idle",
    ))
    out = s.idle_variation_for(Race.GALKA, Gender.MALE)
    assert out is not None
    assert out.clip_id == "hume_m_idle"


def test_idle_variation_none_when_no_idle_anywhere():
    s = AnimationSystem()
    out = s.idle_variation_for(Race.HUME, Gender.MALE)
    assert out is None


# ---- overlay layer + clip helpers ----

def test_overlay_layer_for_face_only_kinds():
    s = AnimationSystem()
    assert s.overlay_layer_for(AnimationKind.TALK_HEAD) == (
        OverlayLayer.FACE_ONLY
    )
    assert s.overlay_layer_for(AnimationKind.EMOTE_NOD) == (
        OverlayLayer.FACE_ONLY
    )


def test_overlay_layer_for_upper_body_kinds():
    s = AnimationSystem()
    assert s.overlay_layer_for(
        AnimationKind.GESTURE_POINT,
    ) == OverlayLayer.UPPER_BODY
    assert s.overlay_layer_for(
        AnimationKind.EMOTE_WAVE,
    ) == OverlayLayer.UPPER_BODY


def test_overlay_layer_for_locomotion_is_none():
    s = AnimationSystem()
    assert s.overlay_layer_for(
        AnimationKind.WALK,
    ) == OverlayLayer.NONE


def test_default_clip_has_root_motion_for_walk():
    c = make_default_clip(
        AnimationKind.WALK, Race.HUME, Gender.MALE,
    )
    assert c.root_motion is True


def test_default_clip_no_root_motion_for_idle():
    c = make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
    )
    assert c.root_motion is False


def test_default_clip_idle_loops():
    c = make_default_clip(
        AnimationKind.IDLE, Race.HUME, Gender.MALE,
    )
    assert c.looping is True


def test_default_clip_gesture_doesnt_loop():
    c = make_default_clip(
        AnimationKind.GESTURE_BOW, Race.HUME, Gender.MALE,
    )
    assert c.looping is False


def test_default_clip_uri_format():
    c = make_default_clip(
        AnimationKind.IDLE, Race.GALKA, Gender.FEMALE,
    )
    assert c.clip_uri.startswith("anim://")


# ---- populate_default_library ----

def test_populate_default_library_at_least_50_clips():
    s = AnimationSystem()
    n = populate_default_library(s)
    assert n >= 50
    assert s.clip_count() == n


def test_populate_covers_all_races():
    s = AnimationSystem()
    populate_default_library(s)
    for race in Race:
        assert len(s.all_for_race(race)) > 0


def test_populate_covers_high_value_kinds_for_each_race():
    s = AnimationSystem()
    populate_default_library(s)
    for race in Race:
        for gender in Gender:
            for kind in (
                AnimationKind.IDLE,
                AnimationKind.WALK,
                AnimationKind.TALK_HEAD,
                AnimationKind.REACTION_SURPRISE,
            ):
                assert s.best_match(kind, race, gender) is not None


def test_populate_provides_hume_extras():
    s = AnimationSystem()
    populate_default_library(s)
    for kind in (
        AnimationKind.RUN,
        AnimationKind.GESTURE_BOW,
        AnimationKind.EMOTE_WAVE,
        AnimationKind.REACTION_LAUGH,
        AnimationKind.REACTION_FEAR,
        AnimationKind.COMBAT_STANCE,
    ):
        assert s.best_match(
            kind, Race.HUME, Gender.MALE,
        ) is not None


def test_populate_galka_falls_back_to_hume_for_run():
    s = AnimationSystem()
    populate_default_library(s)
    out = s.best_match(
        AnimationKind.RUN, Race.GALKA, Gender.MALE,
    )
    assert out is not None
    # No native galka run was registered; fallback chain
    # lands on a HUME clip.
    assert out.race == Race.HUME
