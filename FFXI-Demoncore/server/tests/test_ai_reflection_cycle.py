"""Tests for the AI nightly reflection cycle."""
from __future__ import annotations

from server.ai_reflection_cycle import (
    DEFAULT_REFLECTION_HOUR,
    DEFAULT_STAGE_ORDER,
    CycleStage,
    ReflectionCycle,
    should_run_cycle,
)


def test_default_stage_order():
    assert DEFAULT_STAGE_ORDER[0] == CycleStage.MEMORY_COMPACT
    assert DEFAULT_STAGE_ORDER[-1] == (
        CycleStage.ECONOMY_REGULATOR_TICK
    )
    # All 5 stages
    assert len(DEFAULT_STAGE_ORDER) == 5


def test_cycle_no_callbacks_runs_clean():
    cycle = ReflectionCycle()
    report = cycle.run_cycle(now_seconds=0.0)
    assert report.all_succeeded
    assert report.total_items_processed == 0
    assert report.cycle_number == 1


def test_cycle_with_callbacks_collects_processed():
    cycle = ReflectionCycle()
    cycle.register_stage(
        stage=CycleStage.MEMORY_COMPACT,
        callback=lambda _now: 7,
    )
    cycle.register_stage(
        stage=CycleStage.RUMOR_AGE,
        callback=lambda _now: 3,
    )
    report = cycle.run_cycle(now_seconds=100.0)
    by_stage = {s.stage: s for s in report.stages}
    assert by_stage[CycleStage.MEMORY_COMPACT].items_processed == 7
    assert by_stage[CycleStage.RUMOR_AGE].items_processed == 3
    assert report.total_items_processed == 10


def test_cycle_runs_in_canonical_order():
    cycle = ReflectionCycle()
    visited: list[CycleStage] = []
    for stage in DEFAULT_STAGE_ORDER:
        cycle.register_stage(
            stage=stage,
            callback=(
                lambda _now, s=stage: (visited.append(s), 0)[1]
            ),
        )
    cycle.run_cycle(now_seconds=0.0)
    assert tuple(visited) == DEFAULT_STAGE_ORDER


def test_failing_stage_marked_but_cycle_continues():
    cycle = ReflectionCycle()

    def boom(_now: float) -> int:
        raise RuntimeError("oops")

    cycle.register_stage(
        stage=CycleStage.GOAL_REVIEW, callback=boom,
    )
    cycle.register_stage(
        stage=CycleStage.RUMOR_AGE,
        callback=lambda _now: 5,
    )
    report = cycle.run_cycle(now_seconds=100.0)
    assert not report.all_succeeded
    by_stage = {s.stage: s for s in report.stages}
    assert not by_stage[CycleStage.GOAL_REVIEW].success
    assert "oops" in by_stage[CycleStage.GOAL_REVIEW].error
    # Subsequent stage still ran
    assert by_stage[CycleStage.RUMOR_AGE].success
    assert by_stage[CycleStage.RUMOR_AGE].items_processed == 5


def test_runs_completed_increments():
    cycle = ReflectionCycle()
    cycle.run_cycle(now_seconds=0.0)
    cycle.run_cycle(now_seconds=100.0)
    cycle.run_cycle(now_seconds=200.0)
    assert cycle.runs_completed() == 3


def test_last_run_at_tracks_time():
    cycle = ReflectionCycle()
    assert cycle.last_run_at() is None
    cycle.run_cycle(now_seconds=500.0)
    assert cycle.last_run_at() == 500.0


def test_last_report_packaged():
    cycle = ReflectionCycle()
    cycle.register_stage(
        stage=CycleStage.MEMORY_COMPACT,
        callback=lambda _now: 12,
    )
    cycle.run_cycle(now_seconds=100.0)
    rep = cycle.last_report()
    assert rep is not None
    assert rep.cycle_number == 1
    assert rep.total_items_processed == 12


def test_should_run_at_target_hour_first_time():
    assert should_run_cycle(
        hour_of_day=DEFAULT_REFLECTION_HOUR,
        last_run_at_seconds=None,
        now_seconds=100.0,
    )


def test_should_not_run_off_hour():
    assert not should_run_cycle(
        hour_of_day=12,
        last_run_at_seconds=None,
        now_seconds=100.0,
    )


def test_should_not_run_within_cooldown():
    """Even at the target hour, if the cycle just ran, skip."""
    assert not should_run_cycle(
        hour_of_day=DEFAULT_REFLECTION_HOUR,
        last_run_at_seconds=10_000.0,
        now_seconds=10_100.0,
        cooldown_seconds=60 * 60 * 12,
    )


def test_should_run_after_cooldown():
    assert should_run_cycle(
        hour_of_day=DEFAULT_REFLECTION_HOUR,
        last_run_at_seconds=0.0,
        now_seconds=60 * 60 * 13,
        cooldown_seconds=60 * 60 * 12,
    )


def test_has_stage_check():
    cycle = ReflectionCycle()
    assert not cycle.has_stage(CycleStage.MEMORY_COMPACT)
    cycle.register_stage(
        stage=CycleStage.MEMORY_COMPACT,
        callback=lambda _n: 0,
    )
    assert cycle.has_stage(CycleStage.MEMORY_COMPACT)


def test_full_lifecycle_simulated_night_cycle():
    """Simulate the full nightly cycle with stub stages
    standing in for the real subsystems."""
    cycle = ReflectionCycle()
    counts = {
        CycleStage.MEMORY_COMPACT: 42,    # memories pruned
        CycleStage.GOAL_REVIEW: 18,       # goals reviewed
        CycleStage.FACTION_REVIEW: 11,    # factions ticked
        CycleStage.RUMOR_AGE: 7,          # rumors aged out
        CycleStage.ECONOMY_REGULATOR_TICK: 25,  # items boosted
    }
    for stage, n in counts.items():
        cycle.register_stage(
            stage=stage,
            callback=lambda _now, n=n: n,
        )
    report = cycle.run_cycle(now_seconds=86_400.0)
    assert report.all_succeeded
    assert report.total_items_processed == sum(counts.values())
    # Stages came back in canonical order
    stage_order = [s.stage for s in report.stages]
    assert tuple(stage_order) == DEFAULT_STAGE_ORDER
    # Verify per-stage counts surface correctly
    by_stage = {s.stage: s for s in report.stages}
    for stage, n in counts.items():
        assert by_stage[stage].items_processed == n
