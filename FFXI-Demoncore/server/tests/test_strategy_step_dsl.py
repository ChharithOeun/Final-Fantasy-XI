"""Tests for strategy_step_dsl."""
from __future__ import annotations

from server.strategy_step_dsl import (
    StepKind, StrategyStep, StrategyStepDsl,
)


def _phase_step(order=1, text="Phase 1"):
    return StrategyStep(
        kind=StepKind.PHASE, order=order, text=text,
    )


def test_build_minimal_phase_only():
    d = StrategyStepDsl()
    out = d.build(steps=[_phase_step()])
    assert out.valid is True


def test_build_empty_blocked():
    d = StrategyStepDsl()
    out = d.build(steps=[])
    assert out.valid is False
    assert out.reason == "empty_steps"


def test_build_no_phase_blocked():
    d = StrategyStepDsl()
    out = d.build(steps=[
        StrategyStep(
            kind=StepKind.CALLOUT, order=1,
            text="Stand back",
        ),
    ])
    assert out.valid is False
    assert out.reason == "no_phase_step"


def test_build_order_must_start_at_1():
    d = StrategyStepDsl()
    out = d.build(steps=[
        StrategyStep(
            kind=StepKind.PHASE, order=2, text="P1",
        ),
    ])
    assert out.valid is False
    assert out.reason == "order_must_be_monotonic_from_1"


def test_build_order_skip_blocked():
    d = StrategyStepDsl()
    out = d.build(steps=[
        _phase_step(order=1),
        StrategyStep(
            kind=StepKind.CALLOUT, order=3, text="x",
        ),
    ])
    assert out.valid is False
    assert out.error_at_step == 3


def test_build_blank_text_blocked():
    d = StrategyStepDsl()
    out = d.build(steps=[
        StrategyStep(
            kind=StepKind.PHASE, order=1, text="   ",
        ),
    ])
    assert out.valid is False
    assert out.reason == "text_required"


def test_build_text_too_long_blocked():
    d = StrategyStepDsl()
    out = d.build(steps=[
        StrategyStep(
            kind=StepKind.PHASE, order=1,
            text="x" * 141,
        ),
    ])
    assert out.valid is False
    assert out.reason == "text_too_long"


def test_build_text_at_max_allowed():
    d = StrategyStepDsl()
    out = d.build(steps=[
        StrategyStep(
            kind=StepKind.PHASE, order=1,
            text="x" * 140,
        ),
    ])
    assert out.valid is True


def test_build_too_many_steps_blocked():
    d = StrategyStepDsl()
    steps = [_phase_step()] + [
        StrategyStep(
            kind=StepKind.CALLOUT, order=i + 2,
            text=f"step {i}",
        )
        for i in range(100)
    ]
    out = d.build(steps=steps)
    assert out.valid is False
    assert out.reason == "too_many_steps"


def test_build_trigger_pct_negative_blocked():
    d = StrategyStepDsl()
    out = d.build(steps=[
        _phase_step(),
        StrategyStep(
            kind=StepKind.COOLDOWN, order=2,
            text="2hr at low HP", trigger_pct=-5,
        ),
    ])
    assert out.valid is False
    assert out.reason == "trigger_pct_out_of_range"


def test_build_trigger_pct_over_100_blocked():
    d = StrategyStepDsl()
    out = d.build(steps=[
        _phase_step(),
        StrategyStep(
            kind=StepKind.COOLDOWN, order=2,
            text="too high", trigger_pct=101,
        ),
    ])
    assert out.valid is False
    assert out.reason == "trigger_pct_out_of_range"


def test_build_trigger_pct_at_bounds_allowed():
    d = StrategyStepDsl()
    out = d.build(steps=[
        _phase_step(),
        StrategyStep(
            kind=StepKind.COOLDOWN, order=2,
            text="boss spawned", trigger_pct=100,
        ),
        StrategyStep(
            kind=StepKind.EMERGENCY, order=3,
            text="boss dead", trigger_pct=0,
        ),
    ])
    assert out.valid is True


def test_filter_kind_returns_subset():
    d = StrategyStepDsl()
    steps = [
        _phase_step(order=1),
        StrategyStep(
            kind=StepKind.CALLOUT, order=2, text="stand",
        ),
        StrategyStep(
            kind=StepKind.CALLOUT, order=3, text="hide",
        ),
        StrategyStep(
            kind=StepKind.COOLDOWN, order=4,
            text="2hr", trigger_pct=25,
        ),
    ]
    callouts = d.filter_kind(steps=steps, kind=StepKind.CALLOUT)
    assert len(callouts) == 2


def test_next_step_picks_lowest_pct_ge_current():
    d = StrategyStepDsl()
    steps = [
        _phase_step(order=1),
        StrategyStep(
            kind=StepKind.COOLDOWN, order=2,
            text="2hr", trigger_pct=25,
        ),
        StrategyStep(
            kind=StepKind.COOLDOWN, order=3,
            text="cooldown", trigger_pct=50,
        ),
    ]
    nxt = d.next_step(steps=steps, current_hp_pct=30)
    assert nxt.trigger_pct == 50


def test_next_step_skips_phase_position_required():
    d = StrategyStepDsl()
    steps = [
        _phase_step(order=1),
        StrategyStep(
            kind=StepKind.POSITION, order=2,
            text="behind boss", trigger_pct=80,
        ),
        StrategyStep(
            kind=StepKind.REQUIRED, order=3,
            text="reraise", trigger_pct=80, required_at=True,
        ),
        StrategyStep(
            kind=StepKind.CALLOUT, order=4,
            text="dodge", trigger_pct=80,
        ),
    ]
    nxt = d.next_step(steps=steps, current_hp_pct=10)
    assert nxt.kind == StepKind.CALLOUT


def test_next_step_skips_no_trigger_steps():
    d = StrategyStepDsl()
    steps = [
        _phase_step(order=1),
        StrategyStep(
            kind=StepKind.CALLOUT, order=2,
            text="always-on note",
        ),
    ]
    nxt = d.next_step(steps=steps, current_hp_pct=50)
    assert nxt is None


def test_next_step_returns_none_when_all_below_current():
    d = StrategyStepDsl()
    steps = [
        _phase_step(order=1),
        StrategyStep(
            kind=StepKind.COOLDOWN, order=2,
            text="x", trigger_pct=20,
        ),
    ]
    nxt = d.next_step(steps=steps, current_hp_pct=80)
    assert nxt is None


def test_seven_step_kinds():
    assert len(list(StepKind)) == 7
