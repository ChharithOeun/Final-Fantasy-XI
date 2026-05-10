"""Tests for eye_animation."""
from __future__ import annotations

import pytest

from server.eye_animation import (
    BLINK_RATE_PER_MIN,
    EyeAnimationSystem,
    EyeState,
    Mood,
)


# ---- enum / table coverage ----

def test_five_moods():
    assert {m for m in Mood} == {
        Mood.CALM, Mood.FOCUSED, Mood.ANXIOUS,
        Mood.IN_COMBAT, Mood.DEAD,
    }


def test_blink_rate_table_complete():
    for m in Mood:
        assert m in BLINK_RATE_PER_MIN


def test_blink_rate_calm_is_17():
    assert BLINK_RATE_PER_MIN[Mood.CALM] == 17.0


def test_blink_rate_combat_suppressed():
    assert (
        BLINK_RATE_PER_MIN[Mood.IN_COMBAT]
        < BLINK_RATE_PER_MIN[Mood.CALM]
    )


def test_blink_rate_dead_is_zero():
    assert BLINK_RATE_PER_MIN[Mood.DEAD] == 0.0


def test_blink_rate_anxious_highest():
    rates = list(BLINK_RATE_PER_MIN.values())
    assert BLINK_RATE_PER_MIN[Mood.ANXIOUS] == max(rates)


# ---- system init ----

def test_default_engagement_radius():
    s = EyeAnimationSystem()
    assert s.engagement_radius_m == 6.0


def test_negative_radius_raises():
    with pytest.raises(ValueError):
        EyeAnimationSystem(engagement_radius_m=-1.0)


def test_inverted_hold_range_raises():
    with pytest.raises(ValueError):
        EyeAnimationSystem(
            contact_hold_min_s=4.0,
            contact_hold_max_s=2.0,
        )


# ---- registration ----

def test_register_returns_state():
    s = EyeAnimationSystem()
    st = s.register_eyes("npc_1")
    assert isinstance(st, EyeState)
    assert st.npc_id == "npc_1"


def test_register_empty_id_raises():
    s = EyeAnimationSystem()
    with pytest.raises(ValueError):
        s.register_eyes("")


def test_register_duplicate_raises():
    s = EyeAnimationSystem()
    s.register_eyes("npc_1")
    with pytest.raises(ValueError):
        s.register_eyes("npc_1")


def test_get_unknown_raises():
    s = EyeAnimationSystem()
    with pytest.raises(KeyError):
        s.get("phantom")


def test_has_returns_bool():
    s = EyeAnimationSystem()
    s.register_eyes("a")
    assert s.has("a")
    assert not s.has("b")


# ---- look-at ----

def test_set_look_target_records_id():
    s = EyeAnimationSystem()
    s.register_eyes("npc_1")
    s.set_look_target("npc_1", "player")
    assert s.is_currently_looking_at("npc_1", "player")


def test_set_look_target_resets_hold():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.set_look_target("n", "p1")
    s.update("n", 0.5, scene_lux=1000, mood=Mood.CALM)
    assert s.get("n").contact_hold_s > 0
    s.set_look_target("n", "p2")
    assert s.get("n").contact_hold_s == 0


def test_release_target_clears():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.set_look_target("n", "p")
    s.release_target("n")
    assert s.get("n").look_at_target_id is None


def test_dart_away_after_max_hold():
    s = EyeAnimationSystem(
        contact_hold_min_s=0.1,
        contact_hold_max_s=0.5,
    )
    s.register_eyes("n")
    s.set_look_target("n", "p")
    # Step past the max hold.
    s.update("n", 0.6, scene_lux=1000, mood=Mood.CALM)
    assert s.get("n").look_at_target_id is None


def test_npcs_engaging_with_lists_all():
    s = EyeAnimationSystem()
    for name in ("a", "b", "c"):
        s.register_eyes(name)
    s.set_look_target("a", "player")
    s.set_look_target("c", "player")
    s.set_look_target("b", "vendor")
    assert s.npcs_engaging_with("player") == ("a", "c")


# ---- engagement range ----

def test_in_engagement_range_close():
    s = EyeAnimationSystem(engagement_radius_m=6.0)
    assert s.in_engagement_range(
        (0, 0, 0), (3, 0, 0),
    )


def test_in_engagement_range_far():
    s = EyeAnimationSystem(engagement_radius_m=6.0)
    assert not s.in_engagement_range(
        (0, 0, 0), (10, 0, 0),
    )


# ---- blink ----

def test_blink_advances_phase_calm():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.get("n").blink_phase = 0.5
    s.update("n", 0.05, scene_lux=1000, mood=Mood.CALM)
    # Phase moved forward.
    assert s.get("n").blink_phase != 0.5


def test_blink_dead_holds_open():
    s = EyeAnimationSystem()
    s.register_eyes("npc_dead")
    s.update(
        "npc_dead", 1.0, scene_lux=1000, mood=Mood.DEAD,
    )
    # Dead eyes hold mid-open.
    assert s.get("npc_dead").blink_phase == 0.5


def test_blink_now_resets_phase():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.blink_now("n")
    assert s.get("n").blink_phase == 0.0


def test_is_blinking_after_blink_now():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.blink_now("n")
    assert s.is_blinking("n")


def test_is_eye_closed_during_closed_phase():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.get("n").blink_phase = 0.07
    assert s.is_eye_closed("n")


def test_is_eye_closed_when_open():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.get("n").blink_phase = 0.5
    assert not s.is_eye_closed("n")


# ---- pupil ----

def test_pupil_constricts_in_bright_light():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.update("n", 0.05, scene_lux=80_000, mood=Mood.CALM)
    assert s.get("n").pupil_diameter_mm <= 3.0


def test_pupil_dilates_in_dim_cave():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.update("n", 0.05, scene_lux=2.0, mood=Mood.CALM)
    assert s.get("n").pupil_diameter_mm >= 6.0


def test_pupil_anxious_dilates_extra():
    s = EyeAnimationSystem()
    s.register_eyes("n_calm")
    s.register_eyes("n_anx")
    s.update(
        "n_calm", 0.05, scene_lux=1000, mood=Mood.CALM,
    )
    s.update(
        "n_anx", 0.05, scene_lux=1000, mood=Mood.ANXIOUS,
    )
    assert (
        s.get("n_anx").pupil_diameter_mm
        >= s.get("n_calm").pupil_diameter_mm
    )


# ---- microsaccades ----

def test_microsaccade_amplitude_in_range():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.update("n", 0.05, scene_lux=1000, mood=Mood.CALM)
    amp = s.get("n").microsaccade_amplitude_deg
    assert 0.1 <= amp <= 1.0


def test_microsaccade_velocity_positive():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.update("n", 0.05, scene_lux=1000, mood=Mood.CALM)
    assert s.get("n").saccade_velocity_dps > 0


def test_microsaccade_zero_when_dead():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.update("n", 0.05, scene_lux=1000, mood=Mood.DEAD)
    assert s.get("n").microsaccade_amplitude_deg == 0.0


def test_microsaccade_zero_when_sleeping():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.set_sleeping("n", True)
    s.update("n", 0.05, scene_lux=1000, mood=Mood.CALM)
    assert s.get("n").microsaccade_amplitude_deg == 0.0


# ---- tears ----

def test_tear_amount_grows_with_weary_intent():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    for _ in range(20):
        s.update(
            "n", 0.1, scene_lux=1000, mood=Mood.CALM,
            intent_tag="WEARY",
        )
    assert s.tear_amount("n") > 0.0


def test_tear_amount_decays_when_neutral():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    s.get("n").tear_amount = 0.8
    for _ in range(20):
        s.update(
            "n", 0.1, scene_lux=1000, mood=Mood.CALM,
            intent_tag="NEUTRAL",
        )
    assert s.tear_amount("n") < 0.5


def test_tear_amount_clamped_to_one():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    for _ in range(200):
        s.update(
            "n", 0.5, scene_lux=1000, mood=Mood.CALM,
            intent_tag="AFRAID",
        )
    assert s.tear_amount("n") <= 1.0


def test_tear_amount_clamped_to_zero():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    for _ in range(200):
        s.update(
            "n", 0.5, scene_lux=1000, mood=Mood.CALM,
            intent_tag="HAPPY",
        )
    assert s.tear_amount("n") >= 0.0


def test_tender_intent_also_triggers_tears():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    for _ in range(10):
        s.update(
            "n", 0.1, scene_lux=1000, mood=Mood.CALM,
            intent_tag="TENDER",
        )
    assert s.tear_amount("n") > 0.0


# ---- error paths ----

def test_update_zero_dt_raises():
    s = EyeAnimationSystem()
    s.register_eyes("n")
    with pytest.raises(ValueError):
        s.update("n", 0.0, scene_lux=1000, mood=Mood.CALM)


def test_update_unknown_npc_raises():
    s = EyeAnimationSystem()
    with pytest.raises(KeyError):
        s.update(
            "ghost", 0.1, scene_lux=1000, mood=Mood.CALM,
        )


def test_all_npcs_lists_sorted():
    s = EyeAnimationSystem()
    for name in ("c", "a", "b"):
        s.register_eyes(name)
    assert s.all_npcs() == ("a", "b", "c")
