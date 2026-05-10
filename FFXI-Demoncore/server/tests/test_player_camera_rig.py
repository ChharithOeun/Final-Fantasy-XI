"""Tests for player_camera_rig."""
from __future__ import annotations

import pytest

from server.player_camera_rig import (
    CameraMode,
    CameraRig,
    PlayerCameraRigSystem,
    PlayerStateView,
)


def _make_rig(
    rig_id="r1",
    mode=CameraMode.THIRD_PERSON_FAR,
    fov=90.0,
    dist=8.0,
    height=1.6,
    lerp=0.1,
    smoothing=0.3,
    radius=0.25,
    target="",
):
    return CameraRig(
        rig_id=rig_id,
        current_mode=mode,
        fov_deg=fov,
        distance_m_from_target=dist,
        height_offset_m=height,
        lerp_speed_s=lerp,
        smoothing=smoothing,
        collision_radius_m=radius,
        target_npc_id=target,
    )


# ---- enum coverage ----

def test_camera_mode_count_at_least_ten():
    assert len(list(CameraMode)) >= 10


def test_camera_mode_has_first_person():
    assert CameraMode.FIRST_PERSON in list(CameraMode)


def test_camera_mode_has_chocobo_ride():
    assert CameraMode.CHOCOBO_RIDE in list(CameraMode)


def test_camera_mode_has_ko_orbit():
    assert CameraMode.KO_ORBIT in list(CameraMode)


# ---- register ----

def test_register_rig():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    assert s.rig_count() == 1
    assert s.get_rig("r1").rig_id == "r1"


def test_register_empty_id_raises():
    s = PlayerCameraRigSystem()
    with pytest.raises(ValueError):
        s.register_rig(_make_rig(rig_id=""))


def test_register_duplicate_raises():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    with pytest.raises(ValueError):
        s.register_rig(_make_rig())


def test_register_invalid_fov_high_raises():
    s = PlayerCameraRigSystem()
    with pytest.raises(ValueError):
        s.register_rig(_make_rig(fov=200.0))


def test_register_invalid_fov_zero_raises():
    s = PlayerCameraRigSystem()
    with pytest.raises(ValueError):
        s.register_rig(_make_rig(fov=0))


def test_register_negative_distance_raises():
    s = PlayerCameraRigSystem()
    with pytest.raises(ValueError):
        s.register_rig(_make_rig(dist=-1))


def test_register_negative_radius_raises():
    s = PlayerCameraRigSystem()
    with pytest.raises(ValueError):
        s.register_rig(_make_rig(radius=-0.1))


def test_register_smoothing_out_of_range_raises():
    s = PlayerCameraRigSystem()
    with pytest.raises(ValueError):
        s.register_rig(_make_rig(smoothing=1.5))


def test_get_rig_missing_raises():
    s = PlayerCameraRigSystem()
    with pytest.raises(KeyError):
        s.get_rig("missing")


# ---- fov_for ----

def test_fov_for_over_shoulder_tight_is_60():
    s = PlayerCameraRigSystem()
    assert s.fov_for(CameraMode.OVER_SHOULDER_TIGHT) == 60.0


def test_fov_for_over_shoulder_wide_is_75():
    s = PlayerCameraRigSystem()
    assert s.fov_for(CameraMode.OVER_SHOULDER_WIDE) == 75.0


def test_fov_for_third_person_far_is_90():
    s = PlayerCameraRigSystem()
    assert s.fov_for(CameraMode.THIRD_PERSON_FAR) == 90.0


def test_fov_for_first_person_is_90():
    s = PlayerCameraRigSystem()
    assert s.fov_for(CameraMode.FIRST_PERSON) == 90.0


# ---- transitions ----

def test_allowed_third_to_over_shoulder_tight():
    s = PlayerCameraRigSystem()
    assert s.allowed_transition(
        CameraMode.THIRD_PERSON_FAR,
        CameraMode.OVER_SHOULDER_TIGHT,
    )


def test_allowed_first_to_third_toggle():
    s = PlayerCameraRigSystem()
    assert s.allowed_transition(
        CameraMode.FIRST_PERSON, CameraMode.THIRD_PERSON_FAR,
    )
    assert s.allowed_transition(
        CameraMode.THIRD_PERSON_FAR, CameraMode.FIRST_PERSON,
    )


def test_any_to_cinematic_allowed():
    s = PlayerCameraRigSystem()
    for mode in CameraMode:
        assert s.allowed_transition(
            mode, CameraMode.CINEMATIC_TRACK,
        )


def test_any_to_ko_orbit_allowed():
    s = PlayerCameraRigSystem()
    for mode in CameraMode:
        assert s.allowed_transition(
            mode, CameraMode.KO_ORBIT,
        )


def test_self_transition_is_allowed():
    s = PlayerCameraRigSystem()
    assert s.allowed_transition(
        CameraMode.FIRST_PERSON, CameraMode.FIRST_PERSON,
    )


def test_disallowed_first_person_to_chocobo():
    s = PlayerCameraRigSystem()
    assert not s.allowed_transition(
        CameraMode.FIRST_PERSON, CameraMode.CHOCOBO_RIDE,
    )


# ---- set_mode ----

def test_set_mode_changes_mode():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    rig = s.set_mode(
        "r1", CameraMode.OVER_SHOULDER_TIGHT,
        transition_s=0.4,
    )
    assert rig.current_mode == CameraMode.OVER_SHOULDER_TIGHT
    assert rig.fov_deg == 60.0


def test_set_mode_disallowed_raises():
    s = PlayerCameraRigSystem()
    rig = _make_rig(mode=CameraMode.FIRST_PERSON, fov=90.0)
    s.register_rig(rig)
    with pytest.raises(ValueError):
        s.set_mode("r1", CameraMode.CHOCOBO_RIDE)


def test_set_mode_negative_transition_raises():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    with pytest.raises(ValueError):
        s.set_mode(
            "r1", CameraMode.OVER_SHOULDER_TIGHT,
            transition_s=-0.1,
        )


def test_set_mode_unknown_rig_raises():
    s = PlayerCameraRigSystem()
    with pytest.raises(KeyError):
        s.set_mode("missing", CameraMode.FIRST_PERSON)


# ---- engage_zoom ----

def test_engage_zoom_from_far_to_tight():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig(mode=CameraMode.THIRD_PERSON_FAR))
    rig = s.engage_zoom("r1")
    assert rig.current_mode == CameraMode.OVER_SHOULDER_TIGHT
    assert rig.fov_deg == 60.0


def test_engage_zoom_no_op_if_not_far():
    s = PlayerCameraRigSystem()
    rig0 = _make_rig(
        mode=CameraMode.OVER_SHOULDER_WIDE, fov=75.0,
        dist=2.4,
    )
    s.register_rig(rig0)
    rig = s.engage_zoom("r1")
    assert rig.current_mode == CameraMode.OVER_SHOULDER_WIDE


def test_disengage_pullout_returns_to_far():
    s = PlayerCameraRigSystem()
    rig0 = _make_rig(
        mode=CameraMode.OVER_SHOULDER_TIGHT, fov=60.0,
        dist=1.6,
    )
    s.register_rig(rig0)
    rig = s.disengage_pullout("r1")
    assert rig.current_mode == CameraMode.THIRD_PERSON_FAR


# ---- collision ----

def test_apply_collision_clamps_distance():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig(dist=8.0, radius=0.5))
    rig = s.apply_collision("r1", clipping_distance_m=3.0)
    assert rig.distance_m_from_target == pytest.approx(2.5)


def test_apply_collision_no_clamp_if_clear():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig(dist=4.0, radius=0.25))
    rig = s.apply_collision("r1", clipping_distance_m=20.0)
    assert rig.distance_m_from_target == pytest.approx(4.0)


def test_apply_collision_negative_raises():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    with pytest.raises(ValueError):
        s.apply_collision("r1", clipping_distance_m=-1.0)


def test_apply_collision_zero_pulls_to_zero():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig(dist=8.0, radius=0.25))
    rig = s.apply_collision("r1", clipping_distance_m=0.0)
    assert rig.distance_m_from_target == 0.0


# ---- director handoff ----

def test_handoff_marks_director_owned():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    rig = s.handoff_to_director("r1", "boss_intro_pull")
    assert rig.current_mode == CameraMode.CINEMATIC_TRACK
    assert s.is_director_owned("r1")
    assert s.director_shot("r1") == "boss_intro_pull"


def test_handoff_empty_kind_raises():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    with pytest.raises(ValueError):
        s.handoff_to_director("r1", "")


def test_handoff_double_raises():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    s.handoff_to_director("r1", "x")
    with pytest.raises(ValueError):
        s.handoff_to_director("r1", "y")


def test_reclaim_restores_prev_mode():
    s = PlayerCameraRigSystem()
    rig0 = _make_rig(mode=CameraMode.OVER_SHOULDER_TIGHT)
    s.register_rig(rig0)
    s.handoff_to_director("r1", "shot1")
    rig = s.reclaim_from_director("r1")
    assert rig.current_mode == CameraMode.OVER_SHOULDER_TIGHT
    assert not s.is_director_owned("r1")


def test_reclaim_without_handoff_raises():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    with pytest.raises(ValueError):
        s.reclaim_from_director("r1")


# ---- interpolated pose ----

def test_interpolated_pose_at_zero_uses_from_mode():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig(mode=CameraMode.THIRD_PERSON_FAR))
    s.set_mode(
        "r1", CameraMode.OVER_SHOULDER_TIGHT,
        transition_s=0.4,
    )
    mode, fov, dist = s.interpolated_pose_at("r1", 0.0)
    # fov starts near THIRD_PERSON_FAR (90) at t=0
    assert fov == pytest.approx(90.0)
    assert dist == pytest.approx(8.0)


def test_interpolated_pose_at_one_uses_to_mode():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    s.set_mode(
        "r1", CameraMode.OVER_SHOULDER_TIGHT,
        transition_s=0.4,
    )
    mode, fov, dist = s.interpolated_pose_at("r1", 1.0)
    assert mode == CameraMode.OVER_SHOULDER_TIGHT
    assert fov == pytest.approx(60.0)
    assert dist == pytest.approx(1.6)


def test_interpolated_pose_midway():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    s.set_mode(
        "r1", CameraMode.OVER_SHOULDER_TIGHT,
        transition_s=0.4,
    )
    mode, fov, dist = s.interpolated_pose_at("r1", 0.5)
    assert fov == pytest.approx(75.0)


def test_interpolated_pose_clamps_t():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    s.set_mode(
        "r1", CameraMode.OVER_SHOULDER_TIGHT,
        transition_s=0.4,
    )
    mode, fov, _ = s.interpolated_pose_at("r1", 5.0)
    assert fov == pytest.approx(60.0)


def test_tick_transition_advances_t():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    s.set_mode(
        "r1", CameraMode.OVER_SHOULDER_TIGHT,
        transition_s=0.4,
    )
    t1 = s.tick_transition("r1", 0.2)
    assert t1 == pytest.approx(0.5)


def test_tick_transition_no_dur_returns_one():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    s.set_mode("r1", CameraMode.OVER_SHOULDER_TIGHT)
    assert s.tick_transition("r1", 0.5) == 1.0


# ---- suggested_mode_for ----

def test_suggested_idle_is_third_far():
    s = PlayerCameraRigSystem()
    assert s.suggested_mode_for(
        PlayerStateView()
    ) == CameraMode.THIRD_PERSON_FAR


def test_suggested_engaged_is_over_shoulder_tight():
    s = PlayerCameraRigSystem()
    assert s.suggested_mode_for(
        PlayerStateView(engaged=True),
    ) == CameraMode.OVER_SHOULDER_TIGHT


def test_suggested_chocobo_overrides_engage():
    s = PlayerCameraRigSystem()
    assert s.suggested_mode_for(
        PlayerStateView(on_chocobo=True),
    ) == CameraMode.CHOCOBO_RIDE


def test_suggested_swimming():
    s = PlayerCameraRigSystem()
    assert s.suggested_mode_for(
        PlayerStateView(swimming=True),
    ) == CameraMode.SWIMMING_UNDERWATER


def test_suggested_ledge():
    s = PlayerCameraRigSystem()
    assert s.suggested_mode_for(
        PlayerStateView(on_ledge=True),
    ) == CameraMode.LEDGE_HANG


def test_suggested_ko_priority():
    s = PlayerCameraRigSystem()
    assert s.suggested_mode_for(
        PlayerStateView(
            ko_state=True, engaged=True, swimming=True,
        ),
    ) == CameraMode.KO_ORBIT


def test_suggested_cutscene_overrides_all():
    s = PlayerCameraRigSystem()
    assert s.suggested_mode_for(
        PlayerStateView(
            in_cutscene=True, ko_state=True,
        ),
    ) == CameraMode.CINEMATIC_TRACK


# ---- reset ----

def test_reset_to_default_clears_director():
    s = PlayerCameraRigSystem()
    s.register_rig(_make_rig())
    s.handoff_to_director("r1", "x")
    rig = s.reset_to_default("r1")
    assert rig.current_mode == CameraMode.THIRD_PERSON_FAR
    assert not s.is_director_owned("r1")


def test_default_distance_for_modes():
    s = PlayerCameraRigSystem()
    assert s.default_distance_for(
        CameraMode.FIRST_PERSON,
    ) == 0.0
    assert s.default_distance_for(
        CameraMode.THIRD_PERSON_FAR,
    ) == 8.0
