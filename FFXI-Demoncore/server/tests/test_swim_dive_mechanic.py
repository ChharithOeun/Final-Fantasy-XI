"""Tests for swim_dive_mechanic."""
from __future__ import annotations

from server.swim_dive_mechanic import (
    ASCEND_BAND_THRESHOLD_YALMS,
    ClimbOut,
    DEFAULT_BREATH_SECONDS,
    DROWN_LETHAL_SECONDS,
    SwimDiveMechanic,
    SwimSessionStatus,
)


def test_start_session_happy():
    s = SwimDiveMechanic()
    assert s.start_session(
        player_id="alice", breath_seconds=60,
        starting_depth=2, now_seconds=10,
    ) is True


def test_blank_player_blocked():
    s = SwimDiveMechanic()
    assert s.start_session(
        player_id="", breath_seconds=60, now_seconds=10,
    ) is False


def test_dup_session_blocked():
    s = SwimDiveMechanic()
    s.start_session(player_id="alice", breath_seconds=60, now_seconds=10)
    assert s.start_session(
        player_id="alice", breath_seconds=60, now_seconds=20,
    ) is False


def test_water_walk_evacuates_immediately():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60,
        has_water_walk=True, now_seconds=10,
    )
    sess = s.session(player_id="alice")
    assert sess.status == SwimSessionStatus.EVACUATED


def test_tick_drains_breath():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60, now_seconds=0,
    )
    out = s.tick(player_id="alice", dt_seconds=10, now_seconds=10)
    assert out is not None
    assert out.breath_remaining == 50.0
    assert out.drowning_damage == 0


def test_swimming_skill_reduces_drain():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60,
        has_swimming_skill=True, now_seconds=0,
    )
    out = s.tick(player_id="alice", dt_seconds=10, now_seconds=10)
    # 25% less drain → 7.5/10s remaining = 60 - 7.5 = 52.5
    assert out.breath_remaining == 52.5


def test_drowning_starts_when_breath_zero():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=5, now_seconds=0,
    )
    s.tick(player_id="alice", dt_seconds=5, now_seconds=5)
    # now breath = 0, next tick should damage
    out = s.tick(player_id="alice", dt_seconds=2, now_seconds=7)
    assert out.breath_remaining == 0.0
    assert out.drowning_damage > 0


def test_drowning_lethal_after_threshold():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=1, now_seconds=0,
    )
    s.tick(player_id="alice", dt_seconds=1, now_seconds=1)
    out = s.tick(
        player_id="alice", dt_seconds=DROWN_LETHAL_SECONDS,
        now_seconds=1 + DROWN_LETHAL_SECONDS,
    )
    assert out.status == SwimSessionStatus.DROWNED


def test_ascend_decreases_depth():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60,
        starting_depth=3, now_seconds=0,
    )
    s.ascend(player_id="alice", yalms=ASCEND_BAND_THRESHOLD_YALMS)
    sess = s.session(player_id="alice")
    assert sess.current_depth_band == 2


def test_ascend_below_zero_clamped():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60,
        starting_depth=1, now_seconds=0,
    )
    s.ascend(player_id="alice", yalms=ASCEND_BAND_THRESHOLD_YALMS * 5)
    sess = s.session(player_id="alice")
    assert sess.current_depth_band == 0


def test_descend_increments_band():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60,
        starting_depth=1, now_seconds=0,
    )
    s.descend(player_id="alice", yalms=10)
    sess = s.session(player_id="alice")
    assert sess.current_depth_band == 2


def test_grasp_climb_out_surfaces():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60,
        starting_depth=1,
        climb_outs=[ClimbOut(
            climb_out_id="ice_hole", band_at_top=0,
            requires_band=1, label="broken ice",
        )],
        now_seconds=0,
    )
    out = s.grasp_climb_out(
        player_id="alice", climb_out_id="ice_hole",
    )
    assert out.accepted is True
    assert out.surfaced is True
    assert out.new_band == 0


def test_climb_out_too_deep_rejected():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60,
        starting_depth=3,
        climb_outs=[ClimbOut(
            climb_out_id="ice_hole", band_at_top=0,
            requires_band=1,
        )],
        now_seconds=0,
    )
    out = s.grasp_climb_out(
        player_id="alice", climb_out_id="ice_hole",
    )
    assert out.accepted is False


def test_unknown_climb_out_rejected():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60, starting_depth=1,
        now_seconds=0,
    )
    out = s.grasp_climb_out(
        player_id="alice", climb_out_id="ghost",
    )
    assert out.accepted is False


def test_end_session_drops_record():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60, now_seconds=0,
    )
    s.end_session(player_id="alice")
    assert s.session(player_id="alice") is None


def test_tick_unknown_returns_none():
    s = SwimDiveMechanic()
    assert s.tick(
        player_id="ghost", dt_seconds=1, now_seconds=0,
    ) is None


def test_default_breath_constant():
    assert DEFAULT_BREATH_SECONDS == 60


def test_zero_dt_no_drain():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60, now_seconds=0,
    )
    out = s.tick(player_id="alice", dt_seconds=0, now_seconds=5)
    assert out.breath_remaining == 60.0


def test_evacuated_session_doesnt_tick():
    s = SwimDiveMechanic()
    s.start_session(
        player_id="alice", breath_seconds=60,
        has_water_walk=True, now_seconds=0,
    )
    out = s.tick(player_id="alice", dt_seconds=10, now_seconds=10)
    assert out is None
