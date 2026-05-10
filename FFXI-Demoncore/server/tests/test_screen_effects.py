"""Tests for screen_effects."""
from __future__ import annotations

import pytest

from server.screen_effects import (
    ActiveEffectHandle,
    BlendMode,
    EffectKind,
    IntensityCurve,
    ScreenEffect,
    ScreenEffectSystem,
    populate_default_library,
)


# ---- enums ----

def test_effect_kind_count_at_least_18():
    assert len(list(EffectKind)) >= 18


def test_blend_modes_four():
    assert {b for b in BlendMode} == {
        BlendMode.ADD, BlendMode.MULTIPLY,
        BlendMode.SCREEN, BlendMode.OVERLAY,
    }


# ---- IntensityCurve ----

def test_curve_clamps_below_first_keyframe():
    c = IntensityCurve(
        curve_id="c",
        keyframes=((1.0, 0.5), (2.0, 1.0)),
    )
    assert c.sample(0.0) == 0.5


def test_curve_clamps_above_last_keyframe():
    c = IntensityCurve(
        curve_id="c",
        keyframes=((0.0, 0.0), (1.0, 1.0)),
    )
    assert c.sample(5.0) == 1.0


def test_curve_lerp_midpoint():
    c = IntensityCurve(
        curve_id="c",
        keyframes=((0.0, 0.0), (1.0, 1.0)),
    )
    assert c.sample(0.5) == pytest.approx(0.5)


def test_curve_lerp_quarter():
    c = IntensityCurve(
        curve_id="c",
        keyframes=((0.0, 0.0), (1.0, 1.0)),
    )
    assert c.sample(0.25) == pytest.approx(0.25)


def test_curve_lerp_three_keyframes():
    c = IntensityCurve(
        curve_id="c",
        keyframes=((0.0, 0.0), (1.0, 2.0), (2.0, 0.0)),
    )
    assert c.sample(1.5) == pytest.approx(1.0)


def test_curve_empty_returns_zero():
    c = IntensityCurve(curve_id="c", keyframes=())
    assert c.sample(0.5) == 0.0


def test_curve_exact_keyframe_returns_value():
    c = IntensityCurve(
        curve_id="c",
        keyframes=((0.0, 0.0), (1.0, 0.7)),
    )
    assert c.sample(1.0) == pytest.approx(0.7)


# ---- register / get ----

def _make_effect(eid="ef", kind=EffectKind.HIT_SHAKE_LIGHT,
                 dur=1.0):
    return ScreenEffect(
        effect_id=eid, kind=kind,
        intensity_curve=IntensityCurve(
            curve_id="c",
            keyframes=((0.0, 0.0), (dur, 1.0)),
        ),
        duration_s=dur, blend_mode=BlendMode.ADD,
        affects_player_only=True,
    )


def test_register_and_get():
    s = ScreenEffectSystem()
    e = _make_effect()
    s.register_effect(e)
    assert s.get_effect("ef") is e


def test_register_empty_id_raises():
    s = ScreenEffectSystem()
    with pytest.raises(ValueError):
        s.register_effect(_make_effect(eid=""))


def test_register_zero_duration_raises():
    s = ScreenEffectSystem()
    with pytest.raises(ValueError):
        s.register_effect(_make_effect(dur=0.0))


def test_register_duplicate_raises():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect())
    with pytest.raises(ValueError):
        s.register_effect(_make_effect())


def test_get_unknown_raises():
    s = ScreenEffectSystem()
    with pytest.raises(KeyError):
        s.get_effect("missing")


# ---- apply ----

def test_apply_returns_handle():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect())
    h = s.apply("ef", "p1")
    assert isinstance(h, ActiveEffectHandle)
    assert h.effect_id == "ef"
    assert h.player_id == "p1"


def test_apply_unknown_raises():
    s = ScreenEffectSystem()
    with pytest.raises(KeyError):
        s.apply("missing", "p1")


def test_apply_two_stackable_effects():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect("a", EffectKind.HIT_SHAKE_LIGHT))
    s.register_effect(
        _make_effect("b", EffectKind.INTOXICATION_BLUR),
    )
    h1 = s.apply("a", "p1")
    h2 = s.apply("b", "p1")
    assert h1.handle_id != h2.handle_id


def test_ko_blocks_stacking():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect("a", EffectKind.HIT_SHAKE_LIGHT))
    s.register_effect(_make_effect("ko", EffectKind.KO_FADEOUT))
    s.apply("a", "p1")
    with pytest.raises(RuntimeError):
        s.apply("ko", "p1")


def test_dragon_breath_blocks_stacking():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect("a", EffectKind.HIT_SHAKE_LIGHT))
    s.register_effect(
        _make_effect("dr", EffectKind.DRAGON_BREATH_HEAT_HAZE),
    )
    s.apply("a", "p1")
    with pytest.raises(RuntimeError):
        s.apply("dr", "p1")


def test_cant_stack_on_top_of_ko():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect("ko", EffectKind.KO_FADEOUT))
    s.register_effect(_make_effect("a", EffectKind.HIT_SHAKE_LIGHT))
    s.apply("ko", "p1")
    with pytest.raises(RuntimeError):
        s.apply("a", "p1")


def test_ko_alone_works():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect("ko", EffectKind.KO_FADEOUT))
    h = s.apply("ko", "p1")
    assert h.player_id == "p1"


# ---- sample ----

def test_sample_at_t_zero():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect(dur=2.0))
    h = s.apply("ef", "p1")
    assert s.sample(h, 0.0) == 0.0


def test_sample_at_midpoint():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect(dur=2.0))
    h = s.apply("ef", "p1")
    # curve goes 0->1 over [0, 2]
    assert s.sample(h, 1.0) == pytest.approx(0.5)


def test_sample_after_duration_clamped():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect(dur=2.0))
    h = s.apply("ef", "p1")
    assert s.sample(h, 999.0) == pytest.approx(1.0)


def test_sample_negative_returns_zero():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect(dur=2.0))
    h = s.apply("ef", "p1")
    assert s.sample(h, -1.0) == 0.0


def test_sample_unknown_handle_raises():
    s = ScreenEffectSystem()
    fake = ActiveEffectHandle(
        handle_id="fake", effect_id="x",
        player_id="p", elapsed_s=0.0,
    )
    with pytest.raises(KeyError):
        s.sample(fake, 0.0)


# ---- all_active_for ----

def test_all_active_for_empty_player():
    s = ScreenEffectSystem()
    assert s.all_active_for("nobody") == ()


def test_all_active_for_two_effects():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect("a", EffectKind.HIT_SHAKE_LIGHT))
    s.register_effect(_make_effect("b", EffectKind.LEVITATE_BOB))
    s.apply("a", "p1")
    s.apply("b", "p1")
    actives = s.all_active_for("p1")
    assert len(actives) == 2


def test_all_active_for_player_isolation():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect("a", EffectKind.HIT_SHAKE_LIGHT))
    s.apply("a", "p1")
    assert s.all_active_for("p2") == ()


# ---- is_stackable_with ----

def test_stackable_two_hit_shakes():
    s = ScreenEffectSystem()
    assert s.is_stackable_with(
        EffectKind.HIT_SHAKE_LIGHT, EffectKind.HIT_SHAKE_HEAVY,
    )


def test_stackable_haste_and_silence():
    s = ScreenEffectSystem()
    assert s.is_stackable_with(
        EffectKind.HASTE_TIME_DIALATION,
        EffectKind.SILENCE_MUFFLE_VISUAL,
    )


def test_not_stackable_ko_with_anything():
    s = ScreenEffectSystem()
    assert not s.is_stackable_with(
        EffectKind.KO_FADEOUT, EffectKind.HIT_SHAKE_LIGHT,
    )


def test_not_stackable_dragon_breath_with_anything():
    s = ScreenEffectSystem()
    assert not s.is_stackable_with(
        EffectKind.DRAGON_BREATH_HEAT_HAZE,
        EffectKind.HIT_SHAKE_LIGHT,
    )


def test_not_stackable_two_takeovers():
    s = ScreenEffectSystem()
    assert not s.is_stackable_with(
        EffectKind.KO_FADEOUT,
        EffectKind.DRAGON_BREATH_HEAT_HAZE,
    )


# ---- tick ----

def test_tick_advances_and_expires():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect(dur=1.0))
    s.apply("ef", "p1")
    assert s.active_count() == 1
    expired = s.tick(0.5)
    assert expired == ()
    assert s.active_count() == 1
    expired = s.tick(0.6)
    assert len(expired) == 1
    assert s.active_count() == 0


def test_tick_clears_player_record():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect(dur=1.0))
    s.apply("ef", "p1")
    s.tick(2.0)
    assert s.all_active_for("p1") == ()


def test_tick_multiple_players():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect("a", dur=1.0))
    s.register_effect(_make_effect("b", EffectKind.LEVITATE_BOB,
                                    dur=2.0))
    s.apply("a", "p1")
    s.apply("b", "p2")
    expired = s.tick(1.5)
    # only a expired
    assert len(expired) == 1
    assert expired[0].effect_id == "a"


def test_tick_negative_dt_raises():
    s = ScreenEffectSystem()
    with pytest.raises(ValueError):
        s.tick(-0.5)


def test_tick_zero_dt_no_expiry():
    s = ScreenEffectSystem()
    s.register_effect(_make_effect(dur=1.0))
    s.apply("ef", "p1")
    expired = s.tick(0.0)
    assert expired == ()


# ---- default library ----

def test_default_library_count_at_least_18():
    s = ScreenEffectSystem()
    n = populate_default_library(s)
    assert n >= 18


def test_default_library_has_all_hit_shakes():
    s = ScreenEffectSystem()
    populate_default_library(s)
    for kind in (
        EffectKind.HIT_SHAKE_LIGHT,
        EffectKind.HIT_SHAKE_MEDIUM,
        EffectKind.HIT_SHAKE_HEAVY,
        EffectKind.HIT_SHAKE_ULTRA,
    ):
        s.get_effect(kind.value)


def test_default_library_ko_fadeout_1p2s():
    s = ScreenEffectSystem()
    populate_default_library(s)
    e = s.get_effect(EffectKind.KO_FADEOUT.value)
    assert e.duration_s == pytest.approx(1.2)


def test_default_library_mb_flash_screen_blend():
    s = ScreenEffectSystem()
    populate_default_library(s)
    e = s.get_effect(EffectKind.MB_FLASH.value)
    assert e.blend_mode == BlendMode.SCREEN


def test_default_library_ko_blocks_stack_at_runtime():
    s = ScreenEffectSystem()
    populate_default_library(s)
    s.apply(EffectKind.HIT_SHAKE_LIGHT.value, "p1")
    with pytest.raises(RuntimeError):
        s.apply(EffectKind.KO_FADEOUT.value, "p1")


def test_default_library_petri_grey_long():
    s = ScreenEffectSystem()
    populate_default_library(s)
    e = s.get_effect(EffectKind.PETRIFICATION_GREY_FREEZE.value)
    assert e.duration_s >= 30.0


def test_default_library_paralyze_curve_oscillates():
    s = ScreenEffectSystem()
    populate_default_library(s)
    e = s.get_effect(EffectKind.PARALYZE_STATIC_CRACKLE.value)
    # First keyframe high, second low (oscillating cracks).
    kf = e.intensity_curve.keyframes
    assert kf[0][1] > 0
    assert kf[1][1] == 0.0
