"""Tests for the popout menu animation."""
from __future__ import annotations

from server.popout_menu_animation import (
    AnimEasing,
    AnimPhase,
    PopoutMenuAnimation,
)


def test_open_panel():
    p = PopoutMenuAnimation()
    assert p.open(panel_id="quest_log")
    st = p.state_for("quest_log")
    assert st.phase == AnimPhase.OPENING


def test_open_already_open_rejected():
    p = PopoutMenuAnimation()
    p.open(panel_id="x")
    p.step(elapsed_seconds=10.0)
    assert not p.open(panel_id="x")


def test_step_advances_opening_to_open():
    p = PopoutMenuAnimation(open_duration=0.5)
    p.open(panel_id="x")
    p.step(elapsed_seconds=1.0)
    st = p.state_for("x")
    assert st.phase == AnimPhase.OPEN
    assert st.t_value == 1.0


def test_close_panel():
    p = PopoutMenuAnimation()
    p.open(panel_id="x")
    p.step(elapsed_seconds=10.0)
    assert p.close(panel_id="x")
    st = p.state_for("x")
    assert st.phase == AnimPhase.CLOSING


def test_close_hidden_returns_false():
    p = PopoutMenuAnimation()
    assert not p.close(panel_id="never_opened")


def test_step_closes_to_hidden():
    p = PopoutMenuAnimation(close_duration=0.5)
    p.open(panel_id="x")
    p.step(elapsed_seconds=10.0)
    p.close(panel_id="x")
    p.step(elapsed_seconds=1.0)
    st = p.state_for("x")
    assert st.phase == AnimPhase.HIDDEN
    assert st.blur_back_strength == 0.0


def test_blur_back_grows_in_open_phase():
    p = PopoutMenuAnimation(
        open_duration=0.1,
        blur_back_duration=0.2,
    )
    p.open(panel_id="x")
    # Step to OPEN
    p.step(elapsed_seconds=0.2)
    # Step further while open — blur grows
    p.step(elapsed_seconds=0.1)
    st = p.state_for("x")
    assert 0 < st.blur_back_strength <= 1.0


def test_blur_back_caps_at_one():
    p = PopoutMenuAnimation(
        open_duration=0.1,
        blur_back_duration=0.1,
    )
    p.open(panel_id="x")
    p.step(elapsed_seconds=0.5)
    p.step(elapsed_seconds=10.0)
    st = p.state_for("x")
    assert st.blur_back_strength == 1.0


def test_interact_hover():
    p = PopoutMenuAnimation()
    p.open(panel_id="x")
    p.step(elapsed_seconds=10.0)
    assert p.interact(panel_id="x", kind="hover")
    st = p.state_for("x")
    assert st.phase == AnimPhase.HOVERING


def test_interact_select():
    p = PopoutMenuAnimation()
    p.open(panel_id="x")
    p.step(elapsed_seconds=10.0)
    assert p.interact(panel_id="x", kind="select")
    st = p.state_for("x")
    assert st.phase == AnimPhase.SELECTING


def test_interact_unknown_kind_rejected():
    p = PopoutMenuAnimation()
    p.open(panel_id="x")
    p.step(elapsed_seconds=10.0)
    assert not p.interact(panel_id="x", kind="bogus")


def test_interact_on_closed_rejected():
    p = PopoutMenuAnimation()
    assert not p.interact(panel_id="x", kind="hover")


def test_hover_decays_back_to_open():
    p = PopoutMenuAnimation(
        open_duration=0.1,
        hover_duration=0.2,
    )
    p.open(panel_id="x")
    p.step(elapsed_seconds=0.5)
    p.interact(panel_id="x", kind="hover")
    p.step(elapsed_seconds=1.0)
    st = p.state_for("x")
    assert st.phase == AnimPhase.OPEN


def test_easing_propagated():
    p = PopoutMenuAnimation()
    p.open(
        panel_id="x", easing=AnimEasing.BOUNCE_OUT,
    )
    st = p.state_for("x")
    assert st.easing == AnimEasing.BOUNCE_OUT


def test_zero_step_no_advance():
    p = PopoutMenuAnimation()
    p.open(panel_id="x")
    moved = p.step(elapsed_seconds=0.0)
    assert moved == 0


def test_total_active_panels():
    p = PopoutMenuAnimation()
    p.open(panel_id="a")
    p.open(panel_id="b")
    p.open(panel_id="c")
    assert p.total_active_panels() == 3


def test_state_unknown_panel():
    p = PopoutMenuAnimation()
    assert p.state_for("ghost") is None


def test_t_value_progresses_during_opening():
    p = PopoutMenuAnimation(open_duration=1.0)
    p.open(panel_id="x")
    p.step(elapsed_seconds=0.5)
    st = p.state_for("x")
    assert 0 < st.t_value < 1.0


def test_close_during_opening_works():
    p = PopoutMenuAnimation()
    p.open(panel_id="x")
    # Cancel mid-open
    assert p.close(panel_id="x")
