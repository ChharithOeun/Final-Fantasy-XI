"""Tests for director_ai."""
from __future__ import annotations

import pytest

from server.director_ai import (
    DirectorAI, SceneKind, ShotSuggestion, ShotType, Tempo,
)


def test_suggest_shots_dialogue_medium_returns_top_three():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.DIALOGUE, Tempo.MEDIUM, focus_targets=2,
    )
    assert len(out) == 3
    assert all(isinstance(s, ShotSuggestion) for s in out)


def test_suggest_shots_emotional_slow_picks_extreme_cu():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.EMOTIONAL_BEAT, Tempo.SLOW, focus_targets=1,
    )
    assert out[0].shot == ShotType.EXTREME_CLOSE_UP


def test_suggest_shots_combat_close_fast_picks_handheld():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.COMBAT_CLOSE, Tempo.FAST, focus_targets=1,
    )
    assert out[0].shot == ShotType.HANDHELD


def test_suggest_shots_combat_open_fast_picks_handheld():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.COMBAT_OPEN, Tempo.FAST, focus_targets=1,
    )
    assert out[0].shot == ShotType.HANDHELD


def test_suggest_shots_reveal_slow_picks_wide():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.REVEAL, Tempo.SLOW, focus_targets=0,
    )
    assert out[0].shot == ShotType.WIDE_ESTABLISHING


def test_suggest_shots_exploration_slow_picks_wide():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.EXPLORATION, Tempo.SLOW, focus_targets=0,
    )
    assert out[0].shot == ShotType.WIDE_ESTABLISHING


def test_suggest_shots_zero_targets_drops_two_shot():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.DIALOGUE, Tempo.SLOW, focus_targets=0,
    )
    shots = {s.shot for s in out}
    assert ShotType.MEDIUM_TWO_SHOT not in shots
    assert ShotType.OVER_THE_SHOULDER not in shots


def test_suggest_shots_two_targets_boost_two_shot():
    d = DirectorAI()
    out2 = d.suggest_shots(
        SceneKind.DIALOGUE, Tempo.MEDIUM, focus_targets=2,
    )
    out1 = d.suggest_shots(
        SceneKind.DIALOGUE, Tempo.MEDIUM, focus_targets=1,
    )
    # OTS score should be higher with 2 targets than 1.
    def get(out, st):
        for s in out:
            if s.shot == st:
                return s.score
        return 0.0
    assert get(out2, ShotType.OVER_THE_SHOULDER) > get(
        out1, ShotType.OVER_THE_SHOULDER,
    )


def test_suggest_shots_negative_targets_raises():
    d = DirectorAI()
    with pytest.raises(ValueError):
        d.suggest_shots(
            SceneKind.DIALOGUE, Tempo.MEDIUM,
            focus_targets=-1,
        )


def test_violates_180_no_flip_no_violation():
    d = DirectorAI()
    assert (
        d.violates_180(
            ShotType.OVER_THE_SHOULDER, ShotType.MEDIUM,
            side_flipped=False,
        )
        is False
    )


def test_violates_180_flip_with_medium_violates():
    d = DirectorAI()
    assert (
        d.violates_180(
            ShotType.OVER_THE_SHOULDER, ShotType.MEDIUM,
            side_flipped=True,
        )
        is True
    )


def test_violates_180_overhead_legal_crossing():
    d = DirectorAI()
    assert (
        d.violates_180(
            ShotType.MEDIUM, ShotType.OVERHEAD,
            side_flipped=True,
        )
        is False
    )


def test_violates_180_extreme_close_up_legal_crossing():
    d = DirectorAI()
    assert (
        d.violates_180(
            ShotType.MEDIUM, ShotType.EXTREME_CLOSE_UP,
            side_flipped=True,
        )
        is False
    )


def test_violates_180_pov_legal_crossing():
    d = DirectorAI()
    assert (
        d.violates_180(
            ShotType.MEDIUM, ShotType.POV,
            side_flipped=True,
        )
        is False
    )


def test_pick_next_shot_alternates_ots():
    d = DirectorAI()
    out_a = d.pick_next_shot(ShotType.OVER_THE_SHOULDER, 1)
    assert out_a == ShotType.OVER_THE_SHOULDER  # paired


def test_pick_next_shot_holds_on_even_beat():
    d = DirectorAI()
    out = d.pick_next_shot(ShotType.MEDIUM, 0)
    assert out == ShotType.MEDIUM


def test_pick_next_shot_negative_beat_raises():
    d = DirectorAI()
    with pytest.raises(ValueError):
        d.pick_next_shot(ShotType.MEDIUM, -1)


def test_score_shot_recommended_high():
    d = DirectorAI()
    sc = d.score_shot(
        ShotType.HANDHELD,
        SceneKind.COMBAT_CLOSE, Tempo.FAST,
        focus_targets=1,
    )
    assert sc >= 0.9


def test_score_shot_unrecommended_zero():
    d = DirectorAI()
    sc = d.score_shot(
        ShotType.OVERHEAD,
        SceneKind.DIALOGUE, Tempo.SLOW,
        focus_targets=2,
    )
    assert sc == 0.0


def test_score_shot_zero_targets_kills_intimate():
    d = DirectorAI()
    sc = d.score_shot(
        ShotType.CLOSE_UP,
        SceneKind.DIALOGUE, Tempo.FAST,
        focus_targets=0,
    )
    assert sc == 0.0


def test_score_shot_two_targets_ots_bonus():
    d = DirectorAI()
    sc1 = d.score_shot(
        ShotType.OVER_THE_SHOULDER,
        SceneKind.DIALOGUE, Tempo.MEDIUM,
        focus_targets=1,
    )
    sc2 = d.score_shot(
        ShotType.OVER_THE_SHOULDER,
        SceneKind.DIALOGUE, Tempo.MEDIUM,
        focus_targets=2,
    )
    assert sc2 > sc1


def test_suggestions_sorted_descending():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.DIALOGUE, Tempo.MEDIUM, focus_targets=2,
    )
    scores = [s.score for s in out]
    assert scores == sorted(scores, reverse=True)


def test_suggestions_distinct():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.COMBAT_OPEN, Tempo.FAST, focus_targets=1,
    )
    shots = [s.shot for s in out]
    assert len(set(shots)) == len(shots)


def test_action_set_piece_fast_handheld_top():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.ACTION_SET_PIECE, Tempo.FAST,
        focus_targets=1,
    )
    assert out[0].shot == ShotType.HANDHELD


def test_dialogue_fast_close_up_top():
    d = DirectorAI()
    out = d.suggest_shots(
        SceneKind.DIALOGUE, Tempo.FAST, focus_targets=1,
    )
    # top must be CU per matrix
    assert out[0].shot == ShotType.CLOSE_UP


def test_score_shot_negative_focus_raises():
    d = DirectorAI()
    with pytest.raises(ValueError):
        d.score_shot(
            ShotType.MEDIUM,
            SceneKind.DIALOGUE, Tempo.SLOW,
            focus_targets=-2,
        )
