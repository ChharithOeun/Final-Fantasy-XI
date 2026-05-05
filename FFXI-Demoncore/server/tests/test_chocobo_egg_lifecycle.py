"""Tests for the chocobo egg lifecycle."""
from __future__ import annotations

from server.chocobo_colors import ChocoboColor
from server.chocobo_egg_lifecycle import EggLifecycle, EggState


_HATCH = 90 * 86_400


def test_lay_basic():
    e = EggLifecycle()
    res = e.lay(
        breeder_id="kraw",
        color=ChocoboColor.YELLOW,
        bloodline_traits=("speed", "stamina"),
        is_rainbow=False,
        now_seconds=0,
    )
    assert res.accepted
    assert res.hatch_due_at == _HATCH


def test_lay_double_blocked():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.BROWN,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    res = e.lay(
        breeder_id="kraw",
        color=ChocoboColor.YELLOW,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=10,
    )
    assert not res.accepted


def test_check_default_spoiled():
    e = EggLifecycle()
    snap = e.check(breeder_id="ghost", now_seconds=0)
    assert snap.state == EggState.SPOILED


def test_check_during_incubation():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.BLUE,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    snap = e.check(breeder_id="kraw", now_seconds=10)
    assert snap.state == EggState.INCUBATING
    assert snap.color == ChocoboColor.BLUE


def test_maintain_basic():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.BLUE,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    res = e.maintain_color(
        breeder_id="kraw",
        now_seconds=86_400,
        resources_paid=True,
    )
    assert res.accepted


def test_maintain_no_resources():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.BLUE,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    res = e.maintain_color(
        breeder_id="kraw",
        now_seconds=86_400,
        resources_paid=False,
    )
    assert not res.accepted


def test_decay_to_yellow_when_unmaintained():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.BLUE,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    # 7d interval + 3d grace = 10d before decay; check at 12d
    snap = e.check(
        breeder_id="kraw",
        now_seconds=12 * 86_400,
    )
    assert snap.color == ChocoboColor.YELLOW


def test_change_color_succeeds():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.YELLOW,
        bloodline_traits=("ice_lineage",),
        is_rainbow=False,
        now_seconds=0,
    )
    res = e.change_color(
        breeder_id="kraw",
        target_color=ChocoboColor.BLUE,
        now_seconds=10,
        resources_paid=True,
        success_roll_pct=10,
    )
    assert res.succeeded
    assert res.color_after == ChocoboColor.BLUE


def test_change_color_fails():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.YELLOW,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    res = e.change_color(
        breeder_id="kraw",
        target_color=ChocoboColor.BLUE,
        now_seconds=10,
        resources_paid=True,
        success_roll_pct=90,
    )
    assert not res.succeeded
    assert res.color_after == ChocoboColor.YELLOW


def test_change_color_rainbow_blocked():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.RAINBOW,
        bloodline_traits=(),
        is_rainbow=True,
        now_seconds=0,
    )
    res = e.change_color(
        breeder_id="kraw",
        target_color=ChocoboColor.BLUE,
        now_seconds=10,
        resources_paid=True,
        success_roll_pct=5,
    )
    assert not res.accepted


def test_change_color_no_resources():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.YELLOW,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    res = e.change_color(
        breeder_id="kraw",
        target_color=ChocoboColor.BLUE,
        now_seconds=10,
        resources_paid=False,
        success_roll_pct=10,
    )
    assert not res.accepted


def test_hatch_too_early():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.BLUE,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    res = e.hatch(breeder_id="kraw", now_seconds=86_400)
    assert not res.accepted


def test_hatch_at_term():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.BLUE,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    # Maintain weekly through the full 90-day window
    for day in range(0, 90, 7):
        e.maintain_color(
            breeder_id="kraw",
            now_seconds=day * 86_400,
            resources_paid=True,
        )
    # Final maintain right before hatch keeps the color current
    e.maintain_color(
        breeder_id="kraw",
        now_seconds=_HATCH - 86_400,
        resources_paid=True,
    )
    res = e.hatch(breeder_id="kraw", now_seconds=_HATCH)
    assert res.accepted
    assert res.chick_color == ChocoboColor.BLUE


def test_hatch_rainbow():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.RAINBOW,
        bloodline_traits=(),
        is_rainbow=True,
        now_seconds=0,
    )
    res = e.hatch(breeder_id="kraw", now_seconds=_HATCH)
    assert res.accepted
    assert res.is_rainbow


def test_hatch_no_egg():
    e = EggLifecycle()
    res = e.hatch(breeder_id="ghost", now_seconds=_HATCH)
    assert not res.accepted


def test_maintain_no_egg():
    e = EggLifecycle()
    res = e.maintain_color(
        breeder_id="ghost",
        now_seconds=0, resources_paid=True,
    )
    assert not res.accepted


def test_change_color_invalid_roll():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.YELLOW,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    res = e.change_color(
        breeder_id="kraw",
        target_color=ChocoboColor.BLUE,
        now_seconds=10,
        resources_paid=True,
        success_roll_pct=200,
    )
    assert not res.accepted


def test_lay_after_hatch_allowed():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.YELLOW,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    e.hatch(breeder_id="kraw", now_seconds=_HATCH)
    # After hatch, breeder may lay again (mount has graduated)
    res = e.lay(
        breeder_id="kraw",
        color=ChocoboColor.RED,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=_HATCH + 100,
    )
    assert res.accepted


def test_check_seconds_until():
    e = EggLifecycle()
    e.lay(
        breeder_id="kraw",
        color=ChocoboColor.BLUE,
        bloodline_traits=(),
        is_rainbow=False,
        now_seconds=0,
    )
    snap = e.check(breeder_id="kraw", now_seconds=86_400)
    assert snap.seconds_until_hatch == _HATCH - 86_400
