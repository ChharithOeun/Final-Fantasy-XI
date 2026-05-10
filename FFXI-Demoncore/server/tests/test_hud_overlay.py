"""Tests for hud_overlay."""
from __future__ import annotations

import pytest

from server.hud_overlay import (
    HudDensity,
    HudElement,
    HudElementSpec,
    HudMode,
    HudOverlaySystem,
)


def _spec(
    element=HudElement.HEALTH_GAUGE,
    target=1.0,
    current=1.0,
    fade=0.25,
    modes=(HudMode.COMBAT, HudMode.EXPLORATION),
    hidden=0.0,
):
    return HudElementSpec(
        element=element,
        opacity_target=target,
        opacity_current=current,
        fade_speed_s=fade,
        visible_in_modes=modes,
        opacity_when_not_visible=hidden,
    )


# ---- enum coverage ----

def test_hud_element_count_at_least_eighteen():
    assert len(list(HudElement)) >= 18


def test_hud_mode_count_six():
    assert len(list(HudMode)) == 6


def test_hud_density_count_three():
    assert len(list(HudDensity)) == 3


def test_hud_element_has_casting_bar():
    assert HudElement.CASTING_BAR in list(HudElement)


def test_hud_element_has_party_frame():
    assert HudElement.PARTY_FRAME in list(HudElement)


def test_hud_element_has_chat_window():
    assert HudElement.CHAT_WINDOW in list(HudElement)


def test_hud_element_has_action_bar():
    assert HudElement.ACTION_BAR in list(HudElement)


# ---- register ----

def test_register_element():
    s = HudOverlaySystem()
    s.register_element(_spec())
    assert s.element_count() == 1


def test_register_duplicate_raises():
    s = HudOverlaySystem()
    s.register_element(_spec())
    with pytest.raises(ValueError):
        s.register_element(_spec())


def test_register_invalid_target_high_raises():
    s = HudOverlaySystem()
    with pytest.raises(ValueError):
        s.register_element(_spec(target=1.5))


def test_register_invalid_current_low_raises():
    s = HudOverlaySystem()
    with pytest.raises(ValueError):
        s.register_element(_spec(current=-0.1))


def test_register_negative_fade_raises():
    s = HudOverlaySystem()
    with pytest.raises(ValueError):
        s.register_element(_spec(fade=-1))


def test_register_invalid_hidden_raises():
    s = HudOverlaySystem()
    with pytest.raises(ValueError):
        s.register_element(_spec(hidden=1.5))


def test_opacity_for_unknown_raises():
    s = HudOverlaySystem()
    with pytest.raises(KeyError):
        s.opacity_for(HudElement.HEALTH_GAUGE)


# ---- defaults ----

def test_populate_defaults_at_least_eighteen():
    s = HudOverlaySystem()
    n = s.populate_defaults()
    assert n >= 18


def test_default_health_visible_in_combat():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert s.is_visible_in(
        HudElement.HEALTH_GAUGE, HudMode.COMBAT,
    )


def test_default_health_ghosted_in_exploration():
    s = HudOverlaySystem()
    s.populate_defaults()
    target = s.opacity_for(
        HudElement.HEALTH_GAUGE, HudMode.EXPLORATION,
    )
    # STANDARD density (0.7) * 0.4 ghost = 0.28
    assert target == pytest.approx(0.28)


def test_default_target_frame_hidden_in_exploration():
    s = HudOverlaySystem()
    s.populate_defaults()
    target = s.opacity_for(
        HudElement.TARGET_FRAME, HudMode.EXPLORATION,
    )
    assert target == 0.0


def test_default_casting_bar_visible_in_dialogue():
    s = HudOverlaySystem()
    s.populate_defaults()
    target = s.opacity_for(
        HudElement.CASTING_BAR, HudMode.DIALOGUE,
    )
    assert target > 0.0


def test_cinematic_hides_everything():
    s = HudOverlaySystem()
    s.populate_defaults()
    for elem in HudElement:
        target = s.opacity_for(elem, HudMode.CINEMATIC)
        assert target == 0.0


def test_default_chat_visible_in_dialogue():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert s.is_visible_in(
        HudElement.CHAT_WINDOW, HudMode.DIALOGUE,
    )


# ---- mode set ----

def test_set_mode_returns_previous():
    s = HudOverlaySystem()
    prev = s.set_mode(HudMode.COMBAT)
    assert prev == HudMode.EXPLORATION
    assert s.current_mode() == HudMode.COMBAT


def test_set_mode_updates_targets():
    s = HudOverlaySystem()
    s.populate_defaults()
    s.set_mode(HudMode.COMBAT)
    target = s.target_opacity(HudElement.TARGET_FRAME)
    assert target > 0.0


def test_set_mode_cinematic_zeroes_all_targets():
    s = HudOverlaySystem()
    s.populate_defaults()
    s.set_mode(HudMode.CINEMATIC)
    for elem in HudElement:
        assert s.target_opacity(elem) == 0.0


# ---- density ----

def test_density_minimal_multiplier():
    s = HudOverlaySystem()
    assert s.density_multiplier(
        HudDensity.MINIMAL,
    ) == pytest.approx(0.4)


def test_density_standard_multiplier():
    s = HudOverlaySystem()
    assert s.density_multiplier(
        HudDensity.STANDARD,
    ) == pytest.approx(0.7)


def test_density_dense_multiplier():
    s = HudOverlaySystem()
    assert s.density_multiplier(
        HudDensity.DENSE,
    ) == pytest.approx(1.0)


def test_set_density_persists():
    s = HudOverlaySystem()
    s.set_density(HudDensity.DENSE)
    assert s.density() == HudDensity.DENSE


def test_set_density_changes_targets():
    s = HudOverlaySystem()
    s.populate_defaults()
    s.set_mode(HudMode.COMBAT)
    s.set_density(HudDensity.MINIMAL)
    target = s.target_opacity(HudElement.HEALTH_GAUGE)
    # COMBAT nominal 1.0, MINIMAL multiplier 0.4
    assert target == pytest.approx(0.4)


def test_dense_combat_full_health():
    s = HudOverlaySystem()
    s.populate_defaults()
    s.set_density(HudDensity.DENSE)
    s.set_mode(HudMode.COMBAT)
    assert s.target_opacity(
        HudElement.HEALTH_GAUGE,
    ) == pytest.approx(1.0)


# ---- tick ----

def test_tick_eases_toward_target():
    s = HudOverlaySystem()
    s.register_element(_spec(target=1.0, current=0.0,
                             fade=1.0))
    s.tick(0.5)
    cur = s.current_opacity(HudElement.HEALTH_GAUGE)
    assert cur == pytest.approx(0.5)


def test_tick_fully_completes_when_step_exceeds_one():
    s = HudOverlaySystem()
    s.register_element(_spec(target=1.0, current=0.0,
                             fade=0.5))
    s.tick(1.0)
    cur = s.current_opacity(HudElement.HEALTH_GAUGE)
    assert cur == pytest.approx(1.0)


def test_tick_no_change_when_at_target():
    s = HudOverlaySystem()
    s.register_element(_spec(target=0.5, current=0.5,
                             fade=0.5))
    s.tick(0.1)
    assert s.current_opacity(
        HudElement.HEALTH_GAUGE,
    ) == pytest.approx(0.5)


def test_tick_zero_dt_no_op():
    s = HudOverlaySystem()
    s.register_element(_spec(target=1.0, current=0.0,
                             fade=1.0))
    s.tick(0.0)
    assert s.current_opacity(
        HudElement.HEALTH_GAUGE,
    ) == pytest.approx(0.0)


def test_tick_negative_raises():
    s = HudOverlaySystem()
    with pytest.raises(ValueError):
        s.tick(-0.1)


def test_tick_zero_fade_snaps_to_target():
    s = HudOverlaySystem()
    s.register_element(_spec(target=1.0, current=0.0,
                             fade=0.0))
    s.tick(0.1)
    assert s.current_opacity(
        HudElement.HEALTH_GAUGE,
    ) == pytest.approx(1.0)


# ---- should_render / hide_all ----

def test_should_render_true_for_visible_in_combat():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert s.should_render(
        HudElement.HEALTH_GAUGE, HudMode.COMBAT,
    )


def test_should_render_false_in_cinematic():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert not s.should_render(
        HudElement.HEALTH_GAUGE, HudMode.CINEMATIC,
    )


def test_hide_all_for_cinematic_zeroes_targets():
    s = HudOverlaySystem()
    s.populate_defaults()
    s.set_mode(HudMode.COMBAT)
    s.hide_all_for_cinematic()
    for elem in HudElement:
        assert s.target_opacity(elem) == 0.0


def test_restore_from_cinematic_reapplies_mode():
    s = HudOverlaySystem()
    s.populate_defaults()
    s.set_mode(HudMode.COMBAT)
    s.hide_all_for_cinematic()
    s.restore_from_cinematic()
    assert s.target_opacity(HudElement.HEALTH_GAUGE) > 0.0


# ---- is_visible_in ----

def test_is_visible_in_target_frame_combat():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert s.is_visible_in(
        HudElement.TARGET_FRAME, HudMode.COMBAT,
    )


def test_is_visible_in_target_frame_not_in_dialogue():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert not s.is_visible_in(
        HudElement.TARGET_FRAME, HudMode.DIALOGUE,
    )


def test_is_visible_in_region_banner_only_exploration():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert s.is_visible_in(
        HudElement.REGION_NAME_BANNER, HudMode.EXPLORATION,
    )
    assert not s.is_visible_in(
        HudElement.REGION_NAME_BANNER, HudMode.COMBAT,
    )


def test_dialogue_hides_target_frame():
    s = HudOverlaySystem()
    s.populate_defaults()
    target = s.opacity_for(
        HudElement.TARGET_FRAME, HudMode.DIALOGUE,
    )
    assert target == 0.0


def test_action_bar_visible_in_combat():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert s.should_render(
        HudElement.ACTION_BAR, HudMode.COMBAT,
    )


def test_minimap_visible_in_exploration():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert s.should_render(
        HudElement.MINIMAP, HudMode.EXPLORATION,
    )


def test_minimap_hidden_in_cinematic():
    s = HudOverlaySystem()
    s.populate_defaults()
    assert not s.should_render(
        HudElement.MINIMAP, HudMode.CINEMATIC,
    )
