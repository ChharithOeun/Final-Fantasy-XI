"""Tests for combat_camera_director."""
from __future__ import annotations

import pytest

from server.combat_camera_director import (
    CombatCameraDirector,
    CombatCameraEvent,
    CombatShot,
    DirectorContext,
    DirectorState,
    FocusPriority,
)


def _shot(
    kind="push_in",
    duration=1.5,
    lens=50.0,
    focus=FocusPriority.PLAYER,
    handback=True,
    pri=5,
):
    return CombatShot(
        shot_kind=kind,
        duration_s=duration,
        lens_mm_hint=lens,
        focus_target_priority=focus,
        hand_back_to_player_rig_after=handback,
        interrupt_priority=pri,
    )


def _ctx(rig="r1", target="m1"):
    return DirectorContext(
        player_id="p1", rig_id=rig, target_id=target,
    )


# ---- enums ----

def test_event_count_at_least_eleven():
    assert len(list(CombatCameraEvent)) >= 11


def test_director_state_count_four():
    assert len(list(DirectorState)) == 4


def test_focus_priority_four():
    assert len(list(FocusPriority)) == 4


def test_event_has_boss_intro():
    assert CombatCameraEvent.BOSS_INTRO in list(
        CombatCameraEvent,
    )


def test_event_has_skillchain_open():
    assert CombatCameraEvent.SKILLCHAIN_OPEN in list(
        CombatCameraEvent,
    )


# ---- handler register ----

def test_register_handler():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.ENGAGE_START, _shot(),
    )
    assert d.handler_count() == 1


def test_register_handler_invalid_duration_raises():
    d = CombatCameraDirector()
    with pytest.raises(ValueError):
        d.register_event_handler(
            CombatCameraEvent.ENGAGE_START,
            _shot(duration=0),
        )


def test_register_handler_invalid_lens_raises():
    d = CombatCameraDirector()
    with pytest.raises(ValueError):
        d.register_event_handler(
            CombatCameraEvent.ENGAGE_START,
            _shot(lens=0),
        )


def test_register_handler_invalid_priority_raises():
    d = CombatCameraDirector()
    with pytest.raises(ValueError):
        d.register_event_handler(
            CombatCameraEvent.ENGAGE_START,
            _shot(pri=11),
        )


def test_register_handler_empty_kind_raises():
    d = CombatCameraDirector()
    with pytest.raises(ValueError):
        d.register_event_handler(
            CombatCameraEvent.ENGAGE_START,
            _shot(kind=""),
        )


def test_handler_for_returns_registered():
    d = CombatCameraDirector()
    s = _shot()
    d.register_event_handler(
        CombatCameraEvent.ENGAGE_START, s,
    )
    assert d.handler_for(
        CombatCameraEvent.ENGAGE_START,
    ) == s


def test_handler_for_unregistered_returns_none():
    d = CombatCameraDirector()
    assert d.handler_for(
        CombatCameraEvent.ENGAGE_START,
    ) is None


# ---- defaults ----

def test_populate_defaults_at_least_eleven():
    d = CombatCameraDirector()
    n = d.populate_defaults()
    assert n >= 11


def test_default_boss_intro_is_priority_ten():
    d = CombatCameraDirector()
    d.populate_defaults()
    s = d.handler_for(CombatCameraEvent.BOSS_INTRO)
    assert s.interrupt_priority == 10


def test_default_engage_start_short_duration():
    d = CombatCameraDirector()
    d.populate_defaults()
    s = d.handler_for(CombatCameraEvent.ENGAGE_START)
    assert s.duration_s < 2.0


def test_default_player_down_no_handback():
    d = CombatCameraDirector()
    d.populate_defaults()
    s = d.handler_for(CombatCameraEvent.PLAYER_DOWN)
    assert s.hand_back_to_player_rig_after is False


# ---- trigger ----

def test_trigger_no_handler_returns_none():
    d = CombatCameraDirector()
    assert d.trigger(
        CombatCameraEvent.ENGAGE_START, _ctx(),
    ) is None


def test_trigger_starts_setpiece():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.ENGAGE_START, _shot(),
    )
    s = d.trigger(CombatCameraEvent.ENGAGE_START, _ctx())
    assert s is not None
    assert d.current_setpiece("r1") is not None
    assert d.state_for("r1") == DirectorState.CINEMATIC_SETPIECE


def test_higher_priority_interrupts_lower():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.ENGAGE_START, _shot(pri=2),
    )
    d.register_event_handler(
        CombatCameraEvent.BOSS_INTRO, _shot(
            kind="boss", pri=10, duration=4.0,
        ),
    )
    d.trigger(CombatCameraEvent.ENGAGE_START, _ctx())
    s = d.trigger(CombatCameraEvent.BOSS_INTRO, _ctx())
    assert s is not None
    assert d.current_event("r1") == CombatCameraEvent.BOSS_INTRO


def test_lower_priority_queues():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.BOSS_INTRO, _shot(pri=10),
    )
    d.register_event_handler(
        CombatCameraEvent.CRITICAL_HIT, _shot(pri=3),
    )
    d.trigger(CombatCameraEvent.BOSS_INTRO, _ctx())
    s = d.trigger(CombatCameraEvent.CRITICAL_HIT, _ctx())
    assert s is None
    assert d.queued_count("r1") == 1


def test_queue_empty_after_consume():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.BOSS_INTRO, _shot(pri=10),
    )
    d.register_event_handler(
        CombatCameraEvent.CRITICAL_HIT, _shot(pri=3),
    )
    d.trigger(CombatCameraEvent.BOSS_INTRO, _ctx())
    d.trigger(CombatCameraEvent.CRITICAL_HIT, _ctx())
    d.ends_setpiece("r1")
    assert d.queued_count("r1") == 0
    assert d.current_event("r1") == CombatCameraEvent.CRITICAL_HIT


def test_ends_setpiece_with_no_queue_returns_none():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.ENGAGE_START, _shot(),
    )
    d.trigger(CombatCameraEvent.ENGAGE_START, _ctx())
    assert d.ends_setpiece("r1") is None
    assert d.state_for("r1") == DirectorState.BACK_TO_NORMAL


def test_ends_setpiece_unknown_rig_returns_none():
    d = CombatCameraDirector()
    assert d.ends_setpiece("nope") is None


def test_interrupt_with_alias_for_trigger():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.BOSS_INTRO, _shot(pri=10),
    )
    s = d.interrupt_with(CombatCameraEvent.BOSS_INTRO, _ctx())
    assert s is not None


# ---- tick ----

def test_tick_advances_elapsed():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.ENGAGE_START,
        _shot(duration=1.0),
    )
    d.trigger(CombatCameraEvent.ENGAGE_START, _ctx())
    s = d.tick("r1", 0.5)
    assert s is not None  # not yet ended


def test_tick_ends_setpiece_when_duration_elapsed():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.ENGAGE_START,
        _shot(duration=1.0),
    )
    d.trigger(CombatCameraEvent.ENGAGE_START, _ctx())
    s = d.tick("r1", 1.5)
    assert s is None
    assert d.state_for("r1") == DirectorState.BACK_TO_NORMAL


def test_tick_negative_dt_raises():
    d = CombatCameraDirector()
    with pytest.raises(ValueError):
        d.tick("r1", -1.0)


def test_tick_no_setpiece_returns_none():
    d = CombatCameraDirector()
    assert d.tick("r1", 0.1) is None


# ---- state ----

def test_state_default_normal():
    d = CombatCameraDirector()
    assert d.state_for("r1") == DirectorState.NORMAL


def test_transition_to_returns_prev():
    d = CombatCameraDirector()
    prev = d.transition_to("r1", DirectorState.COMBAT_AUTO)
    assert prev == DirectorState.NORMAL
    assert d.state_for("r1") == DirectorState.COMBAT_AUTO


# ---- Murch six-axis ----

def test_should_cut_boss_intro_score_above_threshold():
    d = CombatCameraDirector()
    assert d.should_cut_for(
        CombatCameraEvent.BOSS_INTRO,
        time_since_last_cut_s=2.0,
    )


def test_should_not_cut_engage_end_below_threshold():
    d = CombatCameraDirector()
    assert not d.should_cut_for(
        CombatCameraEvent.ENGAGE_END,
        time_since_last_cut_s=2.0,
    )


def test_should_not_cut_too_soon_after_last_cut():
    d = CombatCameraDirector()
    assert not d.should_cut_for(
        CombatCameraEvent.BOSS_INTRO,
        time_since_last_cut_s=0.1,
    )


def test_dramatic_hold_raises_threshold():
    d = CombatCameraDirector()
    # CRITICAL_HIT scores 9 — below threshold either way.
    # Test with KILL_BLOW (sum=11) — below default 12 too.
    # Use SKILLCHAIN_OPEN which scores 12 — at threshold,
    # passes default but not when dramatic_hold
    assert d.should_cut_for(
        CombatCameraEvent.SKILLCHAIN_OPEN,
        time_since_last_cut_s=2.0,
    )
    assert not d.should_cut_for(
        CombatCameraEvent.SKILLCHAIN_OPEN,
        time_since_last_cut_s=2.0,
        scene_state={"dramatic_hold": True},
    )


def test_murch_score_lookup():
    d = CombatCameraDirector()
    assert d.murch_score(CombatCameraEvent.BOSS_INTRO) == 18
    assert d.murch_score(CombatCameraEvent.ENGAGE_END) == 6


# ---- priority defaults ----

def test_default_priority_boss_intro_ten():
    d = CombatCameraDirector()
    assert d.default_priority_for(
        CombatCameraEvent.BOSS_INTRO,
    ) == 10


def test_default_priority_engage_end_one():
    d = CombatCameraDirector()
    assert d.default_priority_for(
        CombatCameraEvent.ENGAGE_END,
    ) == 1


# ---- shot data ----

def test_shot_dataclass_immutable():
    import dataclasses
    s = _shot()
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.duration_s = 2.0  # type: ignore[misc]


def test_focus_main_target_in_skillchain_default():
    d = CombatCameraDirector()
    d.populate_defaults()
    s = d.handler_for(CombatCameraEvent.SKILLCHAIN_OPEN)
    assert s.focus_target_priority == FocusPriority.MAIN_TARGET


def test_default_kill_blow_finishing():
    d = CombatCameraDirector()
    d.populate_defaults()
    s = d.handler_for(CombatCameraEvent.KILL_BLOW)
    assert "finishing" in s.shot_kind


# ---- multiple rigs ----

def test_setpiece_per_rig_independent():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.ENGAGE_START, _shot(),
    )
    d.trigger(
        CombatCameraEvent.ENGAGE_START,
        DirectorContext(
            player_id="p1", rig_id="r1", target_id="m1",
        ),
    )
    assert d.current_setpiece("r1") is not None
    assert d.current_setpiece("r2") is None


def test_two_rigs_independent_states():
    d = CombatCameraDirector()
    d.register_event_handler(
        CombatCameraEvent.BOSS_INTRO, _shot(pri=10),
    )
    d.trigger(
        CombatCameraEvent.BOSS_INTRO,
        DirectorContext(
            player_id="p1", rig_id="r1", target_id="b",
        ),
    )
    assert d.state_for("r1") == DirectorState.CINEMATIC_SETPIECE
    assert d.state_for("r2") == DirectorState.NORMAL
