"""Tests for scene_pacing."""
from __future__ import annotations

import pytest

from server.scene_pacing import (
    Beat, BeatKind, MURCH_WEIGHTS, PROFILES,
    PacingProfile, ScenePacingSystem,
    list_profiles, recommended_shot_duration,
    score_against_murch_six,
)


def test_murch_weights_sum_to_one():
    assert sum(MURCH_WEIGHTS.values()) == pytest.approx(1.0)


def test_murch_weights_emotion_is_dominant():
    # Emotion is the largest single weight per Murch.
    assert MURCH_WEIGHTS["emotion"] == 0.51
    assert max(MURCH_WEIGHTS.values()) == MURCH_WEIGHTS["emotion"]


def test_murch_weights_priority_order():
    order = sorted(
        MURCH_WEIGHTS, key=lambda k: -MURCH_WEIGHTS[k],
    )
    assert order == [
        "emotion", "story", "rhythm",
        "eye_trace", "plane_2d", "space_3d",
    ]


def test_score_zero_all_axes_zero():
    assert score_against_murch_six({}) == 0.0


def test_score_full_emotion_only():
    s = score_against_murch_six({"emotion": 1.0})
    assert s == pytest.approx(0.51)


def test_score_all_full_returns_one():
    s = score_against_murch_six({k: 1.0 for k in MURCH_WEIGHTS})
    assert s == pytest.approx(1.0)


def test_score_out_of_range_raises():
    with pytest.raises(ValueError):
        score_against_murch_six({"emotion": 1.5})


def test_score_negative_raises():
    with pytest.raises(ValueError):
        score_against_murch_six({"emotion": -0.1})


def test_profiles_seven_scene_kinds():
    assert len(PROFILES) == 7


def test_profiles_dialogue_min_lt_max():
    p = PROFILES["dialogue"]
    assert p.min_shot_duration_s < p.avg_shot_duration_s
    assert p.avg_shot_duration_s < p.max_shot_duration_s


def test_combat_close_short_shots():
    p = PROFILES["combat_close"]
    assert p.avg_shot_duration_s < 2.0


def test_combat_close_allows_jump_cuts():
    assert PROFILES["combat_close"].allowed_jump_cuts is True


def test_dialogue_no_jump_cuts():
    assert PROFILES["dialogue"].allowed_jump_cuts is False


def test_recommended_shot_duration_climax_short():
    d = recommended_shot_duration(BeatKind.CLIMAX)
    assert d < 2.0


def test_recommended_shot_duration_setup_long():
    d = recommended_shot_duration(BeatKind.SETUP)
    assert d > 5.0


def test_recommended_shot_duration_clamped_to_combat_max():
    # SETUP wants 6s; combat_close max is 3.5s.
    d = recommended_shot_duration(
        BeatKind.SETUP, scene_kind="combat_close",
    )
    assert d == PROFILES["combat_close"].max_shot_duration_s


def test_recommended_shot_duration_unknown_scene_raises():
    with pytest.raises(ValueError):
        recommended_shot_duration(
            BeatKind.SETUP, scene_kind="ghost",
        )


def test_register_sequence_happy():
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="combat_close",
        beats=[
            Beat(BeatKind.SETUP, 5.0, 0.3),
            Beat(BeatKind.ESCALATION, 8.0, 0.6),
            Beat(BeatKind.CLIMAX, 4.0, 1.0),
            Beat(BeatKind.FALLOUT, 6.0, 0.4),
        ],
    )
    assert sid.startswith("seq_")
    seq = s.get(sid)
    assert seq.scene_kind == "combat_close"
    assert len(seq.beats) == 4


def test_register_sequence_unknown_scene_raises():
    s = ScenePacingSystem()
    with pytest.raises(ValueError):
        s.register_sequence(
            scene_kind="__none__",
            beats=[Beat(BeatKind.SETUP, 1.0, 0.1)],
        )


def test_register_sequence_no_beats_raises():
    s = ScenePacingSystem()
    with pytest.raises(ValueError):
        s.register_sequence(
            scene_kind="dialogue", beats=[],
        )


def test_register_sequence_bad_intensity_raises():
    s = ScenePacingSystem()
    with pytest.raises(ValueError):
        s.register_sequence(
            scene_kind="dialogue",
            beats=[Beat(BeatKind.SETUP, 1.0, 1.5)],
        )


def test_register_sequence_zero_duration_raises():
    s = ScenePacingSystem()
    with pytest.raises(ValueError):
        s.register_sequence(
            scene_kind="dialogue",
            beats=[Beat(BeatKind.SETUP, 0, 0.5)],
        )


def test_beat_at_walks_timeline():
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="dialogue",
        beats=[
            Beat(BeatKind.SETUP, 5.0, 0.3),
            Beat(BeatKind.CLIMAX, 2.0, 1.0),
            Beat(BeatKind.FALLOUT, 4.0, 0.4),
        ],
    )
    assert s.beat_at(sid, 1.0).kind == BeatKind.SETUP
    assert s.beat_at(sid, 6.0).kind == BeatKind.CLIMAX
    assert s.beat_at(sid, 8.0).kind == BeatKind.FALLOUT
    # Past end → last beat
    assert s.beat_at(sid, 99.0).kind == BeatKind.FALLOUT


def test_beat_at_negative_raises():
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="dialogue",
        beats=[Beat(BeatKind.SETUP, 5.0, 0.3)],
    )
    with pytest.raises(ValueError):
        s.beat_at(sid, -1.0)


def test_advise_cut_force_cut_when_max_exceeded():
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="combat_close",
        beats=[Beat(BeatKind.CLIMAX, 4.0, 1.0)],
    )
    out = s.advise_cut(
        sid=sid, now_t=0.5,
        current_shot_duration=999.0,
        six_axis_scores={},  # all zero
    )
    assert out["should_cut"] is True
    assert out["reason"] == "exceeded_max_shot_duration"


def test_advise_cut_blocks_below_min_when_no_jump():
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="dialogue",
        beats=[Beat(BeatKind.SETUP, 5.0, 0.3)],
    )
    out = s.advise_cut(
        sid=sid, now_t=0.1,
        current_shot_duration=0.2,
        six_axis_scores={k: 1.0 for k in MURCH_WEIGHTS},
    )
    assert out["should_cut"] is False
    assert out["reason"] == "below_min_shot_duration"


def test_advise_cut_climax_lower_threshold():
    # Climax cuts at threshold 0.35; emotion=1 alone yields
    # 0.51 which exceeds 0.35.
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="combat_close",
        beats=[Beat(BeatKind.CLIMAX, 4.0, 1.0)],
    )
    out = s.advise_cut(
        sid=sid, now_t=0.5,
        current_shot_duration=1.5,
        six_axis_scores={"emotion": 1.0},
    )
    assert out["should_cut"] is True
    assert out["reason"] == "murch_threshold_met"


def test_advise_cut_setup_higher_threshold():
    # Setup beats hold; emotion=1 alone (0.51) is < 0.65.
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="dialogue",
        beats=[Beat(BeatKind.SETUP, 8.0, 0.2)],
    )
    out = s.advise_cut(
        sid=sid, now_t=4.0,
        current_shot_duration=2.0,
        six_axis_scores={"emotion": 1.0},
    )
    assert out["should_cut"] is False


def test_should_cut_now_bool_thinwrapper():
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="combat_close",
        beats=[Beat(BeatKind.CLIMAX, 4.0, 1.0)],
    )
    assert (
        s.should_cut_now(
            sid=sid, now_t=0.5,
            current_shot_duration=2.0,
            six_axis_scores={"emotion": 1.0, "story": 1.0},
        )
        is True
    )


def test_total_duration_sums_beats():
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="dialogue",
        beats=[
            Beat(BeatKind.SETUP, 5.0, 0.3),
            Beat(BeatKind.CLIMAX, 2.0, 1.0),
        ],
    )
    assert s.total_duration(sid) == pytest.approx(7.0)


def test_list_profiles_sorted():
    names = list_profiles()
    assert names == tuple(sorted(names))


def test_get_unknown_sid_raises():
    s = ScenePacingSystem()
    with pytest.raises(KeyError):
        s.get("seq_nope")


def test_advise_cut_negative_duration_raises():
    s = ScenePacingSystem()
    sid = s.register_sequence(
        scene_kind="dialogue",
        beats=[Beat(BeatKind.SETUP, 5.0, 0.3)],
    )
    with pytest.raises(ValueError):
        s.advise_cut(
            sid=sid, now_t=0.0,
            current_shot_duration=-1.0,
            six_axis_scores={},
        )
